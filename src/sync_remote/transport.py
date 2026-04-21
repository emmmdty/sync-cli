from __future__ import annotations

from pathlib import Path
import fnmatch
import os
import re
import secrets
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time

import requests
from dotenv import load_dotenv

from .config import ProjectConfig, expand_user_path
from .operations import create_tar_archive
from .ssh_config import SSHHostEntry, parse_ssh_config_blocks, read_ssh_host_entry, select_ssh_block, upsert_ssh_host_entry

RSYNC_RETRYABLE_EXIT_CODES = {10, 11, 12, 30, 35, 255}


def generate_secure_temp_name(prefix: str = "sync", suffix: str = ".tar.gz") -> str:
    return f"{prefix}_{secrets.token_hex(8)}{suffix}"


def _ssh_config_path(config: ProjectConfig) -> Path:
    return Path(expand_user_path(config.connection.ssh_config_path))


def _ssh_key_path(config: ProjectConfig) -> Path:
    return Path(expand_user_path(config.connection.ssh_key_path))


def _get_ssh_blocks(config: ProjectConfig) -> list[dict]:
    config_path = _ssh_config_path(config)
    if not config_path.exists():
        return []
    return parse_ssh_config_blocks(config_path.read_text(encoding="utf-8").splitlines(True))


def _ssh_alias_exists(config: ProjectConfig) -> bool:
    return select_ssh_block(_get_ssh_blocks(config), config.connection.host) is not None


def resolve_ssh_target(config: ProjectConfig) -> str:
    if _ssh_alias_exists(config):
        return config.connection.host
    if config.connection.hostname:
        return config.connection.hostname
    return config.connection.host


def build_remote_identity(config: ProjectConfig) -> str:
    return f"{config.connection.user}@{resolve_ssh_target(config)}"


def get_ssh_options(config: ProjectConfig, *, include_host_check: bool = True) -> list[str]:
    options = ["-o", "ConnectTimeout=10"]
    config_path = _ssh_config_path(config)
    key_path = _ssh_key_path(config)

    if config_path.exists():
        options.extend(["-F", str(config_path)])
    if config.connection.auth_mode != "password" and key_path.exists():
        options.extend(["-i", str(key_path)])

    if include_host_check and config.connection.known_hosts_check:
        options.extend(["-o", "StrictHostKeyChecking=accept-new"])
    else:
        options.extend(["-o", "StrictHostKeyChecking=no"])
    return options


def format_stderr(stderr: bytes | str | None) -> str:
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace")
    return stderr or ""


def get_port_from_ssh_config(config: ProjectConfig) -> str | None:
    blocks = _get_ssh_blocks(config)
    block = select_ssh_block(blocks, config.connection.host)
    if block and block.get("port"):
        return str(block["port"])
    return None


def update_ssh_port_in_config(new_port: str, config: ProjectConfig) -> None:
    config_path = _ssh_config_path(config)
    if not config_path.exists():
        return
    entry = read_ssh_host_entry(config_path, config.connection.host)
    if entry is None:
        return
    upsert_ssh_host_entry(
        config_path,
        SSHHostEntry(
            host=entry.host,
            hostname=entry.hostname,
            user=entry.user,
            port=str(new_port),
            identity_file=entry.identity_file,
        ),
    )


