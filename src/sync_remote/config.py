from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import copy
import os

import yaml

DEFAULT_CONFIG_FILENAME = "sync-remote.yaml"
LEGACY_CONFIG_FILENAME = "sync_config.yaml"

DEFAULT_SYNC_EXCLUDES = (
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".venv",
    "venv",
    "env",
    ".env",
    ".python-version",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    "uv.lock",
    ".uv",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    ".DS_Store",
    ".claude",
    ".spec-workflow",
    "skills",
    "dist",
    "build",
    "*.egg-info",
    "__pypackages__",
    "node_modules",
    ".next",
    ".output",
    ".nuxt",
    "*.bat",
    "sync_to_remote.py",
    "REMOTE_SYNC_GUIDE.md",
    DEFAULT_CONFIG_FILENAME,
    LEGACY_CONFIG_FILENAME,
    "logs",
    "*.log",
    "/data",
    "models",
    "checkpoints",
    "weights",
    "pretrained",
    "*.bin",
    "*.safetensors",
    "*.gguf",
    "*.ggml",
    "*.pt",
    "*.pth",
    "*.onnx",
    "*.h5",
    "*.pkl",
    "hub",
    ".cache",
    "cache",
    "unsloth_compiled_cache",
    ".huggingface",
    "backup",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.rar",
    "*.7z",
    "*.mp4",
    "*.avi",
    "*.mkv",
    "*.mov",
)

DEFAULT_BACKUP_EXCLUDES = (
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "node_modules",
    ".next",
    ".nuxt",
    ".output",
    "dist",
    "build",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.zip",
    "*.rar",
    "*.7z",
    ".*",
)


@dataclass(frozen=True)
class ProjectSettings:
    remote_base_dir: str
    append_project_dir: bool = True


@dataclass(frozen=True)
class ConnectionSettings:
    user: str
    host: str
    hostname: str
    port_mode: str
    port: int | None
    ssh_config_path: str
    ssh_key_path: str
    known_hosts_check: bool


@dataclass(frozen=True)
class CpolarSettings:
    tunnel_name: str
    env_path: str


@dataclass(frozen=True)
class SyncSettings:
    transport: str
    max_file_size_mb: int
    excludes: tuple[str, ...]


@dataclass(frozen=True)
class BackupSettings:
    excludes: tuple[str, ...]


@dataclass(frozen=True)
class ProjectConfig:
    version: int
    project: ProjectSettings
    connection: ConnectionSettings
    cpolar: CpolarSettings
    sync: SyncSettings
    backup: BackupSettings


def default_project_config() -> ProjectConfig:
    return default_auto_project_config()


def default_auto_project_config() -> ProjectConfig:
    return ProjectConfig(
        version=1,
        project=ProjectSettings(
            remote_base_dir="/srv/projects",
            append_project_dir=True,
        ),
        connection=ConnectionSettings(
            user="user",
            host="cpolar-server",
            hostname="example.tcp.vip.cpolar.cn",
            port_mode="auto",
            port=None,
            ssh_config_path="~/.ssh/config",
            ssh_key_path="~/.ssh/id_ed25519",
            known_hosts_check=True,
        ),
        cpolar=CpolarSettings(
            tunnel_name="my-tunnel",
            env_path="~/.env",
        ),
        sync=SyncSettings(
            transport="rsync",
            max_file_size_mb=50,
            excludes=DEFAULT_SYNC_EXCLUDES,
        ),
        backup=BackupSettings(
            excludes=DEFAULT_BACKUP_EXCLUDES,
        ),
    )


