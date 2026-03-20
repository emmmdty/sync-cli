from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

from .config import (
    DEFAULT_CONFIG_FILENAME,
    ensure_gitignore_entry,
    expand_user_path,
    load_project_config,
    prompt_for_config,
    write_project_config,
)
from .operations import (
    build_remote_dir,
    create_backup_archive,
    current_timestamp,
    default_backup_archive_path,
    default_download_archive_path,
)
from .transport import download_remote_archive, open_vscode_remote, resolve_connection_port, sync_upload


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    pass


def _add_root_help_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示顶层帮助并列出所有子命令",
    )


def _add_command_help_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示当前子命令的帮助信息并退出",
    )


def _add_common_sync_arguments(parser: argparse.ArgumentParser, *, for_open: bool) -> None:
    dry_run_help = "仅预览将要执行的上传操作，不真正传输文件"
    if for_open:
        dry_run_help = "仅预览上传步骤，不真正传输文件，也不会打开 VS Code"

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=dry_run_help,
    )
    parser.add_argument(
        "--transport",
        choices=["rsync", "archive"],
        metavar="MODE",
        help="指定传输方式；默认使用配置文件中的 `sync.transport`；默认配置为 `rsync`，无 rsync 时自动回退 `archive`",
    )
    parser.add_argument(
        "--sync-path",
        nargs="+",
        metavar="PATH",
        help="只同步指定的文件或目录；需要本机安装 rsync",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="PATTERN",
        help="额外排除指定路径或模式；会叠加配置文件中的 excludes",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        metavar="MB",
        help="覆盖配置中的最大文件大小限制，单位 MB",
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        help="临时覆盖本次连接端口，优先级高于配置和自动解析",
    )
    parser.add_argument(
        "--no-list-excluded",
        action="store_true",
        help="不输出排除文件统计信息",
    )