def get_port_from_cpolar(config: ProjectConfig) -> str | None:
    if not config.cpolar.tunnel_name:
        return None

    env_path = Path(expand_user_path(config.cpolar.env_path))
    if env_path.exists():
        load_dotenv(env_path)

    username = os.environ.get("CPOLAR_USER")
    password = os.environ.get("CPOLAR_PASS")
    if not username or not password:
        return None

    login_url = "https://dashboard.cpolar.com/login"
    target_url = "https://dashboard.cpolar.com/status"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": login_url,
    }

    with requests.Session() as session:
        session.get(login_url, timeout=10)
        response = session.post(
            login_url,
            data={"login": username, "password": password},
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200 or "dashboard" not in response.url:
            return None

        target_response = session.get(target_url, headers=headers, timeout=10)
        if target_response.status_code != 200:
            return None

        pattern = (
            rf"<tr>.*?<td>{re.escape(config.cpolar.tunnel_name)}</td>.*?"
            rf"<a[^>]*>(.*?)</a>.*?</tr>"
        )
        match = re.search(pattern, target_response.text, re.DOTALL)
        if not match:
            return None

        extracted_url = match.group(1)
        if ":" not in extracted_url:
            return None

        port = extracted_url.rsplit(":", maxsplit=1)[-1]
        return port


def resolve_connection_port(config: ProjectConfig, explicit_port: str | None = None) -> str:
    if explicit_port:
        return str(explicit_port)

    if config.connection.port_mode == "fixed":
        if config.connection.port is None:
            raise RuntimeError("当前配置使用 fixed 端口模式，但没有配置 connection.port")
        return str(config.connection.port)

    port = get_port_from_cpolar(config)
    if port:
        return port

    port = get_port_from_ssh_config(config)
    if port:
        return port

    raise RuntimeError("无法解析 SSH 端口，请检查 fixed 端口配置、Cpolar 或 SSH config")


def ensure_rsync_available() -> bool:
    return shutil.which("rsync") is not None


def _auth_prefix_and_env(config: ProjectConfig, password: str | None) -> tuple[list[str], dict[str, str] | None]:
    if config.connection.auth_mode != "password":
        return [], None
    if not password:
        raise RuntimeError("当前配置使用 password 认证，但未提供服务器密码")
    if shutil.which("sshpass") is None:
        raise RuntimeError("当前配置使用 password 认证，但未找到 sshpass")
    env = os.environ.copy()
    env["SSHPASS"] = password
    return ["sshpass", "-e"], env


def resolve_effective_transport(transport: str, sync_paths: tuple[str, ...]) -> str:
    if transport != "rsync":
        return transport

    if ensure_rsync_available():
        return "rsync"

    if sync_paths:
        raise RuntimeError("`--sync-path` 需要 rsync，但当前系统未安装 rsync")

    print("[*] rsync 不可用，自动回退到 archive")
    return "archive"


def build_rsync_ssh_command(config: ProjectConfig, port: str) -> str:
    ssh_cmd = [
        "ssh",
        "-p",
        str(port),
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=6",
        "-o",
        "TCPKeepAlive=yes",
        *get_ssh_options(config),
    ]
    return " ".join(shlex.quote(part) for part in ssh_cmd)


def normalize_sync_paths(base_dir: Path | str, raw_paths: tuple[str, ...], *, require_exists: bool) -> list[tuple[str, Path]]:
    root = Path(base_dir).resolve()
    results: list[tuple[str, Path]] = []

    for raw_path in raw_paths:
        candidate = (root / raw_path).resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"路径超出项目目录: {raw_path}")
        if require_exists and not candidate.exists():
            raise FileNotFoundError(f"路径不存在: {raw_path}")
        results.append((candidate.relative_to(root).as_posix(), candidate))

    return results


def ensure_remote_directory(config: ProjectConfig, port: str, target_dir: str, *, password: str | None = None) -> bool:
    try:
        prefix, env = _auth_prefix_and_env(config, password)
    except RuntimeError as exc:
        print(exc)
        return False
    command = [
        "ssh",
        "-p",
        str(port),
        *get_ssh_options(config),
        build_remote_identity(config),
        f"mkdir -p {shlex.quote(target_dir)}",
    ]
    result = subprocess.run(prefix + command, capture_output=True, env=env)
    if result.returncode == 0:
        return True
    print("错误: 创建远程目录失败")
    print(format_stderr(result.stderr))
    return False


