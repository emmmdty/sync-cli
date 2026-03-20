from __future__ import annotations

from pathlib import Path


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
    assert "uv tool install ." in readme_content
    assert "sync-remote init" in readme_content
    assert "sr up" in readme_content
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