def default_fixed_project_config() -> ProjectConfig:
    return ProjectConfig(
        version=1,
        project=ProjectSettings(
            remote_base_dir="/srv/projects",
            append_project_dir=True,
        ),
        connection=ConnectionSettings(
            user="user",
            host="remote-server",
            hostname="example.com",
            port_mode="fixed",
            port=22,
            ssh_config_path="~/.ssh/config",
            ssh_key_path="~/.ssh/id_ed25519",
            known_hosts_check=True,
        ),
        cpolar=CpolarSettings(
            tunnel_name="my-tunnel",
            env_path="~/.env",
        ),
        sync=SyncSettings(
            transport="rsync",
            max_file_size_mb=50,
            excludes=DEFAULT_SYNC_EXCLUDES,
        ),
        backup=BackupSettings(
            excludes=DEFAULT_BACKUP_EXCLUDES,
        ),
    )


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _config_to_dict(config: ProjectConfig) -> dict:
    return {
        "version": config.version,
        "project": {
            "remote_base_dir": config.project.remote_base_dir,
            "append_project_dir": config.project.append_project_dir,
        },
        "connection": {
            "user": config.connection.user,
            "host": config.connection.host,
            "hostname": config.connection.hostname,
            "port_mode": config.connection.port_mode,
            "port": config.connection.port,
            "ssh_config_path": config.connection.ssh_config_path,
            "ssh_key_path": config.connection.ssh_key_path,
            "known_hosts_check": config.connection.known_hosts_check,
        },
        "cpolar": {
            "tunnel_name": config.cpolar.tunnel_name,
            "env_path": config.cpolar.env_path,
        },
        "sync": {
            "transport": config.sync.transport,
            "max_file_size_mb": config.sync.max_file_size_mb,
            "excludes": list(config.sync.excludes),
        },
        "backup": {
            "excludes": list(config.backup.excludes),
        },
    }


def _build_project_config(data: dict) -> ProjectConfig:
    defaults = _config_to_dict(default_project_config())
    merged = _deep_merge(defaults, data or {})

    port = merged["connection"].get("port")
    return ProjectConfig(
        version=int(merged.get("version", 1)),
        project=ProjectSettings(
            remote_base_dir=merged["project"]["remote_base_dir"],
            append_project_dir=bool(merged["project"].get("append_project_dir", True)),
        ),
        connection=ConnectionSettings(
            user=merged["connection"]["user"],
            host=merged["connection"]["host"],
            hostname=merged["connection"].get("hostname", ""),
            port_mode=merged["connection"].get("port_mode", "auto"),
            port=int(port) if port not in (None, "") else None,
            ssh_config_path=merged["connection"]["ssh_config_path"],
            ssh_key_path=merged["connection"]["ssh_key_path"],
            known_hosts_check=bool(merged["connection"].get("known_hosts_check", True)),
        ),
        cpolar=CpolarSettings(
            tunnel_name=merged["cpolar"].get("tunnel_name", ""),
            env_path=merged["cpolar"]["env_path"],
        ),
        sync=SyncSettings(
            transport=merged["sync"].get("transport", "rsync"),
            max_file_size_mb=int(merged["sync"].get("max_file_size_mb", 50)),
            excludes=tuple(merged["sync"].get("excludes", DEFAULT_SYNC_EXCLUDES)),
        ),
        backup=BackupSettings(
            excludes=tuple(merged["backup"].get("excludes", DEFAULT_BACKUP_EXCLUDES)),
        ),
    )


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _map_legacy_config(data: dict) -> dict:
    targets = copy.deepcopy(data.get("targets") or {})
    remote = data.get("remote") or {}
    auto = targets.get("auto") or {}
    cached = targets.get("cached") or {}
    chosen_target = auto or cached or remote
    if not chosen_target and remote:
        chosen_target = remote

    ssh_host = (
        chosen_target.get("ssh_host")
        or chosen_target.get("host")
        or remote.get("host")
        or default_project_config().connection.host
    )
    user = chosen_target.get("user") or remote.get("user") or default_project_config().connection.user
    base_dir = (
        chosen_target.get("base_dir")
        or remote.get("base_dir")
        or default_project_config().project.remote_base_dir
    )

    ssh = data.get("ssh") or {}
    cpolar = data.get("cpolar") or {}
    sync = data.get("sync") or {}

    return {
        "version": 1,
        "project": {
            "remote_base_dir": base_dir,
            "append_project_dir": bool(chosen_target.get("append_project_dir", True)),
        },
        "connection": {
            "user": user,
            "host": ssh_host,
            "hostname": "",
            "port_mode": "auto",
            "port": None,
            "ssh_config_path": ssh.get("config_path", "~/.ssh/config"),
            "ssh_key_path": ssh.get("key_path", "~/.ssh/id_ed25519"),
            "known_hosts_check": ssh.get("known_hosts_check", True),
        },
        "cpolar": {
            "tunnel_name": cpolar.get("tunnel_name", ""),
            "env_path": cpolar.get("env_path", "~/.env"),
        },
        "sync": {
            "transport": sync.get("transport", "rsync"),
            "max_file_size_mb": sync.get("max_file_size_mb", 50),
            "excludes": sync.get("excludes", list(DEFAULT_SYNC_EXCLUDES)),
        },
        "backup": {
            "excludes": list(DEFAULT_BACKUP_EXCLUDES),
        },
    }


