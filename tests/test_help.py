from __future__ import annotations

import pytest

from sync_remote.cli import main


def test_top_level_help_mentions_both_command_names_and_examples(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote" in captured.out
    assert "远程同步命令行工具" in captured.out
    assert "sync-remote  完整命令名" in captured.out
    assert "sr           简写别名" in captured.out
    assert "upload (up)" in captured.out
    assert "download (dl)" in captured.out
    assert "open (op)" in captured.out
    assert "显示顶层帮助并列出所有子命令" in captured.out
    assert "常用示例:" in captured.out
    assert "sync-remote upload --dry-run" in captured.out
    assert "sr upload" in captured.out
    assert "sr up" in captured.out
    assert "sync-remote download" in captured.out
    assert "sr dl" in captured.out
    assert "sync-remote open" in captured.out
    assert "sr op" in captured.out
    assert "watch (wt)" in captured.out
    assert "target" in captured.out
    assert "config" in captured.out
    assert "port-sync" in captured.out
    assert "switch" in captured.out
    assert "del" in captured.out
    assert "upload-all-gpu" in captured.out
    assert "version" in captured.out
    assert "update" in captured.out
    assert "sr target list" in captured.out
    assert "sr config validate" in captured.out
    assert "sr port-sync --json" in captured.out


def test_init_help_explains_generated_config_and_modes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["init", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote init" in captured.out
    assert "运行后会在当前目录生成或更新 `sync-remote.yaml`" in captured.out
    assert "若检测到 `.gitignore`，会自动追加配置文件名" in captured.out
    assert "若当前目录已存在配置文件，则会追加新的服务器并将其设为默认" in captured.out
    assert "auto: 自动模式，优先从 Cpolar 获取端口，失败时回退 ~/.ssh/config" in captured.out
    assert "fixed: 固定模式，直接使用配置中的固定端口，不访问 Cpolar" in captured.out
    assert "会优先读取本机 ~/.ssh/config 中已有的 Host" in captured.out
    assert "若没有可用 Host，可在初始化过程中创建新的 SSH 配置" in captured.out
    assert "显示当前子命令的帮助信息并退出" in captured.out


def test_upload_help_mentions_long_and_short_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["upload", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote upload" in captured.out
    assert "可执行命令: `sync-remote upload`、`sync-remote up`、`sr upload`、`sr up`" in captured.out
    assert "默认作用于配置文件中的当前默认服务器" in captured.out
    assert "默认使用配置文件中的 `sync.transport`；默认配置为 `rsync`" in captured.out
    assert "仅预览将要执行的上传操作，不真正传输文件" in captured.out
    assert "只同步指定的文件或目录；需要本机安装 rsync" in captured.out
    assert "额外排除指定路径或模式；会叠加配置文件中的 excludes" in captured.out
    assert "覆盖配置中的最大文件大小限制，单位 MB" in captured.out
    assert "临时覆盖本次连接端口，优先级高于配置和自动解析" in captured.out
    assert "--hosts" in captured.out
    assert "不输出排除文件统计信息" in captured.out
    assert "password 模式会在命令执行前提示输入服务器密码" in captured.out


def test_download_help_mentions_long_and_short_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["download", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote download" in captured.out
    assert "可执行命令: `sync-remote download`、`sync-remote dl`、`sr download`、`sr dl`" in captured.out
    assert "默认作用于配置文件中的当前默认服务器" in captured.out
    assert "默认保存在当前目录，文件名为 `<项目名>-时间戳.tar.gz`" in captured.out
    assert "临时覆盖本次连接端口，优先级高于配置和自动解析" in captured.out
    assert "自定义输出压缩包路径；默认输出到当前目录" in captured.out


def test_open_help_mentions_long_and_short_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["open", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote open" in captured.out
    assert "可执行命令: `sync-remote open`、`sync-remote op`、`sr open`、`sr op`" in captured.out
    assert "默认作用于配置文件中的当前默认服务器" in captured.out
    assert "先执行一次 upload 逻辑" in captured.out
    assert "仅预览上传步骤，不真正传输文件，也不会打开 VS Code" in captured.out
    assert "只同步指定的文件或目录；需要本机安装 rsync" in captured.out
    assert "额外排除指定路径或模式；会叠加配置文件中的 excludes" in captured.out
    assert "覆盖配置中的最大文件大小限制，单位 MB" in captured.out
    assert "临时覆盖本次连接端口，优先级高于配置和自动解析" in captured.out
    assert "不输出排除文件统计信息" in captured.out
    assert "--watch" in captured.out
    assert "上传成功并打开远端目录后，继续监听本地改动并自动同步" in captured.out


def test_watch_help_mentions_long_and_short_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["watch", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote watch" in captured.out
    assert "可执行命令: `sync-remote watch`、`sync-remote wt`、`sr watch`、`sr wt`" in captured.out
    assert "默认作用于配置文件中的当前默认服务器" in captured.out
    assert "先执行一次上传，再持续监听当前目录变更" in captured.out
    assert "默认防抖时间为 1000ms" in captured.out
    assert "仅预览将要执行的上传操作，不真正传输文件" in captured.out
    assert "--debounce-ms" in captured.out


def test_backup_help_describes_output_defaults(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["backup", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote backup" in captured.out
    assert "默认输出到当前目录的上级目录" in captured.out
    assert "会跳过 `.git`、虚拟环境、`node_modules` 和隐藏目录" in captured.out
    assert "自定义备份压缩包路径；默认文件名为 `<项目名>-backup-时间戳.tar.gz`" in captured.out


def test_status_help_describes_report_contents(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["status", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote status" in captured.out
    assert "显示当前默认服务器、生效配置、SSH 目标、SSH 文件状态、远端目录和端口解析结果" in captured.out
    assert "服务器列表、认证方式" in captured.out
    assert "认证方式、SSH 配置文件、私钥、公钥和别名状态" in captured.out
    assert "适合在 upload/download/open 前先确认配置解析结果" in captured.out


def test_doctor_help_describes_checks(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["doctor", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote doctor" in captured.out
    assert "检查 ssh、rsync、code、sshpass、配置文件、SSH 文件和端口解析状态" in captured.out
    assert "SSH 配置文件、私钥、公钥、别名以及 password 模式所需的 sshpass" in captured.out
    assert "适合在首次联机前排查环境问题" in captured.out


def test_switch_help_describes_default_host_switching(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["switch", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote switch" in captured.out
    assert "切换当前项目默认使用的服务器" in captured.out
    assert "不传时会列出已配置服务器供选择" in captured.out
    assert "若传入不存在的 host，会提示后回退到选择列表" in captured.out


def test_del_help_describes_host_removal(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["del", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote del" in captured.out
    assert "删除当前项目中的一个服务器配置" in captured.out
    assert "若传入不存在的 host，会提示后回退到选择列表" in captured.out
    assert "若删除默认服务器，会自动把最后一个剩余服务器设为默认" in captured.out


def test_upload_all_gpu_help_describes_batch_upload_behavior(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["upload-all-gpu", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote upload-all-gpu" in captured.out
    assert "并发把当前目录上传到配置文件中的所有服务器" in captured.out
    assert "某个服务器失败时不会中断后续服务器" in captured.out


def test_port_sync_help_describes_preview_and_apply_modes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["port-sync", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote port-sync" in captured.out
    assert "默认只预览，不写配置文件，也不写 SSH config" in captured.out
    assert "`--apply` 时会把解析结果写回项目配置" in captured.out
    assert "`--write-ssh-config`" in captured.out


def test_target_help_describes_canonical_target_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["target", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote target" in captured.out
    assert "目标服务器管理命令树" in captured.out
    assert "list" in captured.out
    assert "use" in captured.out
    assert "remove" in captured.out
    assert "port-sync" in captured.out


def test_config_help_describes_validation_and_migration_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["config", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote config" in captured.out
    assert "配置检查、解释和迁移命令树" in captured.out
    assert "validate" in captured.out
    assert "explain" in captured.out
    assert "migrate" in captured.out


def test_version_help_describes_current_version_output(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["version", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote version" in captured.out
    assert "显示当前安装版本号" in captured.out
    assert "0.4.3-main-YYYY-MM-DD" in captured.out


def test_update_help_describes_channels(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["update", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote update" in captured.out
    assert "--channel {main,release}" in captured.out
    assert "仅支持通过 `uv tool install` 安装的命令进行自动更新" in captured.out
    assert "默认优先使用最新 Release" in captured.out
