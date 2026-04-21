from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import getpass
import json
import os
from pathlib import Path
import shutil
import sys
import time

from dotenv import dotenv_values

from .config import (
    CURRENT_CONFIG_VERSION,
    DEFAULT_CONFIG_FILENAME,
    config_to_v3_dict,
    delete_server as delete_config_server,
    describe_project_config,
    ensure_gitignore_entry,
    expand_user_path,
    list_server_names,
    load_project_config,
    prompt_for_config,
    set_default_host as set_config_default_host,
    update_server_port,
    validate_project_config,
    write_project_config,
)
from .operations import (
    build_remote_dir,
    create_backup_archive,
    current_timestamp,
    default_backup_archive_path,
    default_download_archive_path,
)
from .self_update import get_display_version, run_self_update
from .ssh_config import read_ssh_host_entry
from .transport import (
    download_remote_archive,
    open_vscode_remote,
    resolve_connection_port,
    should_exclude_by_pattern,
    sync_upload,
    update_ssh_port_in_config,
)


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


def _add_json_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 输出结果，适合脚本或自动化调用",
    )


def _emit_output(*, payload: dict, text_lines: list[str], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for line in text_lines:
        print(line)


def _add_common_sync_arguments(parser: argparse.ArgumentParser, *, for_open: bool, include_watch_hint: bool = False) -> None:
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
    if include_watch_hint:
        parser.add_argument(
            "--watch",
            action="store_true",
            help="上传成功并打开远端目录后，继续监听本地改动并自动同步",
        )
        parser.add_argument(
            "--debounce-ms",
            type=int,
            default=1000,
            metavar="MS",
            help="监听防抖时间，单位毫秒；默认 1000",
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
            "  sr target list\n"
            "  sr target use gpu-b\n"
            "  sr config validate\n"
            "  sr port-sync --json\n"
            "  sr switch gpu-b\n"
            "  sync-remote download\n"
            "  sr dl\n"
            "  sr upload-all-gpu\n"
            "  sr version\n"
            "  sr update --channel release\n"
            "  sync-remote open\n"
            "  sr op\n"
            "  sync-remote watch\n"
            "  sr wt"
        ),
        formatter_class=HelpFormatter,
    )
    _add_root_help_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        add_help=False,
        help="生成或追加当前目录的 sync-remote.yaml 配置",
        description=(
            "初始化当前目录的 sync-remote.yaml\n"
            "可执行命令: `sync-remote init` 或 `sr init`\n\n"
            "运行后会在当前目录生成或更新 `sync-remote.yaml`\n"
            "若检测到 `.gitignore`，会自动追加配置文件名\n"
            "若当前目录已存在配置文件，则会追加新的服务器并将其设为默认\n"
            "会优先读取本机 ~/.ssh/config 中已有的 Host\n"
            "若没有可用 Host，可在初始化过程中创建新的 SSH 配置\n\n"
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
            "  - 默认作用于配置文件中的当前默认服务器\n"
            "  - 可通过 `--hosts` 一次指定一个或多个目标服务器\n"
            "  - 默认使用配置文件中的 `sync.transport`；默认配置为 `rsync`\n"
            "  - 默认优先使用 rsync 进行增量上传\n"
            "  - 不删除远端额外文件\n"
            "  - 若本机没有 rsync，会自动回退到 archive 模式\n"
            "  - password 模式会在命令执行前提示输入服务器密码"
        ),
        epilog=(
            "示例:\n"
            "  sr up\n"
            "  sr up --dry-run\n"
            "  sr up --hosts gpu-a gpu-b\n"
            "  sr up --sync-path src README.md\n"
            "  sr up --transport archive"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(upload)
    _add_common_sync_arguments(upload, for_open=False)
    upload.add_argument(
        "--hosts",
        nargs="+",
        metavar="HOST",
        help="上传到一个或多个指定服务器；不传时仍使用当前默认服务器",
    )
    upload.add_argument(
        "--all-targets",
        action="store_true",
        help="上传到当前配置中的所有目标服务器；是 `upload-all-gpu` 的规范替代写法",
    )

    download = subparsers.add_parser(
        "download",
        aliases=["dl"],
        add_help=False,
        help="将远端目录打包下载到当前目录，不自动解压",
        description=(
            "将远端目录打包下载到当前目录。\n"
            "可执行命令: `sync-remote download`、`sync-remote dl`、`sr download`、`sr dl`\n\n"
            "行为说明:\n"
            "  - 默认作用于配置文件中的当前默认服务器\n"
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
            "  - 默认作用于配置文件中的当前默认服务器\n"
            "  - 先执行一次 upload 逻辑\n"
            "  - `--dry-run` 时仅预览上传步骤，不真正传输文件，也不会打开 VS Code\n"
            "  - 上传成功后再调用 VS Code 打开远端目录\n"
            "  - 依赖本机 `code` 命令和可用的 SSH alias"
        ),
        epilog=(
            "示例:\n"
            "  sr op\n"
            "  sr op --dry-run\n"
            "  sr op --sync-path src\n"
            "  sr op --watch"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(open_command)
    _add_common_sync_arguments(open_command, for_open=True, include_watch_hint=True)

    watch_command = subparsers.add_parser(
        "watch",
        aliases=["wt"],
        add_help=False,
        help="先上传一次，再持续监听本地变更并自动同步",
        description=(
            "先执行一次上传，再持续监听当前目录变更。\n"
            "可执行命令: `sync-remote watch`、`sync-remote wt`、`sr watch`、`sr wt`\n\n"
            "行为说明:\n"
            "  - 默认作用于配置文件中的当前默认服务器\n"
            "  - 启动时会先执行一次上传\n"
            "  - 默认防抖时间为 1000ms\n"
            "  - rsync 可用时仅同步变更路径\n"
            "  - archive 模式下会回退为重新打包上传"
        ),
        epilog=(
            "示例:\n"
            "  sr watch\n"
            "  sr wt --debounce-ms 1500\n"
            "  sr wt --sync-path src"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(watch_command)
    _add_common_sync_arguments(watch_command, for_open=False)
    watch_command.add_argument(
        "--debounce-ms",
        type=int,
        default=1000,
        metavar="MS",
        help="监听防抖时间，单位毫秒；默认 1000",
    )

    switch_command = subparsers.add_parser(
        "switch",
        add_help=False,
        help="切换默认上传服务器",
        description=(
            "切换当前项目默认使用的服务器。\n"
            "可执行命令: `sync-remote switch` 或 `sr switch`\n\n"
            "行为说明:\n"
            "  - 可直接传入 host 别名\n"
            "  - 不传时会列出已配置服务器供选择\n"
            "  - 若传入不存在的 host，会提示后回退到选择列表\n"
            "  - 切换后会更新配置中的默认服务器"
        ),
        epilog=(
            "示例:\n"
            "  sr switch gpu-b\n"
            "  sr switch"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(switch_command)
    switch_command.add_argument("host", nargs="?", help="要切换到的 Host 别名")

    delete_command = subparsers.add_parser(
        "del",
        add_help=False,
        help="删除指定服务器配置",
        description=(
            "删除当前项目中的一个服务器配置。\n"
            "可执行命令: `sync-remote del` 或 `sr del`\n\n"
            "行为说明:\n"
            "  - 可直接传入 host 别名\n"
            "  - 不传时会列出已配置服务器供选择\n"
            "  - 若传入不存在的 host，会提示后回退到选择列表\n"
            "  - 若删除默认服务器，会自动把最后一个剩余服务器设为默认"
        ),
        epilog=(
            "示例:\n"
            "  sr del gpu-b\n"
            "  sr del"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(delete_command)
    delete_command.add_argument("host", nargs="?", help="要删除的 Host 别名")

    upload_all = subparsers.add_parser(
        "upload-all-gpu",
        add_help=False,
        help="将当前目录上传到所有已配置服务器",
        description=(
            "并发把当前目录上传到配置文件中的所有服务器。\n"
            "可执行命令: `sync-remote upload-all-gpu` 或 `sr upload-all-gpu`\n\n"
            "行为说明:\n"
            "  - 内部复用 `upload --hosts <all>` 的批量上传逻辑\n"
            "  - 某个服务器失败时不会中断后续服务器\n"
            "  - 全部完成后输出成功/失败汇总"
        ),
        epilog=(
            "示例:\n"
            "  sr upload-all-gpu\n"
            "  sr upload-all-gpu --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(upload_all)
    _add_common_sync_arguments(upload_all, for_open=False)

    port_sync = subparsers.add_parser(
        "port-sync",
        add_help=False,
        help="显式预览或应用目标服务器的端口同步结果",
        description=(
            "解析当前目标服务器的 SSH 端口，并以显式预览或应用方式同步结果。\n"
            "可执行命令: `sync-remote port-sync` 或 `sr port-sync`\n\n"
            "行为说明:\n"
            "  - 默认只预览，不写配置文件，也不写 SSH config\n"
            "  - `--apply` 时会把解析结果写回项目配置\n"
            "  - 只有显式传入 `--write-ssh-config` 时才会写 SSH config"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(port_sync)
    _add_json_argument(port_sync)
    port_sync.add_argument("host", nargs="?", help="要同步端口的目标服务器；不传时使用当前默认服务器")
    port_sync.add_argument("--apply", action="store_true", help="将解析结果写回项目配置")
    port_sync.add_argument("--write-ssh-config", action="store_true", help="在 `--apply` 时同时更新 SSH config 中对应 Host 的端口")

    target_command = subparsers.add_parser(
        "target",
        add_help=False,
        help="目标服务器管理命令",
        description="目标服务器管理命令树，提供列表、切换、删除和显式端口同步。",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(target_command)
    target_subparsers = target_command.add_subparsers(dest="target_command", required=True)

    target_list = target_subparsers.add_parser(
        "list",
        add_help=False,
        help="列出当前配置中的所有目标服务器",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(target_list)
    _add_json_argument(target_list)

    target_use = target_subparsers.add_parser(
        "use",
        add_help=False,
        help="切换当前默认目标服务器",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(target_use)
    target_use.add_argument("host", nargs="?", help="要切换到的目标服务器")

    target_remove = target_subparsers.add_parser(
        "remove",
        add_help=False,
        help="删除一个目标服务器配置",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(target_remove)
    target_remove.add_argument("host", nargs="?", help="要删除的目标服务器")

    target_port_sync = target_subparsers.add_parser(
        "port-sync",
        add_help=False,
        help="显式预览或应用目标服务器的端口同步结果",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(target_port_sync)
    _add_json_argument(target_port_sync)
    target_port_sync.add_argument("host", nargs="?", help="要同步端口的目标服务器；不传时使用当前默认服务器")
    target_port_sync.add_argument("--apply", action="store_true", help="将解析结果写回项目配置")
    target_port_sync.add_argument("--write-ssh-config", action="store_true", help="在 `--apply` 时同时更新 SSH config 中对应 Host 的端口")

    config_command = subparsers.add_parser(
        "config",
        add_help=False,
        help="配置检查、解释和迁移命令",
        description="配置检查、解释和迁移命令树。",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(config_command)
    config_subparsers = config_command.add_subparsers(dest="config_command", required=True)

    config_validate = config_subparsers.add_parser(
        "validate",
        add_help=False,
        help="检查当前项目配置是否可读取",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(config_validate)
    _add_json_argument(config_validate)

    config_explain = config_subparsers.add_parser(
        "explain",
        add_help=False,
        help="解释当前配置的默认目标和目标列表",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(config_explain)
    _add_json_argument(config_explain)

    config_migrate = config_subparsers.add_parser(
        "migrate",
        add_help=False,
        help="预览或应用 v3 规范化配置迁移",
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(config_migrate)
    _add_json_argument(config_migrate)
    config_migrate.add_argument("--apply", action="store_true", help="将当前配置写回为 v3 规范化格式")

    version_command = subparsers.add_parser(
        "version",
        add_help=False,
        help="显示当前安装版本号",
        description=(
            "显示当前安装版本号。\n"
            "可执行命令: `sync-remote version` 或 `sr version`\n\n"
            "若当前安装来自 main 通道，会显示类似 `0.4.3-main-YYYY-MM-DD` 的展示版本。"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(version_command)

    update_command = subparsers.add_parser(
        "update",
        add_help=False,
        help="从 GitHub 更新当前工具版本",
        description=(
            "从 GitHub 更新当前工具版本。\n"
            "可执行命令: `sync-remote update` 或 `sr update`\n\n"
            "行为说明:\n"
            "  - 仅支持通过 `uv tool install` 安装的命令进行自动更新\n"
            "  - 默认优先使用最新 Release\n"
            "  - 若最新 Release/Tag 版本低于当前基线版本，则自动切换到 main\n"
            "  - 支持显式指定 `main` 或 `release` 通道"
        ),
        formatter_class=HelpFormatter,
    )
    _add_command_help_argument(update_command)
    update_command.add_argument(
        "--channel",
        choices=["main", "release"],
        metavar="{main,release}",
        help="指定更新通道；默认根据当前版本和最新 Release 自动选择",
    )

    status = subparsers.add_parser(
        "status",
        add_help=False,
        help="显示当前配置、远端目录和端口解析结果",
        description=(
            "显示当前默认服务器、生效配置、SSH 目标、SSH 文件状态、远端目录和端口解析结果。\n"
            "会显示服务器列表、认证方式、SSH 配置文件、私钥、公钥和别名状态。\n"
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
            "检查 ssh、rsync、code、sshpass、配置文件、SSH 文件和端口解析状态。\n"
            "会检查当前默认服务器对应的 SSH 配置文件、私钥、公钥、别名以及 password 模式所需的 sshpass。\n"
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


def _select_host_from_config(config, *, prompt_text: str = "选择服务器") -> str | None:
    hosts = list_server_names(config)
    if not hosts:
        print("当前配置中没有可用服务器")
        return None

    print("可用服务器：")
    default_index = 1
    for index, host in enumerate(hosts, start=1):
        suffix = " (default)" if host == config.default_host else ""
        if host == config.default_host:
            default_index = index
        print(f"  {index}. {host}{suffix}")

    selection = input(f"{prompt_text} [{default_index}]: ").strip() or str(default_index)
    try:
        selected_index = int(selection)
    except ValueError:
        print(f"无效选择: {selection}")
        return None
    if not 1 <= selected_index <= len(hosts):
        print(f"无效选择: {selection}")
        return None
    return hosts[selected_index - 1]


def _resolve_requested_host(config, requested_host: str | None) -> str | None:
    if requested_host and requested_host in config.servers:
        return requested_host
    if requested_host:
        print(f"未找到服务器: {requested_host}")
    return _select_host_from_config(config)


def _handle_init() -> int:
    project_dir = Path.cwd()
    try:
        existing_config, _existing_path = load_project_config(project_dir)
    except FileNotFoundError:
        existing_config = None

    config = prompt_for_config(existing_config=existing_config)
    config_path = write_project_config(config, project_dir / DEFAULT_CONFIG_FILENAME)
    ensure_gitignore_entry(project_dir, DEFAULT_CONFIG_FILENAME)
    print(f"配置已写入: {config_path}")
    return 0


def _ssh_config_file(config) -> Path:
    return Path(expand_user_path(config.connection.ssh_config_path))


def _ssh_private_key_file(config) -> Path:
    return Path(expand_user_path(config.connection.ssh_key_path))


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


def _ssh_alias_status(config) -> str:
    entry = read_ssh_host_entry(_ssh_config_file(config), config.connection.host)
    return "OK" if entry is not None else "MISSING"


def _cpolar_env_status(config) -> str:
    if config.connection.port_mode != "auto":
        return "SKIPPED (fixed mode)"
    env_path = Path(expand_user_path(config.cpolar.env_path))
    status = "OK" if env_path.exists() else "MISSING"
    return f"{status} ({env_path})"


def _cpolar_credentials_status(config) -> str:
    if config.connection.port_mode != "auto":
        return "SKIPPED (fixed mode)"
    env_path = Path(expand_user_path(config.cpolar.env_path))
    values = dict(dotenv_values(env_path)) if env_path.exists() else {}
    username = os.environ.get("CPOLAR_USER") or values.get("CPOLAR_USER")
    password = os.environ.get("CPOLAR_PASS") or values.get("CPOLAR_PASS")
    status = "OK" if username and password else "MISSING"
    return f"{status} ({env_path})"


def _sshpass_status(config) -> str:
    if config.connection.auth_mode != "password":
        return "SKIPPED (key mode)"
    resolved = shutil.which("sshpass")
    return f"OK ({resolved})" if resolved else "MISSING"


def _resolve_runtime_password(config) -> str | None:
    if config.connection.auth_mode != "password":
        return None
    if shutil.which("sshpass") is None:
        print("当前配置使用 password 认证，但未找到 sshpass")
        return None
    return getpass.getpass("服务器密码: ")


def _resolve_port_for_command(config, *, explicit_port: str | None):
    port = resolve_connection_port(config, explicit_port=explicit_port)
    return port, config


def _normalize_requested_hosts(config, raw_hosts: tuple[str, ...]) -> tuple[str, ...] | None:
    hosts = tuple(dict.fromkeys(raw_hosts))
    missing_hosts = tuple(host for host in hosts if host not in config.servers)
    if not missing_hosts:
        return hosts

    print(f"未找到服务器: {', '.join(missing_hosts)}")
    print(f"可用服务器: {', '.join(list_server_names(config))}")
    return None


def _perform_upload(args: argparse.Namespace, *, config, remote_dir: str, port: str, password: str | None, sync_paths: tuple[str, ...] | None = None) -> bool:
    return sync_upload(
        local_dir=Path.cwd(),
        remote_dir=remote_dir,
        port=port,
        config=config,
        dry_run=args.dry_run,
        list_excluded=not args.no_list_excluded,
        transport=args.transport,
        sync_paths=tuple(sync_paths if sync_paths is not None else (args.sync_path or ())),
        extra_excludes=tuple(args.exclude or ()),
        max_size_mb=args.max_size,
        password=password,
    )


def _run_upload_to_hosts(args: argparse.Namespace, *, config, hosts: tuple[str, ...]) -> int:
    target_hosts = _normalize_requested_hosts(config, hosts)
    if target_hosts is None:
        return 1

    prepared_targets: list[tuple[str, object, str, str, str | None]] = []
    failures: dict[str, str] = {}

    for host in target_hosts:
        host_config = set_config_default_host(config, host)
        try:
            port = resolve_connection_port(host_config, explicit_port=args.port)
        except RuntimeError as exc:
            failures[host] = str(exc)
            continue

        password = _resolve_runtime_password(host_config)
        if host_config.connection.auth_mode == "password" and password is None:
            failures[host] = "未提供 password 模式所需密码或缺少 sshpass"
            continue

        prepared_targets.append((host, host_config, _resolve_remote_dir(host_config), port, password))

    results: dict[str, bool] = {}
    if prepared_targets:
        with ThreadPoolExecutor(max_workers=len(prepared_targets)) as executor:
            future_to_host = {
                executor.submit(
                    _perform_upload,
                    args,
                    config=host_config,
                    remote_dir=remote_dir,
                    port=port,
                    password=password,
                ): host
                for host, host_config, remote_dir, port, password in prepared_targets
            }
            for future in as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    results[host] = future.result()
                except Exception as exc:  # pragma: no cover - defensive guard around thread futures
                    results[host] = False
                    failures[host] = str(exc)

    successes = [host for host in target_hosts if results.get(host)]
    for host in target_hosts:
        if host in failures:
            continue
        if results.get(host) is False:
            failures[host] = "上传失败"

    print("上传汇总:")
    print(f"成功: {', '.join(successes) if successes else '<none>'}")
    if failures:
        print("失败:")
        for host in target_hosts:
            if host in failures:
                print(f"  - {host}: {failures[host]}")
    else:
        print("失败: <none>")
    return 0 if not failures else 1


def _collect_watch_snapshot(project_dir: Path, *, exclude_patterns: tuple[str, ...]) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for current_root, dirs, filenames in os.walk(project_dir, topdown=True):
        current_path = Path(current_root)
        dirs[:] = [
            directory
            for directory in dirs
            if not should_exclude_by_pattern(current_path / directory, project_dir, exclude_patterns)
        ]
        for filename in filenames:
            file_path = current_path / filename
            if should_exclude_by_pattern(file_path, project_dir, exclude_patterns):
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue
            snapshot[file_path.relative_to(project_dir).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def iter_change_batches(project_dir: Path, *, exclude_patterns: tuple[str, ...], debounce_ms: int):
    previous = _collect_watch_snapshot(project_dir, exclude_patterns=exclude_patterns)
    interval = max(debounce_ms / 1000.0, 0.2)
    while True:
        time.sleep(interval)
        current = _collect_watch_snapshot(project_dir, exclude_patterns=exclude_patterns)
        changed = {
            path
            for path, state in current.items()
            if previous.get(path) != state
        }
        changed.update(path for path in previous if path not in current)
        previous = current
        if changed:
            yield changed


def _restrict_watch_paths(changed_paths: set[str], selected_paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized = sorted(path for path in changed_paths)
    if not selected_paths:
        return tuple(normalized)

    allowed = [Path(path).as_posix().rstrip("/") for path in selected_paths]
    filtered = [
        path
        for path in normalized
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in allowed)
    ]
    return tuple(filtered)


def _run_watch_loop(args: argparse.Namespace, *, config, remote_dir: str, port: str, password: str | None) -> int:
    project_dir = Path.cwd()
    excludes = tuple(config.sync.excludes) + tuple(args.exclude or ())
    selected_paths = tuple(Path(path).as_posix().rstrip("/") for path in (args.sync_path or ()))
    try:
        for changed_paths in iter_change_batches(
            project_dir,
            exclude_patterns=excludes,
            debounce_ms=max(args.debounce_ms, 100),
        ):
            sync_paths = _restrict_watch_paths(changed_paths, selected_paths)
            if not sync_paths:
                continue
            existing_sync_paths = tuple(path for path in sync_paths if (project_dir / path).exists())
            if not existing_sync_paths and (args.transport or config.sync.transport) == "rsync":
                print("检测到的改动仅包含删除或已不存在的路径，跳过本次同步")
                continue
            success = _perform_upload(
                args,
                config=config,
                remote_dir=remote_dir,
                port=port,
                password=password,
                sync_paths=existing_sync_paths if existing_sync_paths else (),
            )
            if not success:
                print("监听同步失败，等待下一次改动...")
    except KeyboardInterrupt:
        print("已停止监听")
    return 0


def _handle_upload(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    if args.all_targets:
        return _run_upload_to_hosts(
            args,
            config=config,
            hosts=list_server_names(config),
        )
    if args.hosts:
        return _run_upload_to_hosts(
            args,
            config=config,
            hosts=tuple(args.hosts),
        )

    remote_dir = _resolve_remote_dir(config)

    try:
        port, config = _resolve_port_for_command(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    password = _resolve_runtime_password(config)
    if config.connection.auth_mode == "password" and password is None:
        return 1

    success = _perform_upload(args, config=config, remote_dir=remote_dir, port=port, password=password)
    return 0 if success else 1


def _handle_download(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port, config = _resolve_port_for_command(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    password = _resolve_runtime_password(config)
    if config.connection.auth_mode == "password" and password is None:
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
        password=password,
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

    config, config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port, config = _resolve_port_for_command(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    password = _resolve_runtime_password(config)
    if config.connection.auth_mode == "password" and password is None:
        return 1

    success = _perform_upload(args, config=config, remote_dir=remote_dir, port=port, password=password)
    if not success:
        return 1
    if args.dry_run:
        return 0
    if not open_vscode_remote(remote_dir=remote_dir, config=config):
        return 1
    if not args.watch:
        return 0
    return _run_watch_loop(args, config=config, remote_dir=remote_dir, port=port, password=password)


def _handle_watch(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    remote_dir = _resolve_remote_dir(config)

    try:
        port, config = _resolve_port_for_command(config, explicit_port=args.port)
    except RuntimeError as exc:
        print(exc)
        return 1

    password = _resolve_runtime_password(config)
    if config.connection.auth_mode == "password" and password is None:
        return 1

    success = _perform_upload(args, config=config, remote_dir=remote_dir, port=port, password=password)
    if not success:
        return 1
    return _run_watch_loop(args, config=config, remote_dir=remote_dir, port=port, password=password)


def _handle_switch(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    target_host = _resolve_requested_host(config, args.host)
    if target_host is None:
        return 1
    if target_host == config.default_host:
        print(f"默认服务器已是: {target_host}")
        return 0

    updated_config = set_config_default_host(config, target_host)
    write_project_config(updated_config, config_path)
    print(f"默认服务器已切换为: {target_host}")
    return 0


def _handle_delete(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    target_host = _resolve_requested_host(config, args.host)
    if target_host is None:
        return 1

    try:
        updated_config = delete_config_server(config, target_host)
    except ValueError as exc:
        print(exc)
        return 1

    write_project_config(updated_config, config_path)
    print(f"已删除服务器: {target_host}")
    print(f"当前默认服务器: {updated_config.default_host}")
    return 0


def _handle_target_list(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    payload = {
        "default_target": config.default_host,
        "targets": [
            {"name": host, "default": host == config.default_host}
            for host in list_server_names(config)
        ],
    }
    text_lines = [
        f"默认目标服务器: {config.default_host}",
        "目标服务器列表:",
        *[
            f"  - {item['name']}{' (default)' if item['default'] else ''}"
            for item in payload["targets"]
        ],
    ]
    _emit_output(payload=payload, text_lines=text_lines, as_json=args.json)
    return 0


def _handle_target_use(args: argparse.Namespace) -> int:
    return _handle_switch(args)


def _handle_target_remove(args: argparse.Namespace) -> int:
    return _handle_delete(args)


def _handle_port_sync(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    target_host = _resolve_requested_host(config, getattr(args, "host", None) or config.default_host)
    if target_host is None:
        return 1

    target_config = set_config_default_host(config, target_host)
    try:
        port = resolve_connection_port(target_config, explicit_port=None)
    except RuntimeError as exc:
        print(exc)
        return 1

    resolved_port = int(port)
    config_would_change = target_config.connection.port != resolved_port
    ssh_would_change = bool(args.write_ssh_config)
    payload = {
        "target": target_host,
        "mode": target_config.connection.port_mode,
        "resolved_port": resolved_port,
        "preview": not args.apply,
        "config_would_change": config_would_change,
        "ssh_would_change": ssh_would_change,
    }

    if not args.apply:
        _emit_output(
            payload=payload,
            text_lines=[
                f"目标服务器: {target_host}",
                f"端口模式: {target_config.connection.port_mode}",
                f"解析端口: {resolved_port}",
                f"项目配置将更新: {'yes' if config_would_change else 'no'}",
                f"SSH config 将更新: {'yes' if ssh_would_change else 'no'}",
            ],
            as_json=args.json,
        )
        return 0

    updated_config = config
    if config_would_change:
        updated_config = update_server_port(config, target_host, resolved_port)
        write_project_config(updated_config, config_path)

    if args.write_ssh_config:
        update_ssh_port_in_config(port, set_config_default_host(updated_config, target_host))

    payload.update(
        {
            "preview": False,
            "config_updated": config_would_change,
            "ssh_updated": bool(args.write_ssh_config),
            "schema_version": CURRENT_CONFIG_VERSION,
        }
    )
    _emit_output(
        payload=payload,
        text_lines=[
            f"目标服务器: {target_host}",
            f"已同步端口: {resolved_port}",
            f"项目配置已更新: {'yes' if config_would_change else 'no'}",
            f"SSH config 已更新: {'yes' if args.write_ssh_config else 'no'}",
        ],
        as_json=args.json,
    )
    return 0


def _handle_upload_all(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, _config_path = loaded
    return _run_upload_to_hosts(
        args,
        config=config,
        hosts=list_server_names(config),
    )


def _handle_config_validate(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    payload = validate_project_config(config, config_path)
    _emit_output(
        payload=payload,
        text_lines=[
            f"配置文件: {config_path}",
            f"配置版本: {config.version}",
            f"默认目标服务器: {config.default_host}",
            "配置校验结果: OK",
        ],
        as_json=args.json,
    )
    return 0


def _handle_config_explain(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    payload = describe_project_config(config, config_path)
    _emit_output(
        payload=payload,
        text_lines=[
            f"配置文件: {config_path}",
            f"当前配置版本: {config.version}",
            f"规范化写回版本: {CURRENT_CONFIG_VERSION}",
            f"默认目标服务器: {config.default_host}",
            f"目标服务器: {', '.join(list_server_names(config))}",
        ],
        as_json=args.json,
    )
    return 0


def _handle_config_migrate(args: argparse.Namespace) -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    normalized = config_to_v3_dict(config)
    payload = {
        "preview": not args.apply,
        "source_path": str(config_path),
        "current_version": config.version,
        "target_version": CURRENT_CONFIG_VERSION,
        "normalized": normalized,
    }

    if not args.apply:
        _emit_output(
            payload=payload,
            text_lines=[
                f"配置文件: {config_path}",
                f"当前版本: {config.version}",
                f"目标版本: {CURRENT_CONFIG_VERSION}",
                "当前操作: preview",
            ],
            as_json=args.json,
        )
        return 0

    write_project_config(config, config_path)
    payload["preview"] = False
    _emit_output(
        payload=payload,
        text_lines=[
            f"配置文件: {config_path}",
            f"已迁移为版本 {CURRENT_CONFIG_VERSION}",
        ],
        as_json=args.json,
    )
    return 0


def _handle_version() -> int:
    print(f"sync-remote {get_display_version()}")
    return 0


def _handle_update(args: argparse.Namespace) -> int:
    success, message = run_self_update(channel=args.channel)
    print(message)
    return 0 if success else 1


def _handle_status() -> int:
    loaded = _load_config_or_report()
    if loaded is None:
        return 1

    config, config_path = loaded
    remote_dir = _resolve_remote_dir(config)
    ssh_config = _ssh_config_file(config)
    ssh_private_key = _ssh_private_key_file(config)
    ssh_public_key = _ssh_public_key_file(config)

    print(f"配置文件: {config_path}")
    print(f"默认服务器: {config.default_host}")
    print("服务器列表:")
    for host in list_server_names(config):
        suffix = " (default)" if host == config.default_host else ""
        print(f"  - {host}{suffix}")
    print(f"认证方式: {config.connection.auth_mode}")
    print(f"端口模式: {config.connection.port_mode}")
    print(f"SSH Host: {config.connection.host}")
    print(f"SSH HostName: {config.connection.hostname or '<none>'}")
    print(f"SSH 配置文件: {_path_check_status(ssh_config)} ({ssh_config})")
    print(f"SSH 私钥: {_path_check_status(ssh_private_key)} ({ssh_private_key})")
    print(f"SSH 公钥: {_path_check_status(ssh_public_key)} ({ssh_public_key})")
    print(f"SSH Alias: {_ssh_alias_status(config)}")
    print(f"Cpolar 环境文件: {_cpolar_env_status(config)}")
    print(f"Cpolar 凭证: {_cpolar_credentials_status(config)}")
    print(f"sshpass: {_sshpass_status(config)}")
    print(f"远端目录: {remote_dir}")
    try:
        port, _updated_config = _resolve_port_for_command(config, explicit_port=None)
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
    print(f"sshpass: {_sshpass_status(config)}")
    ssh_config = _ssh_config_file(config)
    ssh_private_key = _ssh_private_key_file(config)
    ssh_public_key = _ssh_public_key_file(config)
    print(f"ssh_config: {_path_check_status(ssh_config)} ({ssh_config})")
    print(f"ssh_private_key: {_path_check_status(ssh_private_key)} ({ssh_private_key})")
    print(f"ssh_public_key: {_path_check_status(ssh_public_key)} ({ssh_public_key})")
    print(f"ssh_alias: {_ssh_alias_status(config)}")
    print(f"cpolar_env: {_cpolar_env_status(config)}")
    print(f"cpolar_credentials: {_cpolar_credentials_status(config)}")
    try:
        port, _updated_config = _resolve_port_for_command(config, explicit_port=None)
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
    if args.command in {"watch", "wt"}:
        return _handle_watch(args)
    if args.command == "switch":
        return _handle_switch(args)
    if args.command == "del":
        return _handle_delete(args)
    if args.command == "upload-all-gpu":
        return _handle_upload_all(args)
    if args.command == "port-sync":
        return _handle_port_sync(args)
    if args.command == "target":
        if args.target_command == "list":
            return _handle_target_list(args)
        if args.target_command == "use":
            return _handle_target_use(args)
        if args.target_command == "remove":
            return _handle_target_remove(args)
        if args.target_command == "port-sync":
            return _handle_port_sync(args)
    if args.command == "config":
        if args.config_command == "validate":
            return _handle_config_validate(args)
        if args.config_command == "explain":
            return _handle_config_explain(args)
        if args.config_command == "migrate":
            return _handle_config_migrate(args)
    if args.command == "version":
        return _handle_version()
    if args.command == "update":
        return _handle_update(args)
    if args.command == "status":
        return _handle_status()
    if args.command == "doctor":
        return _handle_doctor()

    parser.print_help()
    return 1


def run() -> None:
    raise SystemExit(main())
