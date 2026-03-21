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


def test_init_help_explains_generated_config_and_modes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["init", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote init" in captured.out
    assert "运行后会在当前目录生成 `sync-remote.yaml`" in captured.out
    assert "若检测到 `.gitignore`，会自动追加配置文件名" in captured.out
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
    assert "默认使用配置文件中的 `sync.transport`；默认配置为 `rsync`" in captured.out
    assert "仅预览将要执行的上传操作，不真正传输文件" in captured.out
    assert "只同步指定的文件或目录；需要本机安装 rsync" in captured.out
    assert "额外排除指定路径或模式；会叠加配置文件中的 excludes" in captured.out
    assert "覆盖配置中的最大文件大小限制，单位 MB" in captured.out
    assert "临时覆盖本次连接端口，优先级高于配置和自动解析" in captured.out
    assert "不输出排除文件统计信息" in captured.out
    assert "password 模式会在命令执行前提示输入服务器密码" in captured.out


def test_download_help_mentions_long_and_short_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["download", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync-remote download" in captured.out
    assert "可执行命令: `sync-remote download`、`sync-remote dl`、`sr download`、`sr dl`" in captured.out
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
    assert "显示当前生效的配置文件、认证方式、SSH 目标、SSH 文件状态、远端目录和端口解析结果" in captured.out
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