def load_project_config(cwd: Path | str | None = None) -> tuple[ProjectConfig, Path]:
    base_dir = Path(cwd or Path.cwd())
    new_path = base_dir / DEFAULT_CONFIG_FILENAME
    legacy_path = base_dir / LEGACY_CONFIG_FILENAME

    if new_path.exists():
        return _build_project_config(_load_yaml(new_path)), new_path
    if legacy_path.exists():
        return _build_project_config(_map_legacy_config(_load_yaml(legacy_path))), legacy_path

    raise FileNotFoundError(
        f"未找到配置文件，请先在 {base_dir} 运行 `sync-remote init` 生成 {DEFAULT_CONFIG_FILENAME}"
    )


def write_project_config(config: ProjectConfig, path: Path | str) -> Path:
    destination = Path(path)
    destination.write_text(
        yaml.safe_dump(_config_to_dict(config), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return destination


def ensure_gitignore_entry(base_dir: Path | str, entry: str = DEFAULT_CONFIG_FILENAME) -> None:
    gitignore_path = Path(base_dir) / ".gitignore"
    if not gitignore_path.exists():
        return

    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    if entry in lines:
        return

    with gitignore_path.open("a", encoding="utf-8") as handle:
        if lines:
            handle.write("\n")
        handle.write(f"{entry}\n")


def prompt_for_config(input_fn=None) -> ProjectConfig:
    auto_defaults = default_auto_project_config()
    input_reader = input_fn or input

    def ask(prompt_text: str, default: str) -> str:
        answer = input_reader(f"{prompt_text} [{default}]: ").strip()
        return answer or default

    port_mode = ask("端口模式（auto/fixed）", auto_defaults.connection.port_mode).lower()
    if port_mode not in {"auto", "fixed"}:
        port_mode = auto_defaults.connection.port_mode

    defaults = default_fixed_project_config() if port_mode == "fixed" else auto_defaults

    port: int | None = None
    tunnel_name = defaults.cpolar.tunnel_name
    env_path = defaults.cpolar.env_path

    if port_mode == "fixed":
        raw_port = ask("固定 SSH 端口", str(defaults.connection.port or 22))
        port = int(raw_port)
    else:
        tunnel_name = ask("Cpolar 隧道名", defaults.cpolar.tunnel_name)
        env_path = ask("Cpolar 环境变量文件", defaults.cpolar.env_path)

    user = ask("SSH 用户", defaults.connection.user)
    host = ask("SSH Host 别名", defaults.connection.host)
    hostname = ask("SSH HostName", defaults.connection.hostname)
    remote_base_dir = ask("远端基础目录", defaults.project.remote_base_dir)

    return ProjectConfig(
        version=1,
        project=ProjectSettings(
            remote_base_dir=remote_base_dir,
            append_project_dir=True,
        ),
        connection=ConnectionSettings(
            user=user,
            host=host,
            hostname=hostname,
            port_mode=port_mode,
            port=port,
            ssh_config_path=defaults.connection.ssh_config_path,
            ssh_key_path=defaults.connection.ssh_key_path,
            known_hosts_check=defaults.connection.known_hosts_check,
        ),
        cpolar=CpolarSettings(
            tunnel_name=tunnel_name,
            env_path=env_path,
        ),
        sync=defaults.sync,
        backup=defaults.backup,
    )


def expand_user_path(value: str) -> str:
    return os.path.expanduser(value)
