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
    assert 'license = { file = "LICENSE" }' in content
    assert 'authors = [{ name = "emmmdty" }]' in content


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
    assert "远程同步命令行工具" in readme_content
    assert "## 适用群体" in readme_content
    assert "需要在本地项目目录和远端服务器目录之间高频同步代码" in readme_content
    assert "远端 SSH 端口会变化" in readme_content
    assert "uv tool install ." in readme_content
    assert "sync-remote init" in readme_content
    assert "sr up" in readme_content
    assert "适合通过 Cpolar 等隧道暴露 SSH，且公网端口经常变化的场景" in readme_content
    assert "`sync_to_remote.py` 只是兼容包装层" in readme_content
    assert "它会把旧调用方式转发到新的 `sync-remote` CLI" in readme_content
    assert "MIT" in readme_content

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
    assert any(step.get("run") == "uv build" for step in build_steps)
