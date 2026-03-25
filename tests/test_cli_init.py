from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sync_remote.cli import main
from sync_remote.config import DEFAULT_CONFIG_FILENAME


def _prepare_home(tmp_path: Path, *, ssh_config: str | None = None, with_keys: bool = True, key_name: str = "id_ed25519") -> Path:
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    if ssh_config is not None:
        (ssh_dir / "config").write_text(ssh_config, encoding="utf-8")
    if with_keys:
        (ssh_dir / key_name).write_text("PRIVATE", encoding="utf-8")
        (ssh_dir / f"{key_name}.pub").write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")
    return home


def test_init_writes_yaml_updates_gitignore_and_uses_selected_ssh_host(tmp_path: Path, monkeypatch) -> None:
    home = _prepare_home(
        tmp_path,
        ssh_config=(
            "Host gpu\n"
            "  HostName gpu.internal\n"
            "  User alice\n"
            "  Port 2222\n"
            "  IdentityFile ~/.ssh/id_ed25519\n"
        ),
    )
    answers = iter(
        [
            "fixed",
            "1",
            "",
            "",
            "",
            "",
            "",
            "/srv/work",
            "",
        ]
    )

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("__pycache__/\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    config_path = tmp_path / DEFAULT_CONFIG_FILENAME
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "gpu"
    assert data["servers"]["gpu"]["port_mode"] == "fixed"
    assert data["servers"]["gpu"]["port"] == 2222
    assert data["servers"]["gpu"]["user"] == "alice"
    assert data["servers"]["gpu"]["host"] == "gpu"
    assert data["servers"]["gpu"]["hostname"] == "gpu.internal"
    assert data["servers"]["gpu"]["ssh_key_path"] == "~/.ssh/id_ed25519"
    assert data["servers"]["gpu"]["auth_mode"] == "key"
    assert data["project"]["remote_base_dir"] == "/srv/work"

    gitignore_lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    assert gitignore_lines.count(DEFAULT_CONFIG_FILENAME) == 1


def test_init_help_describes_ssh_bootstrap_and_modes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["init", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "可执行命令: `sync-remote init` 或 `sr init`" in captured.out
    assert "auto: 自动模式" in captured.out
    assert "fixed: 固定模式" in captured.out
    assert "会优先读取本机 ~/.ssh/config 中已有的 Host" in captured.out
    assert "若没有可用 Host，可在初始化过程中创建新的 SSH 配置" in captured.out


def test_init_auto_uses_auto_preset_defaults_and_creates_ssh_config(tmp_path: Path, monkeypatch) -> None:
    home = _prepare_home(tmp_path, with_keys=True)
    answers = iter(["", "", "", "", "", "", "", "", ""])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "cpolar-server"
    assert data["servers"]["cpolar-server"]["port_mode"] == "auto"
    assert data["servers"]["cpolar-server"]["port"] is None
    assert data["servers"]["cpolar-server"]["user"] == "user"
    assert data["servers"]["cpolar-server"]["host"] == "cpolar-server"
    assert data["servers"]["cpolar-server"]["hostname"] == "example.tcp.vip.cpolar.cn"
    assert data["project"]["remote_base_dir"] == "/srv/projects"
    assert data["servers"]["cpolar-server"]["ssh_key_path"] == "~/.ssh/id_ed25519"
    assert data["servers"]["cpolar-server"]["auth_mode"] == "key"
    assert data["servers"]["cpolar-server"]["cpolar"]["tunnel_name"] == "my-tunnel"

    ssh_config = (home / ".ssh" / "config").read_text(encoding="utf-8")
    assert "Host cpolar-server" in ssh_config
    assert "HostName example.tcp.vip.cpolar.cn" in ssh_config
    assert "IdentityFile ~/.ssh/id_ed25519" in ssh_config


def test_init_fixed_uses_fixed_preset_defaults(tmp_path: Path, monkeypatch) -> None:
    home = _prepare_home(tmp_path, with_keys=True)
    answers = iter(["fixed", "", "", "", "", "", "", "", ""])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "remote-server"
    assert data["servers"]["remote-server"]["port_mode"] == "fixed"
    assert data["servers"]["remote-server"]["port"] == 22
    assert data["servers"]["remote-server"]["user"] == "user"
    assert data["servers"]["remote-server"]["host"] == "remote-server"
    assert data["servers"]["remote-server"]["hostname"] == "example.com"
    assert data["project"]["remote_base_dir"] == "/srv/projects"
    assert data["servers"]["remote-server"]["ssh_key_path"] == "~/.ssh/id_ed25519"
    assert data["servers"]["remote-server"]["auth_mode"] == "key"


def test_init_creates_ssh_config_and_can_switch_to_password_mode_when_keys_are_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = _prepare_home(tmp_path, with_keys=False)
    answers = iter(
        [
            "fixed",
            "2222",
            "alice",
            "gpu",
            "gpu.internal",
            "",
            "/srv/work",
            "n",
            "password",
        ]
    )

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "gpu"
    assert data["servers"]["gpu"]["auth_mode"] == "password"
    ssh_config = (home / ".ssh" / "config").read_text(encoding="utf-8")
    assert "Host gpu" in ssh_config
    assert "HostName gpu.internal" in ssh_config
    assert "User alice" in ssh_config
    assert "Port 2222" in ssh_config
    assert "IdentityFile ~/.ssh/id_ed25519" in ssh_config


def test_init_can_generate_missing_keypair(tmp_path: Path, monkeypatch) -> None:
    home = _prepare_home(tmp_path, with_keys=False)
    answers = iter(
        [
            "fixed",
            "2222",
            "alice",
            "gpu",
            "gpu.internal",
            "",
            "/srv/work",
            "y",
            "",
        ]
    )
    calls: list[list[str]] = []

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    def fake_run(command: list[str], check: bool = False, **_kwargs):
        calls.append(command)
        private_key = home / ".ssh" / "id_ed25519"
        public_key = home / ".ssh" / "id_ed25519.pub"
        private_key.write_text("PRIVATE", encoding="utf-8")
        public_key.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr("sync_remote.config.subprocess.run", fake_run)

    exit_code = main(["init"])

    assert exit_code == 0
    assert calls
    assert calls[0][0] == "ssh-keygen"
    assert (home / ".ssh" / "id_ed25519").exists()
    assert (home / ".ssh" / "id_ed25519.pub").exists()
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "gpu"
    assert data["servers"]["gpu"]["auth_mode"] == "key"


def test_init_appends_server_and_sets_new_default_host(tmp_path: Path, monkeypatch) -> None:
    home = _prepare_home(
        tmp_path,
        ssh_config=(
            "Host gpu-b\n"
            "  HostName gpu-b.internal\n"
            "  User bob\n"
            "  Port 2200\n"
            "  IdentityFile ~/.ssh/id_ed25519\n"
        ),
    )
    existing_config = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/work", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "fixed",
                "port": 2222,
                "ssh_config_path": "~/.ssh/config",
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            }
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }
    answers = iter(["fixed", "1", "", "", "", "", "", "", ""])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)
    (tmp_path / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(existing_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    exit_code = main(["init"])

    assert exit_code == 0
    data = yaml.safe_load((tmp_path / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["default_host"] == "gpu-b"
    assert set(data["servers"]) == {"gpu-a", "gpu-b"}
    assert data["servers"]["gpu-a"]["host"] == "gpu-a"
    assert data["servers"]["gpu-b"]["host"] == "gpu-b"
    assert data["servers"]["gpu-b"]["hostname"] == "gpu-b.internal"
    assert data["servers"]["gpu-b"]["port"] == 2200
    assert data["project"]["remote_base_dir"] == "/srv/work"