def build_rsync_command(
    config: ProjectConfig,
    *,
    port: str,
    source: str,
    destination: str,
    excludes: tuple[str, ...],
) -> list[str]:
    command = [
        "rsync",
        "-az",
        "--partial",
        "--modify-window=-1",
        "--info=progress2,name0",
        "-e",
        build_rsync_ssh_command(config, port),
    ]
    for pattern in excludes:
        command.extend(["--exclude", pattern])
    command.extend([source, destination])
    return command


def normalize_remote_parent(path: str) -> str:
    return path or "."


def filter_sync_paths(
    base_dir: Path,
    selected_paths: list[tuple[str, Path]],
    *,
    excludes: tuple[str, ...],
    max_size_bytes: int,
) -> list[tuple[str, Path]]:
    return [
        (rel_path, abs_path)
        for rel_path, abs_path in selected_paths
        if not should_exclude(abs_path, base_dir, excludes, max_size_bytes)
    ]


def run_rsync_command(command: list[str], label: str, *, config: ProjectConfig, password: str | None = None) -> bool:
    try:
        prefix, env = _auth_prefix_and_env(config, password)
    except RuntimeError as exc:
        print(exc)
        return False
    for attempt in range(1, 4):
        result = subprocess.run(prefix + command, text=True, env=env)
        if result.returncode == 0:
            return True
        if result.returncode in RSYNC_RETRYABLE_EXIT_CODES and attempt < 3:
            print(f"rsync {label} 中断，5 秒后重试...")
            time.sleep(5)
            continue
        print(f"错误: rsync {label}失败 (返回码: {result.returncode})")
        return False
    return False


def should_exclude(path: Path, base_dir: Path, exclude_patterns: tuple[str, ...], max_size: int) -> bool:
    rel_path = path.relative_to(base_dir).as_posix()
    name = path.name

    for pattern in exclude_patterns:
        if pattern.startswith("/"):
            root_pattern = pattern[1:]
            rel_parts = rel_path.split("/")
            if rel_parts and fnmatch.fnmatch(rel_parts[0], root_pattern):
                return True
            continue

        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in rel_path.split("/")):
            return True

    if path.is_file():
        try:
            if path.stat().st_size > max_size:
                return True
        except OSError:
            return True
    return False


def should_exclude_by_pattern(path: Path, base_dir: Path, exclude_patterns: tuple[str, ...]) -> bool:
    rel_path = path.relative_to(base_dir).as_posix()
    name = path.name

    for pattern in exclude_patterns:
        if pattern.startswith("/"):
            rel_parts = rel_path.split("/")
            if rel_parts and fnmatch.fnmatch(rel_parts[0], pattern[1:]):
                return True
            continue
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in rel_path.split("/")):
            return True
    return False


def collect_files(base_dir: Path, exclude_patterns: tuple[str, ...], max_size: int) -> list[str]:
    files: list[str] = []
    for current_root, dirs, filenames in os.walk(base_dir, topdown=True):
        current_path = Path(current_root)
        dirs[:] = [
            directory
            for directory in dirs
            if not should_exclude(current_path / directory, base_dir, exclude_patterns, max_size)
        ]
        for filename in filenames:
            file_path = current_path / filename
            if should_exclude(file_path, base_dir, exclude_patterns, max_size):
                continue
            files.append(file_path.relative_to(base_dir).as_posix())
    return files


def collect_excluded_files(base_dir: Path, exclude_patterns: tuple[str, ...], max_size: int) -> list[str]:
    excluded: list[str] = []
    for current_root, dirs, filenames in os.walk(base_dir, topdown=True):
        current_path = Path(current_root)
        excluded_dirs = []
        for directory in dirs:
            dir_path = current_path / directory
            if should_exclude(dir_path, base_dir, exclude_patterns, max_size):
                excluded_dirs.append(directory)
                excluded.append(f"{dir_path.relative_to(base_dir).as_posix()}/")

        dirs[:] = [directory for directory in dirs if directory not in excluded_dirs]

        for filename in filenames:
            file_path = current_path / filename
            if file_path.is_file() and file_path.stat().st_size > max_size:
                continue
            if should_exclude_by_pattern(file_path, base_dir, exclude_patterns):
                excluded.append(file_path.relative_to(base_dir).as_posix())
    return excluded


