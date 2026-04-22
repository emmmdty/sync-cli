from __future__ import annotations

from pathlib import Path

import pytest

from sync_remote.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_readmes_link_to_beginner_tutorials_and_start_here_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")

    assert "## 新手先看" in readme
    assert "[docs/LEARN_BY_EXAMPLE.md](docs/LEARN_BY_EXAMPLE.md)" in readme
    assert "[docs/LEARN_BY_EXAMPLE.en.md](docs/LEARN_BY_EXAMPLE.en.md)" in readme

    assert "## Start Here" in readme_en
    assert "[docs/LEARN_BY_EXAMPLE.md](docs/LEARN_BY_EXAMPLE.md)" in readme_en
    assert "[docs/LEARN_BY_EXAMPLE.en.md](docs/LEARN_BY_EXAMPLE.en.md)" in readme_en


def test_beginner_tutorial_docs_exist_and_cover_major_workflows() -> None:
    tutorial_zh = ROOT / "docs" / "LEARN_BY_EXAMPLE.md"
    tutorial_en = ROOT / "docs" / "LEARN_BY_EXAMPLE.en.md"

    assert tutorial_zh.exists()
    assert tutorial_en.exists()

    zh_content = tutorial_zh.read_text(encoding="utf-8")
    en_content = tutorial_en.read_text(encoding="utf-8")

    zh_expected = [
        "它是什么，不是什么",
        "前置准备与安装",
        "第一次初始化",
        "检查环境 / doctor",
        "理解目标服务器",
        "切换目标服务器",
        "固定端口目标",
        "动态端口目标",
        "推送同步",
        "持续监听",
        "打开远端项目",
        "配置检查、解释与迁移",
        "常见故障排查",
        "兼容命令与何时不要用",
        "日常工作流",
        "安全恢复",
    ]
    for fragment in zh_expected:
        assert fragment in zh_content

    en_expected = [
        "What It Is and Is Not",
        "Prerequisites and Installation",
        "First-Time Setup",
        "Check Your Environment with doctor",
        "Understand Targets",
        "Switch Targets",
        "Fixed-Port Workflow",
        "Dynamic-Port Workflow",
        "Push Sync Workflow",
        "Watch Workflow",
        "Open the Remote Project",
        "Validate, Explain, and Migrate Config",
        "Troubleshooting",
        "Legacy Aliases",
        "Daily Workflow",
        "Safe Recovery",
    ]
    for fragment in en_expected:
        assert fragment in en_content


def test_migration_and_troubleshooting_docs_link_beginner_materials() -> None:
    migration = (ROOT / "docs" / "MIGRATION.md").read_text(encoding="utf-8")
    troubleshooting = (ROOT / "docs" / "TROUBLESHOOTING.md").read_text(encoding="utf-8")

    assert "[LEARN_BY_EXAMPLE.md](LEARN_BY_EXAMPLE.md)" in migration
    assert "[LEARN_BY_EXAMPLE.en.md](LEARN_BY_EXAMPLE.en.md)" in migration
    assert "sr config validate" in migration
    assert "sr config explain" in migration
    assert "sr config migrate --json" in migration
    assert "sr config migrate --apply" in migration
    assert "sr port-sync --json" in migration
    assert "sr port-sync --apply --write-ssh-config" in migration

    assert "[LEARN_BY_EXAMPLE.md](LEARN_BY_EXAMPLE.md)" in troubleshooting
    assert "[LEARN_BY_EXAMPLE.en.md](LEARN_BY_EXAMPLE.en.md)" in troubleshooting
    assert "sr port-sync --json" in troubleshooting


@pytest.mark.parametrize(
    "argv",
    [
        ["upload", "--help"],
        ["open", "--help"],
        ["watch", "--help"],
        ["target", "list", "--help"],
        ["target", "use", "--help"],
        ["target", "remove", "--help"],
        ["target", "port-sync", "--help"],
        ["config", "validate", "--help"],
        ["config", "explain", "--help"],
        ["config", "migrate", "--help"],
        ["port-sync", "--help"],
        ["status", "--help"],
        ["doctor", "--help"],
    ],
)
def test_documented_core_commands_have_help_contracts(argv, capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == 0
    assert "usage: sync-remote" in capsys.readouterr().out
