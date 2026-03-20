from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sync_remote.cli import main
from sync_remote.config import DEFAULT_CONFIG_FILENAME


def test_init_writes_yaml_and_updates_gitignore(tmp_path: Path, monkeypatch) -> None:
    answers = iter(
        [
            "fixed",
            "2222",
            "alice",
            "gpu",
            "gpu.internal",
            "/srv/work",
        ]
    )

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("__pycache__/\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    config_path = tmp_path / DEFAULT_CONFIG_FILENAME
    assert config_path.exists()

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["connection"]["port_mode"] == "fixed"
    assert data["connection"]["port"] == 2222
    assert data["connection"]["user"] == "alice"
    assert data["connection"]["host"] == "gpu"
    assert data["connection"]["hostname"] == "gpu.internal"
    assert data["project"]["remote_base_dir"] == "/srv/work"

    gitignore_lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    assert gitignore_lines.count(DEFAULT_CONFIG_FILENAME) == 1


def test_init_help_describes_auto_and_fixed(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["init", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "可执行命令: `sync-remote init` 或 `sr init`" in captured.out
    assert "auto: 自动模式" in captured.out
    assert "fixed: 固定模式" in captured.out


def test_init_auto_uses_auto_preset_defaults(tmp_path: Path, monkeypatch) -> None:
    answers = iter(["", "", "", "", "", "", ""])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["connection"]["port_mode"] == "auto"
    assert data["connection"]["port"] is None
    assert data["connection"]["user"] == "user"
    assert data["connection"]["host"] == "cpolar-server"
    assert data["connection"]["hostname"] == "example.tcp.vip.cpolar.cn"
    assert data["project"]["remote_base_dir"] == "/srv/projects"
    assert data["connection"]["ssh_key_path"] == "~/.ssh/id_ed25519"
    assert data["cpolar"]["tunnel_name"] == "my-tunnel"


def test_init_fixed_uses_fixed_preset_defaults(tmp_path: Path, monkeypatch) -> None:
    answers = iter(["fixed", "", "", "", "", "", ""])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["connection"]["port_mode"] == "fixed"
    assert data["connection"]["port"] == 22
    assert data["connection"]["user"] == "user"
    assert data["connection"]["host"] == "remote-server"
    assert data["connection"]["hostname"] == "example.com"
    assert data["project"]["remote_base_dir"] == "/srv/projects"
    assert data["connection"]["ssh_key_path"] == "~/.ssh/id_ed25519"