def sync_upload_rsync(
    *,
    local_dir: Path,
    remote_dir: str,
    port: str,
    config: ProjectConfig,
    excludes: tuple[str, ...],
    dry_run: bool,
    list_excluded: bool,
    sync_paths: tuple[str, ...],
    max_size_bytes: int,
    password: str | None,
) -> bool:
    print(f"本地: {local_dir}")
    print(f"远程: {build_remote_identity(config)}:{remote_dir}")

    if sync_paths:
        selected_paths = filter_sync_paths(
            local_dir,
            normalize_sync_paths(local_dir, sync_paths, require_exists=True),
            excludes=excludes,
            max_size_bytes=max_size_bytes,
        )
        if not selected_paths:
            print("没有文件需要同步")
            return True
        if dry_run:
            for rel_path, _ in selected_paths:
                print(f"[DRY-RUN] 上传路径: {rel_path}")
            return True
        for rel_path, abs_path in selected_paths:
            remote_target = f"{remote_dir}/{rel_path}".replace("//", "/")
            remote_parent = normalize_remote_parent(os.path.dirname(remote_target))
            if not ensure_remote_directory(config, port, remote_parent, password=password):
                return False
            command_excludes = excludes if abs_path.is_dir() else ()
            command = build_rsync_command(
                config,
                port=port,
                source=str(abs_path),
                destination=f"{build_remote_identity(config)}:{remote_parent}/",
                excludes=command_excludes,
            )
            if not run_rsync_command(command, f"上传 {rel_path}", config=config, password=password):
                return False
        return True

    files = collect_files(local_dir, excludes, max_size_bytes)
    if list_excluded:
        excluded = collect_excluded_files(local_dir, excludes, max_size_bytes)
        if excluded:
            print(f"排除文件数: {len(excluded)}")

    if dry_run:
        print(f"[DRY-RUN] 将上传 {len(files)} 个文件到 {remote_dir}")
        return True

    if not files:
        print("没有文件需要同步")
        return True

    if not ensure_remote_directory(config, port, remote_dir, password=password):
        return False

    command = build_rsync_command(
        config,
        port=port,
        source=f"{local_dir}/",
        destination=f"{build_remote_identity(config)}:{remote_dir}/",
        excludes=excludes,
    )
    return run_rsync_command(command, "上传", config=config, password=password)


def sync_upload_archive(
    *,
    local_dir: Path,
    remote_dir: str,
    port: str,
    config: ProjectConfig,
    excludes: tuple[str, ...],
    dry_run: bool,
    list_excluded: bool,
    max_size_bytes: int,
    password: str | None,
) -> bool:
    files = collect_files(local_dir, excludes, max_size_bytes)
    if list_excluded:
        excluded = collect_excluded_files(local_dir, excludes, max_size_bytes)
        if excluded:
            print(f"排除文件数: {len(excluded)}")
    if dry_run:
        print(f"[DRY-RUN] 将使用 archive 上传 {len(files)} 个文件")
        return True
    if not files:
        print("没有文件需要同步")
        return True

    remote_parent = normalize_remote_parent(os.path.dirname(remote_dir.rstrip("/")))
    if not ensure_remote_directory(config, port, remote_parent, password=password):
        return False

    local_temp = Path(tempfile.gettempdir()) / generate_secure_temp_name()
    try:
        with local_temp.open("wb") as handle:
            create_tar_archive(local_dir, files, handle, project_name=Path(remote_dir).name)

        remote_temp = f"/tmp/{generate_secure_temp_name()}"
        try:
            prefix, env = _auth_prefix_and_env(config, password)
        except RuntimeError as exc:
            print(exc)
            return False
        scp_command = [
            "scp",
            "-P",
            str(port),
            *get_ssh_options(config),
            str(local_temp),
            f"{build_remote_identity(config)}:{remote_temp}",
        ]
        result = subprocess.run(prefix + scp_command, capture_output=True, env=env)
        if result.returncode != 0:
            print(format_stderr(result.stderr))
            return False

        extract_command = [
            "ssh",
            "-p",
            str(port),
            *get_ssh_options(config),
            build_remote_identity(config),
            (
                f"cd {shlex.quote(remote_parent)} && "
                f"tar -xzf {shlex.quote(remote_temp)} && rm -f {shlex.quote(remote_temp)}"
            ),
        ]
        result = subprocess.run(prefix + extract_command, capture_output=True, env=env)
        if result.returncode != 0:
            print(format_stderr(result.stderr))
            return False
        return True
    finally:
        local_temp.unlink(missing_ok=True)


