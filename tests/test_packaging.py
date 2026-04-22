from __future__ import annotations

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_entrypoints_and_repository_metadata() -> None:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'sync-remote = "sync_remote.cli:run"' in content
    assert 'sr = "sync_remote.cli:run"' in content
    assert 'description = "CLI tool for syncing the current project directory to a remote server"' in content
    assert 'readme = "README.md"' in content
    assert 'license = "MIT"' in content
    assert 'license-files = ["LICENSE"]' in content
    assert 'License :: OSI Approved :: MIT License' not in content
    assert 'authors = [{ name = "emmmdty" }]' in content


def test_uv_lock_keeps_local_package_version_in_sync_with_pyproject() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lockfile = (ROOT / "uv.lock").read_text(encoding="utf-8")

    pyproject_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    locked_version = re.search(
        r'\[\[package\]\]\nname = "sync-remote"\nversion = "([^"]+)"',
        lockfile,
    )

    assert pyproject_version is not None
    assert locked_version is not None
    assert locked_version.group(1) == pyproject_version.group(1)


def test_repository_has_readme_license_and_gitignore() -> None:
    readme = ROOT / "README.md"
    license_file = ROOT / "LICENSE"
    gitignore = ROOT / ".gitignore"

    assert readme.exists()
    assert license_file.exists()
    assert gitignore.exists()

    readme_content = readme.read_text(encoding="utf-8")
    license_content = license_file.read_text(encoding="utf-8")
    gitignore_content = gitignore.read_text(encoding="utf-8")

    assert "# sync-remote" in readme_content
    assert "SSH-first 远程开发同步命令行工具" in readme_content
    assert "## 新手先看" in readme_content
    assert "[docs/LEARN_BY_EXAMPLE.md](docs/LEARN_BY_EXAMPLE.md)" in readme_content
    assert "## 适用场景" in readme_content
    assert "需要在本地项目目录和远端开发机之间高频同步代码" in readme_content
    assert "同一份项目配置里切换默认目标或批量上传" in readme_content
    assert "远端 SSH 端口可能通过 Cpolar 等隧道动态变化" in readme_content
    assert "## 首次使用前准备" in readme_content
    assert "Python 3.10+" in readme_content
    assert "使用 `open` 时需要 VS Code 和 `code` 命令" in readme_content
    assert "使用 `auto` 端口模式时需要准备含 `CPOLAR_USER` 和 `CPOLAR_PASS` 的环境变量文件" in readme_content
    assert "uv tool install ." in readme_content
    assert "sr init" in readme_content
    assert "sr up" in readme_content
    assert "sr target list" in readme_content
    assert "sr target use gpu-b" in readme_content
    assert "sr target remove gpu-b" in readme_content
    assert "sr config validate" in readme_content
    assert "sr config migrate --apply" in readme_content
    assert "sr port-sync --json" in readme_content
    assert "sr port-sync --apply --write-ssh-config" in readme_content
    assert "sr switch gpu-b" in readme_content
    assert "sr upload-all-gpu" in readme_content
    assert "sr version" in readme_content
    assert "sr update --channel release" in readme_content
    assert "sr watch" in readme_content
    assert "sync-remote open --watch" in readme_content
    assert "旧版单服务器配置仍可读取，但新的写回结构统一是 `version: 3`" in readme_content
    assert "### `version: 3` 规范化多目标示例" in readme_content
    assert "default_target: gpu-b" in readme_content
    assert "targets:" in readme_content
    assert "kind: provider" in readme_content
    assert "resolved: null" in readme_content
    assert "hostname: example.tcp.vip.cpolar.cn" in readme_content
    assert "auth_mode: password" in readme_content
    assert "Host gpu-a" in readme_content
    assert "Host gpu-b" in readme_content
    assert "`update` 只支持通过 `uv tool install` 或 `uv tool install --editable` 安装的命令自动更新" in readme_content
    assert "它本身只是兼容包装层，会把旧调用方式转发到新的 `sync-remote` CLI" in readme_content
    assert "兼容命令仍保留，但推荐优先使用 `target`、`config` 和显式 `port-sync`" in readme_content
    assert "MIT" in readme_content

    assert "MIT License" in license_content
    assert "Copyright (c) 2026 emmmdty" in license_content

    assert "__pycache__/" in gitignore_content
    assert ".venv/" in gitignore_content
    assert "dist/" in gitignore_content
    assert "sync-remote.yaml" in gitignore_content
    assert "sync_config.yaml" in gitignore_content


def test_repository_has_phase3_docs_and_english_readme() -> None:
    readme_en = ROOT / "README.en.md"
    troubleshooting = ROOT / "docs" / "TROUBLESHOOTING.md"
    migration = ROOT / "docs" / "MIGRATION.md"
    release_notes = ROOT / "docs" / "RELEASE_NOTES.md"

    assert readme_en.exists()
    assert troubleshooting.exists()
    assert migration.exists()
    assert release_notes.exists()

    readme_content = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_en_content = readme_en.read_text(encoding="utf-8")
    troubleshooting_content = troubleshooting.read_text(encoding="utf-8")
    migration_content = migration.read_text(encoding="utf-8")
    release_notes_content = release_notes.read_text(encoding="utf-8")

    assert "English quickstart: [README.en.md](README.en.md)" in readme_content
    assert "# sync-remote (English)" in readme_en_content
    assert "SSH-first remote development sync CLI" in readme_en_content
    assert "## 故障排查" in troubleshooting_content
    assert "## Migration" in migration_content
    assert "## Release Checklist" in release_notes_content


def test_repository_does_not_keep_local_project_config_files() -> None:
    assert not (ROOT / "sync-remote.yaml").exists()
    assert not (ROOT / "sync_config.yaml").exists()


def test_repository_has_github_actions_ci_workflow() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"

    assert workflow_path.exists()

    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    assert data["name"] == "CI"
    assert "push" in data["on"]
    assert "pull_request" in data["on"]
    assert data["on"]["push"]["branches"] == ["main"]
    assert data["on"]["pull_request"]["branches"] == ["main"]

    test_job = data["jobs"]["test"]
    build_job = data["jobs"]["build"]

    assert test_job["runs-on"] == "ubuntu-latest"
    assert build_job["runs-on"] == "ubuntu-latest"
    assert test_job["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12"]

    test_steps = test_job["steps"]
    build_steps = build_job["steps"]

    assert any(step.get("uses") == "actions/checkout@v5" for step in test_steps)
    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in test_steps)
    assert any(step.get("run") == "uv sync --locked --group dev" for step in test_steps)
    assert any(step.get("run") == "uv run pytest -q" for step in test_steps)

    assert any(step.get("uses") == "actions/checkout@v5" for step in build_steps)
    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in build_steps)
    build_setup_uv_step = next(step for step in build_steps if step.get("uses") == "astral-sh/setup-uv@v7")
    assert build_setup_uv_step["with"]["save-cache"] is False
    assert any(step.get("run") == "uv build" for step in build_steps)
