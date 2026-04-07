from __future__ import annotations

from pathlib import Path

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


def test_repository_has_readme_license_and_gitignore() -> None:
    readme = ROOT / "README.md"
    usage_doc = ROOT / "docs" / "usage.md"
    license_file = ROOT / "LICENSE"
    gitignore = ROOT / ".gitignore"

    assert readme.exists()
    assert usage_doc.exists()
    assert license_file.exists()
    assert gitignore.exists()

    readme_content = readme.read_text(encoding="utf-8")
    usage_content = usage_doc.read_text(encoding="utf-8")
    license_content = license_file.read_text(encoding="utf-8")
    gitignore_content = gitignore.read_text(encoding="utf-8")

    assert "# sync-remote" in readme_content
    assert "把本地项目目录同步到远端 Linux 服务器" in readme_content
    assert "项目内命令" in readme_content
    assert "任意目录命令" in readme_content
    assert "uv tool install git+https://github.com/emmmdty/sync-cli.git" in readme_content
    assert "sr init" in readme_content
    assert "sr doctor" in readme_content
    assert "sr up" in readme_content
    assert "sr port-sync --hostname gpu-a.internal" in readme_content
    assert "sr update --channel release" in readme_content
    assert "docs/usage.md" in readme_content
    assert "如果你的 SSH `User` 不是 cpolar tunnel 名，请显式传 `--tunnel`" in readme_content
    assert "旧版单服务器配置" not in readme_content
    assert "兼容包装层" not in readme_content
    assert "MIT" in readme_content

    assert "# sync-remote 使用手册" in usage_content
    assert "## 1. 安装" in usage_content
    assert "## 2. 最快上手" in usage_content
    assert "## 3. 项目内命令" in usage_content
    assert "## 4. 任意目录更新 SSH 端口" in usage_content
    assert "## 5. `sync-remote.yaml` 示例" in usage_content
    assert "## 7. 排错" in usage_content
    assert "sr port-sync --hostname gpu-a.internal" in usage_content
    assert "同名 tunnel" in usage_content
    assert "如果你的 SSH `User` 不是 cpolar tunnel 名，请显式传 `--tunnel`" in usage_content

    assert "MIT License" in license_content
    assert "Copyright (c) 2026 emmmdty" in license_content

    assert "__pycache__/" in gitignore_content
    assert ".venv/" in gitignore_content
    assert "dist/" in gitignore_content
    assert "sync-remote.yaml" in gitignore_content
    assert "sync_config.yaml" in gitignore_content


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