def sync_upload(
    *,
    local_dir: Path | str,
    remote_dir: str,
    port: str,
    config: ProjectConfig,
    dry_run: bool = False,
    list_excluded: bool = True,
    transport: str | None = None,
    sync_paths: tuple[str, ...] = (),
    extra_excludes: tuple[str, ...] = (),
    max_size_mb: int | None = None,
    password: str | None = None,
) -> bool:
    project_dir = Path(local_dir).resolve()
    transport_name = resolve_effective_transport(transport or config.sync.transport, sync_paths)
    max_size_bytes = (max_size_mb or config.sync.max_file_size_mb) * 1024 * 1024
    excludes = tuple(config.sync.excludes) + tuple(extra_excludes)

    if transport_name == "rsync":
        return sync_upload_rsync(
            local_dir=project_dir,
            remote_dir=remote_dir,
            port=port,
            config=config,
            excludes=excludes,
            dry_run=dry_run,
            list_excluded=list_excluded,
            sync_paths=sync_paths,
            max_size_bytes=max_size_bytes,
            password=password,
        )
    return sync_upload_archive(
        local_dir=project_dir,
        remote_dir=remote_dir,
        port=port,
        config=config,
        excludes=excludes,
        dry_run=dry_run,
        list_excluded=list_excluded,
        max_size_bytes=max_size_bytes,
        password=password,
    )


def download_remote_archive(
    *,
    local_dir: Path | str,
    remote_dir: str,
    port: str,
    output_path: Path | str,
    config: ProjectConfig,
    password: str | None = None,
) -> bool:
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    remote_dir = remote_dir.rstrip("/")
    remote_parent = normalize_remote_parent(os.path.dirname(remote_dir.rstrip("/")))
    remote_name = os.path.basename(remote_dir)
    exclude_args = " ".join(f"--exclude={shlex.quote(item)}" for item in config.sync.excludes)
    remote_tar_command = (
        f"cd {shlex.quote(remote_parent)} && "
        f"tar {exclude_args} -czf - {shlex.quote(remote_name)} 2>/dev/null"
    )

    ssh_command = [
        "ssh",
        "-p",
        str(port),
        *get_ssh_options(config),
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=3",
        build_remote_identity(config),
        remote_tar_command,
    ]
    try:
        prefix, env = _auth_prefix_and_env(config, password)
    except RuntimeError as exc:
        print(exc)
        return False

    with destination.open("wb") as handle:
        process = subprocess.Popen(prefix + ssh_command, stdout=handle, stderr=subprocess.PIPE, env=env)
        _, stderr = process.communicate()

    if process.returncode != 0:
        print(format_stderr(stderr))
        destination.unlink(missing_ok=True)
        return False

    if destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        print("下载的压缩包为空")
        return False

    print(f"下载完成: {destination}")
    return True


def open_vscode_remote(*, remote_dir: str, config: ProjectConfig) -> bool:
    command = ["code", "--remote", f"ssh-remote+{config.connection.host}", remote_dir]
    try:
        subprocess.Popen(command, shell=(os.name == "nt"))
    except FileNotFoundError:
        print("未找到 code 命令，请确认 VS Code CLI 已加入 PATH")
        return False
    return True