def _build_parser(*, prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        add_help=False,
        description=(
            "远程同步命令行工具\n\n"
            "命令名称:\n"
            "  sync-remote  完整命令名\n"
            "  sr           简写别名"
        ),
        epilog=(
            "常用示例:\n"
            "  sync-remote init\n"
            "  sync-remote upload --dry-run\n"
            "  sr upload\n"
            "  sr up\n"
            "  sync-remote download\n"
            "  sr dl\n"
            "  sync-remote open\n"
            "  sr op"
        ),
        formatter_class=HelpFormatter,
    )
    _add_root_help_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        add_help=False,
        help="初始化当前目录的 sync-remote.yaml 配置文件",
        description=(
            "初始化当前目录的 sync-remote.yaml\n"
            "可执行命令: `sync-remote init` 或 `sr init`\n\n"
            "运行后会在当前目录生成 `sync-remote.yaml`\n"
            "若检测到 `.gitignore`，会自动追加配置文件名\n\n"
            "端口模式:\n"
            "  auto: 自动模式，优先从 Cpolar 获取端口，失败时回退 ~/.ssh/config\n"
            "  fixed: 固定模式，直接使用配置中的固定端口，不访问 Cpolar"
        ),
        epilog=(
            "示例:\n"
            "  sr init\n"
            "  sync-remote init"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(init_parser)

    upload = subparsers.add_parser(
        "upload",
        aliases=["up"],
        add_help=False,
        help="将当前目录的本地变更增量上传到远端目录",
        description=(
            "增量上传当前目录到远端目录。\n"
            "可执行命令: `sync-remote upload`、`sync-remote up`、`sr upload`、`sr up`\n\n"
            "行为说明:\n"
            "  - 默认使用配置文件中的 `sync.transport`；默认配置为 `rsync`\n"
            "  - 默认优先使用 rsync 进行增量上传\n"
            "  - 不删除远端额外文件\n"
            "  - 若本机没有 rsync，会自动回退到 archive 模式"
        ),
        epilog=(
            "示例:\n"
            "  sr up\n"
            "  sr up --dry-run\n"
            "  sr up --sync-path src README.md\n"
            "  sr up --transport archive"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(upload)
    _add_common_sync_arguments(upload, for_open=False)

    download = subparsers.add_parser(
        "download",
        aliases=["dl"],
        add_help=False,
        help="将远端目录打包下载到当前目录，不自动解压",
        description=(
            "将远端目录打包下载到当前目录。\n"
            "可执行命令: `sync-remote download`、`sync-remote dl`、`sr download`、`sr dl`\n\n"
            "行为说明:\n"
            "  - 下载结果为 tar.gz 压缩包\n"
            "  - 默认保存在当前目录，文件名为 `<项目名>-时间戳.tar.gz`\n"
            "  - 不会自动解压到本地目录"
        ),
        epilog=(
            "示例:\n"
            "  sr dl\n"
            "  sr dl --output ./remote-snapshot.tar.gz"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(download)
    download.add_argument(
        "--port",
        metavar="PORT",
        help="临时覆盖本次连接端口，优先级高于配置和自动解析",
    )
    download.add_argument(
        "--output",
        metavar="FILE",
        help="自定义输出压缩包路径；默认输出到当前目录",
    )

    backup = subparsers.add_parser(
        "backup",
        add_help=False,
        help="将当前目录压缩备份到上级目录",
        description=(
            "将当前目录压缩备份到上级目录。\n"
            "可执行命令: `sync-remote backup` 或 `sr backup`\n\n"
            "行为说明:\n"
            "  - 默认输出到当前目录的上级目录\n"
            "  - 默认文件名为 `<项目名>-backup-时间戳.tar.gz`\n"
            "  - 会跳过 `.git`、虚拟环境、`node_modules` 和隐藏目录"
        ),
        epilog=(
            "示例:\n"
            "  sr backup\n"
            "  sr backup --output ../my-project-backup.tar.gz"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(backup)
    backup.add_argument(
        "--output",
        metavar="FILE",
        help="自定义备份压缩包路径；默认文件名为 `<项目名>-backup-时间戳.tar.gz`",
    )

    open_command = subparsers.add_parser(
        "open",
        aliases=["op"],
        add_help=False,
        help="先增量上传，再通过 VS Code Remote SSH 打开远端目录",
        description=(
            "先增量上传当前目录，再通过 VS Code Remote SSH 打开远端目录。\n"
            "可执行命令: `sync-remote open`、`sync-remote op`、`sr open`、`sr op`\n\n"
            "行为说明:\n"
            "  - 先执行一次 upload 逻辑\n"
            "  - `--dry-run` 时仅预览上传步骤，不真正传输文件，也不会打开 VS Code\n"
            "  - 上传成功后再调用 VS Code 打开远端目录\n"
            "  - 依赖本机 `code` 命令和可用的 SSH alias"
        ),
        epilog=(
            "示例:\n"
            "  sr op\n"
            "  sr op --dry-run\n"
            "  sr op --sync-path src"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(open_command)
    _add_common_sync_arguments(open_command, for_open=True)

    status = subparsers.add_parser(
        "status",
        add_help=False,
        help="显示当前配置、远端目录和端口解析结果",
        description=(
            "显示当前生效的配置文件、SSH 目标、SSH 配置文件和公钥状态、远端目录和端口解析结果。\n"
            "适合在 upload/download/open 前先确认配置解析结果。"
        ),
        epilog=(
            "示例:\n"
            "  sr status\n"
            "  sync-remote status"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(status)

    doctor = subparsers.add_parser(
        "doctor",
        add_help=False,
        help="检查本机依赖、配置文件和端口解析状态",
        description=(
            "检查 ssh、rsync、code、配置文件、SSH 配置文件和公钥是否存在，以及端口解析状态。\n"
            "适合在首次联机前排查环境问题。"
        ),
        epilog=(
            "示例:\n"
            "  sr doctor\n"
            "  sync-remote doctor"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(doctor)
    return parser


def _load_config_or_report() -> tuple[object, Path] | None:
    try:
        return load_project_config(Path.cwd())
    except FileNotFoundError as exc:
        print(exc)
        return None


def _handle_init() -> int:
    project_dir = Path.cwd()
    config = prompt_for_config()
    config_path = write_project_config(config, project_dir / DEFAULT_CONFIG_FILENAME)
    ensure_gitignore_entry(project_dir, DEFAULT_CONFIG_FILENAME)
    print(f"配置已写入: {config_path}")
    return 0


def _ssh_config_file(config) -> Path:
    return Path(expand_user_path(config.connection.ssh_config_path))


def _ssh_public_key_file(config) -> Path:
    configured_key = expand_user_path(config.connection.ssh_key_path)
    if configured_key.endswith(".pub"):
        return Path(configured_key)
    return Path(f"{configured_key}.pub")


def _path_check_status(path: Path) -> str:
    return "OK" if path.exists() else "MISSING"


def _resolve_remote_dir(config) -> str:
    return build_remote_dir(
        config.project.remote_base_dir,
        Path.cwd(),
        append_project_dir=config.project.append_project_dir,
    )


def _handle_upload(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port = resolve_connection_port(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    success = sync_upload(
        local_dir=Path.cwd(),
        remote_dir=remote_dir,
        port=port,
        config=config,
        dry_run=args.dry_run,
        list_excluded=not args.no_list_excluded,
        transport=args.transport,
        sync_paths=tuple(args.sync_path or ()),
        extra_excludes=tuple(args.exclude or ()),
        max_size_mb=args.max_size,
    )
    return 0 if success else 1


def _handle_download(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port = resolve_connection_port(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    output_path = Path(args.output).resolve() if args.output else default_download_archive_path(
        Path.cwd(),
        current_timestamp(),
    )
    success = download_remote_archive(
        local_dir=Path.cwd(),
        remote_dir=remote_dir,
        port=port,
        output_path=output_path,
        config=config,
    )
    return 0 if success else 1


def _handle_backup(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    output_path = Path(args.output).resolve() if args.output else default_backup_archive_path(
        Path.cwd(),
        current_timestamp(),
    )
    success = create_backup_archive(
        local_dir=Path.cwd(),
        output_path=output_path,
        config=config,
    )
    return 0 if success else 1


def _handle_open(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port = resolve_connection_port(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    success = sync_upload(
        local_dir=Path.cwd(),
        remote_dir=remote_dir,
        port=port,
        config=config,
        dry_run=args.dry_run,
        list_excluded=not args.no_list_excluded,
        transport=args.transport,
        sync_paths=tuple(args.sync_path or ()),
        extra_excludes=tuple(args.exclude or ()),
        max_size_mb=args.max_size,
    )
    if not success:
        return 1
    if args.dry_run:
        return 0
    return 0 if open_vscode_remote(remote_dir=remote_dir, config=config) else 1


def _handle_status() -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    print(f"配置文件: {config_path}")
    print(f"SSH Host: {config.connection.host}")
    print(f"SSH HostName: {config.connection.hostname or '<none>'}")
    ssh_config = _ssh_config_file(config)
    ssh_public_key = _ssh_public_key_file(config)
    print(f"SSH 配置文件: {_path_check_status(ssh_config)} ({ssh_config})")
    print(f"SSH 公钥: {_path_check_status(ssh_public_key)} ({ssh_public_key})")
    print(f"远端目录: {remote_dir}")
    try:
        port = resolve_connection_port(config)
        print(f"端口: {port}")
    except RuntimeError as exc:
        print(f"端口: 未解析 ({exc})")
    return 0


def _handle_doctor() -> int:
    checks = {
        "ssh": shutil.which("ssh"),
        "rsync": shutil.which("rsync"),
        "code": shutil.which("code"),
    }
    for name, resolved in checks.items():
        status = "OK" if resolved else "MISSING"
        print(f"{name}: {status}{f' ({resolved})' if resolved else ''}")

    try:
        config, config_path = load_project_config(Path.cwd())
    except FileNotFoundError as exc:
        print(exc)
        return 1

    print(f"config: OK ({config_path})")
    ssh_config = _ssh_config_file(config)
    ssh_public_key = _ssh_public_key_file(config)
    print(f"ssh_config: {_path_check_status(ssh_config)} ({ssh_config})")
    print(f"ssh_public_key: {_path_check_status(ssh_public_key)} ({ssh_public_key})")
    try:
        port = resolve_connection_port(config)
        print(f"port: OK ({port})")
    except RuntimeError as exc:
        print(f"port: ERROR ({exc})")
    return 0


def _resolve_prog_name() -> str:
    invoked_as = Path(sys.argv[0]).name
    return invoked_as if invoked_as in {"sync-remote", "sr"} else "sync-remote"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser(prog=_resolve_prog_name())
    args = parser.parse_args(argv)

    if args.command == "init":
        return _handle_init()
    if args.command in {"upload", "up"}:
        return _handle_upload(args)
    if args.command in {"download", "dl"}:
        return _handle_download(args)
    if args.command == "backup":
        return _handle_backup(args)
    if args.command in {"open", "op"}:
        return _handle_open(args)
    if args.command == "status":
        return _handle_status()
    if args.command == "doctor":
        return _handle_doctor()

    parser.print_help()
    return 1


def run() -> None:
    raise SystemExit(main())
