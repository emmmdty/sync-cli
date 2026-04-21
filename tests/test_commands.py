from __future__ import annotations

import json
from pathlib import Path

import yaml

from sync_remote.cli import main
from sync_remote.config import (
    DEFAULT_CONFIG_FILENAME,
    BackupSettings,
    ConnectionSettings,
    CpolarSettings,
    ProjectConfig,
    ProjectSettings,
    ServerSettings,
    SyncSettings,
)


def build_config(
    *,
    ssh_config_path: str = "~/.ssh/config",
    ssh_key_path: str = "~/.ssh/id_ed25519",
    host: str = "gpu",
    hostname: str = "gpu.internal",
    port_mode: str = "fixed",
    port: int | None = 2222,
    auth_mode: str = "key",
    tunnel_name: str = "",
    env_path: str = "~/.env",
) -> ProjectConfig:
    return ProjectConfig(
        version=1,
        project=ProjectSettings(remote_base_dir="/srv/work", append_project_dir=True),
        connection=ConnectionSettings(
            user="alice",
            host=host,
            hostname=hostname,
            port_mode=port_mode,
            port=port,
            ssh_config_path=ssh_config_path,
            ssh_key_path=ssh_key_path,
            known_hosts_check=True,
            auth_mode=auth_mode,
        ),
        cpolar=CpolarSettings(tunnel_name=tunnel_name, env_path=env_path),
        sync=SyncSettings(transport="rsync", max_file_size_mb=50, excludes=(".git",)),
        backup=BackupSettings(excludes=(".git", ".venv", ".*")),
    )


def build_multi_config(*, default_host: str = "gpu-a") -> ProjectConfig:
    servers = {
        "gpu-a": ServerSettings(
            connection=ConnectionSettings(
                user="alice",
                host="gpu-a",
                hostname="gpu-a.internal",
                port_mode="fixed",
                port=2222,
                ssh_config_path="~/.ssh/config",
                ssh_key_path="~/.ssh/id_ed25519",
                known_hosts_check=True,
                auth_mode="key",
            ),
            cpolar=CpolarSettings(tunnel_name="", env_path="~/.env"),
        ),
        "gpu-b": ServerSettings(
            connection=ConnectionSettings(
                user="bob",
                host="gpu-b",
                hostname="gpu-b.internal",
                port_mode="fixed",
                port=2200,
                ssh_config_path="~/.ssh/config",
                ssh_key_path="~/.ssh/id_ed25519",
                known_hosts_check=True,
                auth_mode="key",
            ),
            cpolar=CpolarSettings(tunnel_name="", env_path="~/.env"),
        ),
    }
    active_server = servers[default_host]
    return ProjectConfig(
        version=2,
        project=ProjectSettings(remote_base_dir="/srv/work", append_project_dir=True),
        connection=active_server.connection,
        cpolar=active_server.cpolar,
        sync=SyncSettings(transport="rsync", max_file_size_mb=50, excludes=(".git",)),
        backup=BackupSettings(excludes=(".git", ".venv", ".*")),
        default_host=default_host,
        servers=servers,
    )


def test_target_list_json_reports_default_target(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "sync_remote.cli.load_project_config",
        lambda cwd=None: (build_multi_config(default_host="gpu-b"), project_dir / "sync-remote.yaml"),
    )

    exit_code = main(["target", "list", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["default_target"] == "gpu-b"
    assert payload["targets"] == [
        {"name": "gpu-a", "default": False},
        {"name": "gpu-b", "default": True},
    ]


def test_target_use_updates_default_target_and_persists_config(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    saved: dict[str, object] = {}
    config = build_multi_config(default_host="gpu-a")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))

    def fake_write(updated_config, path):
        saved["config"] = updated_config
        saved["path"] = Path(path)
        return Path(path)

    monkeypatch.setattr("sync_remote.cli.write_project_config", fake_write)

    exit_code = main(["target", "use", "gpu-b"])

    assert exit_code == 0
    assert saved["path"] == project_dir / "sync-remote.yaml"
    assert saved["config"].default_host == "gpu-b"
    assert saved["config"].connection.host == "gpu-b"


def test_upload_all_targets_dispatches_to_all_targets(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config = build_multi_config(default_host="gpu-a")
    attempts: list[tuple[str, str, str]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr(
        "sync_remote.cli.resolve_connection_port",
        lambda config, explicit_port=None: "2222" if config.connection.host == "gpu-a" else "2200",
    )

    def fake_upload(*, remote_dir, port, config, **_kwargs):
        attempts.append((config.connection.host, remote_dir, port))
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["upload", "--all-targets"])

    assert exit_code == 0
    assert sorted(attempts) == [
        ("gpu-a", "/srv/work/demo", "2222"),
        ("gpu-b", "/srv/work/demo", "2200"),
    ]


def test_config_validate_and_explain_json(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config = build_multi_config(default_host="gpu-b")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))

    exit_code = main(["config", "validate", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["version"] == 2
    assert payload["default_target"] == "gpu-b"

    exit_code = main(["config", "explain", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["default_target"] == "gpu-b"
    assert payload["targets"] == ["gpu-a", "gpu-b"]
    assert payload["source_path"] == str(project_dir / "sync-remote.yaml")


def test_config_migrate_preview_json_does_not_write_file(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-b",
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
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            },
            "gpu-b": {
                "user": "bob",
                "host": "gpu-b",
                "hostname": "gpu-b.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": "~/.ssh/config",
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "password",
                "remote_base_dir": "/srv/work-b",
                "append_project_dir": False,
                "cpolar": {"tunnel_name": "prod-tunnel", "env_path": "~/.env.prod"},
            },
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    config_path = project_dir / DEFAULT_CONFIG_FILENAME
    config_path.write_text(yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    exit_code = main(["config", "migrate", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["preview"] is True
    assert payload["target_version"] == 3
    assert payload["normalized"]["default_target"] == "gpu-b"
    saved_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved_data["version"] == 2
    assert saved_data["default_host"] == "gpu-b"


def test_config_migrate_apply_writes_v3_schema(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-b",
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
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            },
            "gpu-b": {
                "user": "bob",
                "host": "gpu-b",
                "hostname": "gpu-b.internal",
                "port_mode": "auto",
                "port": 2300,
                "ssh_config_path": "~/.ssh/config",
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "password",
                "remote_base_dir": "/srv/work-b",
                "append_project_dir": False,
                "cpolar": {"tunnel_name": "prod-tunnel", "env_path": "~/.env.prod"},
            },
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    config_path = project_dir / DEFAULT_CONFIG_FILENAME
    config_path.write_text(yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    exit_code = main(["config", "migrate", "--apply"])

    assert exit_code == 0
    saved_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved_data["version"] == 3
    assert saved_data["default_target"] == "gpu-b"
    assert set(saved_data["targets"]) == {"gpu-a", "gpu-b"}
    assert saved_data["targets"]["gpu-b"]["port"]["resolved"] == 2300


def test_target_port_sync_preview_json_does_not_write_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_dir = tmp_path / "home" / ".ssh"
    ssh_dir.mkdir(parents=True)
    ssh_config_path = ssh_dir / "config"
    ssh_config_path.write_text(
        "Host gpu-a\n"
        "  HostName gpu-a.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "gpu-a", "env_path": "~/.env"},
            }
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    config_path = project_dir / DEFAULT_CONFIG_FILENAME
    config_path.write_text(yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2300")

    exit_code = main(["target", "port-sync", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["preview"] is True
    assert payload["target"] == "gpu-a"
    assert payload["resolved_port"] == 2300
    assert payload["config_would_change"] is True
    assert payload["ssh_would_change"] is False
    saved_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved_data["servers"]["gpu-a"]["port"] is None
    assert "Port 22" in ssh_config_path.read_text(encoding="utf-8")


def test_target_port_sync_apply_updates_config_and_ssh_when_opted_in(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_dir = tmp_path / "home" / ".ssh"
    ssh_dir.mkdir(parents=True)
    ssh_config_path = ssh_dir / "config"
    ssh_config_path.write_text(
        "Host gpu-a\n"
        "  HostName gpu-a.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "gpu-a", "env_path": "~/.env"},
            }
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    config_path = project_dir / DEFAULT_CONFIG_FILENAME
    config_path.write_text(yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2300")

    exit_code = main(["target", "port-sync", "--apply", "--write-ssh-config"])

    assert exit_code == 0
    saved_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved_data["version"] == 3
    assert saved_data["targets"]["gpu-a"]["port"]["resolved"] == 2300
    assert "Port 2300" in ssh_config_path.read_text(encoding="utf-8")


def test_open_uploads_before_opening_remote(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    events: list[tuple[str, object]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_upload(*, local_dir, remote_dir, port, config, **_kwargs):
        events.append(("upload", local_dir, remote_dir, port, config.connection.host))
        return True

    def fake_open(*, remote_dir, config):
        events.append(("open", remote_dir, config.connection.host))
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)
    monkeypatch.setattr("sync_remote.cli.open_vscode_remote", fake_open)

    exit_code = main(["open"])

    assert exit_code == 0
    assert events == [
        ("upload", project_dir, "/srv/work/demo", "2222", "gpu"),
        ("open", "/srv/work/demo", "gpu"),
    ]


def test_upload_alias_up_dispatches_to_upload_handler(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_upload(*, local_dir, remote_dir, port, config, dry_run, **_kwargs):
        captured["local_dir"] = local_dir
        captured["remote_dir"] = remote_dir
        captured["port"] = port
        captured["host"] = config.connection.host
        captured["dry_run"] = dry_run
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["up", "--dry-run"])

    assert exit_code == 0
    assert captured == {
        "local_dir": project_dir,
        "remote_dir": "/srv/work/demo",
        "port": "2222",
        "host": "gpu",
        "dry_run": True,
    }


def test_upload_password_mode_prompts_and_passes_password(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "sync_remote.cli.load_project_config",
        lambda cwd=None: (build_config(auth_mode="password"), project_dir / "sync-remote.yaml"),
    )
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")
    monkeypatch.setattr("sync_remote.cli.shutil.which", lambda name: "/usr/bin/sshpass" if name == "sshpass" else f"/usr/bin/{name}")
    monkeypatch.setattr("sync_remote.cli.getpass.getpass", lambda _prompt="": "secret")

    def fake_upload(*, password, **_kwargs):
        captured["password"] = password
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["upload"])

    assert exit_code == 0
    assert captured["password"] == "secret"


def test_download_uses_timestamped_archive_output(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")
    monkeypatch.setattr("sync_remote.cli.current_timestamp", lambda: "20260319_231500")

    def fake_download(*, local_dir, remote_dir, port, output_path, config, **_kwargs):
        captured["local_dir"] = local_dir
        captured["remote_dir"] = remote_dir
        captured["port"] = port
        captured["output_path"] = output_path
        captured["host"] = config.connection.host
        return True

    monkeypatch.setattr("sync_remote.cli.download_remote_archive", fake_download)

    exit_code = main(["download"])

    assert exit_code == 0
    assert captured == {
        "local_dir": project_dir,
        "remote_dir": "/srv/work/demo",
        "port": "2222",
        "output_path": project_dir / "demo-20260319_231500.tar.gz",
        "host": "gpu",
    }


def test_download_alias_dl_dispatches_to_download_handler(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")
    monkeypatch.setattr("sync_remote.cli.current_timestamp", lambda: "20260319_231500")

    def fake_download(*, local_dir, remote_dir, port, output_path, config, **_kwargs):
        captured["local_dir"] = local_dir
        captured["remote_dir"] = remote_dir
        captured["port"] = port
        captured["output_path"] = output_path
        captured["host"] = config.connection.host
        return True

    monkeypatch.setattr("sync_remote.cli.download_remote_archive", fake_download)

    exit_code = main(["dl"])

    assert exit_code == 0
    assert captured == {
        "local_dir": project_dir,
        "remote_dir": "/srv/work/demo",
        "port": "2222",
        "output_path": project_dir / "demo-20260319_231500.tar.gz",
        "host": "gpu",
    }


def test_backup_uses_parent_directory_timestamped_archive_name(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.current_timestamp", lambda: "20260319_231500")

    def fake_backup(*, local_dir, output_path, config):
        captured["local_dir"] = local_dir
        captured["output_path"] = output_path
        captured["excludes"] = config.backup.excludes
        return True

    monkeypatch.setattr("sync_remote.cli.create_backup_archive", fake_backup)

    exit_code = main(["backup"])

    assert exit_code == 0
    assert captured == {
        "local_dir": project_dir,
        "output_path": tmp_path / "demo-backup-20260319_231500.tar.gz",
        "excludes": (".git", ".venv", ".*"),
    }


def test_open_alias_op_dispatches_to_open_handler(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    events: list[tuple[str, object]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_upload(*, local_dir, remote_dir, port, config, dry_run, **_kwargs):
        events.append(("upload", local_dir, remote_dir, port, config.connection.host, dry_run))
        return True

    def fake_open(*, remote_dir, config):
        events.append(("open", remote_dir, config.connection.host))
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)
    monkeypatch.setattr("sync_remote.cli.open_vscode_remote", fake_open)

    exit_code = main(["op", "--dry-run"])

    assert exit_code == 0
    assert events == [
        ("upload", project_dir, "/srv/work/demo", "2222", "gpu", True),
    ]


def test_watch_alias_wt_runs_initial_upload_and_incremental_sync(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (project_dir / "README.md").write_text("# demo\n", encoding="utf-8")
    events: list[tuple[str, object]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_batches(*_args, **_kwargs):
        yield {"src/app.py", "README.md"}

    def fake_upload(*, sync_paths, **_kwargs):
        events.append(("upload", tuple(sync_paths)))
        if len(events) > 1:
            raise KeyboardInterrupt
        return True

    monkeypatch.setattr("sync_remote.cli.iter_change_batches", fake_batches)
    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["wt"])

    assert exit_code == 0
    assert events == [
        ("upload", ()),
        ("upload", ("README.md", "src/app.py")),
    ]


def test_watch_prints_plan_and_normalizes_windows_style_selected_paths(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    events: list[tuple[str, object]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_batches(*_args, **_kwargs):
        yield {"src/app.py"}

    def fake_upload(*, sync_paths, **_kwargs):
        events.append(("upload", tuple(sync_paths)))
        if len(events) > 1:
            raise KeyboardInterrupt
        return True

    monkeypatch.setattr("sync_remote.cli.iter_change_batches", fake_batches)
    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["watch", "--sync-path", "src\\app.py"])

    assert exit_code == 0
    assert events == [
        ("upload", ("src/app.py",)),
        ("upload", ("src/app.py",)),
    ]
    captured = capsys.readouterr()
    assert "监听计划:" in captured.out
    assert "监听后端: poll (requested: auto)" in captured.out
    assert "监听范围: src/app.py" in captured.out
    assert "按 Ctrl-C 停止监听" in captured.out


def test_open_watch_opens_remote_then_enters_watch_loop(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    events: list[tuple[str, object]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (build_config(), project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")

    def fake_batches(*_args, **_kwargs):
        yield {"src/app.py"}

    def fake_upload(*, sync_paths, **_kwargs):
        events.append(("upload", tuple(sync_paths)))
        if len(events) > 1:
            raise KeyboardInterrupt
        return True

    def fake_open(*, remote_dir, config):
        events.append(("open", remote_dir, config.connection.host))
        return True

    monkeypatch.setattr("sync_remote.cli.iter_change_batches", fake_batches)
    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)
    monkeypatch.setattr("sync_remote.cli.open_vscode_remote", fake_open)

    exit_code = main(["open", "--watch"])

    assert exit_code == 0
    assert events == [
        ("upload", ()),
        ("open", "/srv/work/demo", "gpu"),
        ("upload", ("src/app.py",)),
    ]


def test_status_reports_auth_mode_and_ssh_file_existence(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_config = tmp_path / "ssh_config"
    ssh_config.write_text("Host gpu\n", encoding="utf-8")
    ssh_private_key = tmp_path / "id_ed25519"
    ssh_private_key.write_text("PRIVATE", encoding="utf-8")
    ssh_public_key = tmp_path / "id_ed25519.pub"
    ssh_public_key.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")

    config = build_config(
        ssh_config_path=str(ssh_config),
        ssh_key_path=str(ssh_private_key),
        auth_mode="password",
        port_mode="auto",
        port=None,
        host="cpolar-server",
        hostname="example.tcp.vip.cpolar.cn",
        tunnel_name="my-tunnel",
        env_path=str(tmp_path / ".env"),
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "45678")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "OK")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"OK ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"OK ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._sshpass_status", lambda config: "OK (/usr/bin/sshpass)")

    exit_code = main(["status"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "认证方式: password" in captured.out
    assert "端口模式: auto" in captured.out
    assert f"SSH 配置文件: OK ({ssh_config})" in captured.out
    assert f"SSH 私钥: OK ({ssh_private_key})" in captured.out
    assert f"SSH 公钥: OK ({ssh_public_key})" in captured.out
    assert "SSH Alias: OK" in captured.out
    assert f"Cpolar 环境文件: OK ({config.cpolar.env_path})" in captured.out
    assert f"Cpolar 凭证: OK ({config.cpolar.env_path})" in captured.out
    assert "sshpass: OK (/usr/bin/sshpass)" in captured.out


def test_doctor_reports_missing_ssh_config_public_key_and_sshpass(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_config = tmp_path / "missing_config"
    ssh_private_key = tmp_path / "id_ed25519"
    ssh_public_key = tmp_path / "id_ed25519.pub"

    config = build_config(
        ssh_config_path=str(ssh_config),
        ssh_key_path=str(ssh_private_key),
        auth_mode="password",
        port_mode="auto",
        port=None,
        host="cpolar-server",
        hostname="example.tcp.vip.cpolar.cn",
        tunnel_name="my-tunnel",
        env_path=str(tmp_path / ".env"),
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2222")
    monkeypatch.setattr("sync_remote.cli.shutil.which", lambda name: None if name == "sshpass" else f"/usr/bin/{name}")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "MISSING")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"MISSING ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"MISSING ({config.cpolar.env_path})")

    exit_code = main(["doctor"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "sshpass: MISSING" in captured.out
    assert f"ssh_config: MISSING ({ssh_config})" in captured.out
    assert f"ssh_public_key: MISSING ({ssh_public_key})" in captured.out
    assert "ssh_alias: MISSING" in captured.out
    assert f"cpolar_env: MISSING ({config.cpolar.env_path})" in captured.out
    assert f"cpolar_credentials: MISSING ({config.cpolar.env_path})" in captured.out


def test_status_json_reports_read_only_diagnostics_and_port_resolution(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_config = tmp_path / "ssh_config"
    ssh_config.write_text("Host gpu\n", encoding="utf-8")
    ssh_private_key = tmp_path / "id_ed25519"
    ssh_private_key.write_text("PRIVATE", encoding="utf-8")
    ssh_public_key = tmp_path / "id_ed25519.pub"
    ssh_public_key.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")

    config = build_config(
        ssh_config_path=str(ssh_config),
        ssh_key_path=str(ssh_private_key),
        auth_mode="password",
        port_mode="auto",
        port=None,
        host="cpolar-server",
        hostname="example.tcp.vip.cpolar.cn",
        tunnel_name="my-tunnel",
        env_path=str(tmp_path / ".env"),
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "45678")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "OK")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"OK ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"OK ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._sshpass_status", lambda config: "OK (/usr/bin/sshpass)")

    exit_code = main(["status", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["read_only"] is True
    assert payload["default_target"] == "cpolar-server"
    assert payload["port"]["status"] == "ok"
    assert payload["port"]["value"] == "45678"
    assert payload["checks"]["ssh_alias"] == "OK"
    assert payload["checks"]["ssh_private_key"]["status"] == "OK"
    assert payload["checks"]["sshpass"] == "OK (/usr/bin/sshpass)"


def test_doctor_json_reports_issues_and_actionable_hints(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_config = tmp_path / "missing_config"
    ssh_private_key = tmp_path / "id_ed25519"
    ssh_public_key = tmp_path / "id_ed25519.pub"

    config = build_config(
        ssh_config_path=str(ssh_config),
        ssh_key_path=str(ssh_private_key),
        auth_mode="password",
        port_mode="auto",
        port=None,
        host="cpolar-server",
        hostname="example.tcp.vip.cpolar.cn",
        tunnel_name="my-tunnel",
        env_path=str(tmp_path / ".env"),
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.shutil.which", lambda name: None if name == "sshpass" else f"/usr/bin/{name}")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "MISSING")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"MISSING ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"MISSING ({config.cpolar.env_path})")
    monkeypatch.setattr(
        "sync_remote.cli.resolve_connection_port",
        lambda config, explicit_port=None: (_ for _ in ()).throw(RuntimeError("cpolar login failed")),
    )

    exit_code = main(["doctor", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "sshpass" in payload["issues"]
    assert "ssh_alias" in payload["issues"]
    assert "cpolar_env" in payload["issues"]
    assert payload["port"]["status"] == "error"
    assert "sr port-sync --json" in payload["hints"]


def test_switch_updates_default_host_and_persists_config(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    saved: dict[str, object] = {}
    config = build_multi_config(default_host="gpu-a")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))

    def fake_write(updated_config, path):
        saved["config"] = updated_config
        saved["path"] = Path(path)
        return Path(path)

    monkeypatch.setattr("sync_remote.cli.write_project_config", fake_write)

    exit_code = main(["switch", "gpu-b"])

    assert exit_code == 0
    assert saved["path"] == project_dir / "sync-remote.yaml"
    assert saved["config"].default_host == "gpu-b"
    assert saved["config"].connection.host == "gpu-b"


def test_del_missing_host_prompts_for_selection_and_removes_selected_server(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    saved: dict[str, object] = {}
    answers = iter(["2"])
    config = build_multi_config(default_host="gpu-a")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))

    def fake_write(updated_config, path):
        saved["config"] = updated_config
        return Path(path)

    monkeypatch.setattr("sync_remote.cli.write_project_config", fake_write)

    exit_code = main(["del", "missing"])

    assert exit_code == 0
    assert set(saved["config"].servers) == {"gpu-a"}
    assert saved["config"].default_host == "gpu-a"
    captured = capsys.readouterr()
    assert "未找到服务器: missing" in captured.out


def test_upload_all_gpu_continues_after_failures_and_reports_summary(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config = build_multi_config(default_host="gpu-a")
    attempts: list[tuple[str, str, str]] = []

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr(
        "sync_remote.cli.resolve_connection_port",
        lambda config, explicit_port=None: "2222" if config.connection.host == "gpu-a" else "2200",
    )

    def fake_upload(*, remote_dir, port, config, **_kwargs):
        attempts.append((config.connection.host, remote_dir, port))
        return config.connection.host != "gpu-b"

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["upload-all-gpu"])

    assert exit_code == 1
    assert attempts == [
        ("gpu-a", "/srv/work/demo", "2222"),
        ("gpu-b", "/srv/work/demo", "2200"),
    ]
    captured = capsys.readouterr()
    assert "gpu-a" in captured.out
    assert "gpu-b" in captured.out
    assert "失败" in captured.out


def test_upload_hosts_uses_requested_hosts_and_server_specific_remote_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
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
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            },
            "gpu-b": {
                "user": "bob",
                "host": "gpu-b",
                "hostname": "gpu-b.internal",
                "port_mode": "fixed",
                "port": 2200,
                "ssh_config_path": "~/.ssh/config",
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-b",
                "append_project_dir": False,
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            },
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }
    attempts: list[tuple[str, str, str]] = []

    monkeypatch.chdir(project_dir)
    (project_dir / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sync_remote.cli.resolve_connection_port",
        lambda config, explicit_port=None: "2222" if config.connection.host == "gpu-a" else "2200",
    )

    def fake_upload(*, remote_dir, port, config, **_kwargs):
        attempts.append((config.connection.host, remote_dir, port))
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["upload", "--hosts", "gpu-b", "gpu-a"])

    assert exit_code == 0
    assert sorted(attempts) == [
        ("gpu-a", "/srv/work-a/demo", "2222"),
        ("gpu-b", "/srv/work-b", "2200"),
    ]


def test_status_does_not_persist_resolved_auto_port_to_yaml_or_ssh_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_dir = tmp_path / "home" / ".ssh"
    ssh_dir.mkdir(parents=True)
    ssh_config_path = ssh_dir / "config"
    ssh_config_path.write_text(
        "Host gpu-a\n"
        "  HostName gpu-a.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "gpu-a", "env_path": "~/.env"},
            }
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    (project_dir / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2300")

    exit_code = main(["status"])

    assert exit_code == 0
    saved_data = yaml.safe_load((project_dir / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_data["servers"]["gpu-a"]["port"] is None
    assert "Port 22" in ssh_config_path.read_text(encoding="utf-8")


def test_doctor_does_not_persist_resolved_auto_port_to_yaml_or_ssh_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_dir = tmp_path / "home" / ".ssh"
    ssh_dir.mkdir(parents=True)
    ssh_config_path = ssh_dir / "config"
    ssh_config_path.write_text(
        "Host gpu-a\n"
        "  HostName gpu-a.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "gpu-a", "env_path": "~/.env"},
            }
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    monkeypatch.chdir(project_dir)
    (project_dir / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2300")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "OK")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"OK ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"OK ({config.cpolar.env_path})")

    exit_code = main(["doctor"])

    assert exit_code == 0
    saved_data = yaml.safe_load((project_dir / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_data["servers"]["gpu-a"]["port"] is None
    assert "Port 22" in ssh_config_path.read_text(encoding="utf-8")


def test_status_reports_default_host_and_server_list(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    config = build_multi_config(default_host="gpu-b")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("sync_remote.cli.load_project_config", lambda cwd=None: (config, project_dir / "sync-remote.yaml"))
    monkeypatch.setattr("sync_remote.cli.resolve_connection_port", lambda config, explicit_port=None: "2200")
    monkeypatch.setattr("sync_remote.cli._ssh_alias_status", lambda config: "OK")
    monkeypatch.setattr("sync_remote.cli._cpolar_env_status", lambda config: f"SKIPPED ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._cpolar_credentials_status", lambda config: f"SKIPPED ({config.cpolar.env_path})")
    monkeypatch.setattr("sync_remote.cli._sshpass_status", lambda config: "SKIPPED (key mode)")

    exit_code = main(["status"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "默认服务器: gpu-b" in captured.out
    assert "服务器列表:" in captured.out
    assert "gpu-a" in captured.out
    assert "gpu-b" in captured.out


def test_upload_hosts_does_not_persist_auto_port_resolution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    ssh_dir = tmp_path / "home" / ".ssh"
    ssh_dir.mkdir(parents=True)
    ssh_config_path = ssh_dir / "config"
    ssh_config_path.write_text(
        "Host gpu-a\n"
        "  HostName gpu-a.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n"
        "Host gpu-b\n"
        "  HostName gpu-b.internal\n"
        "  User bob\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config_data = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/default", "append_project_dir": True},
        "default_host": "gpu-a",
        "servers": {
            "gpu-a": {
                "user": "alice",
                "host": "gpu-a",
                "hostname": "gpu-a.internal",
                "port_mode": "fixed",
                "port": 2222,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-a",
                "append_project_dir": True,
                "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
            },
            "gpu-b": {
                "user": "bob",
                "host": "gpu-b",
                "hostname": "gpu-b.internal",
                "port_mode": "auto",
                "port": None,
                "ssh_config_path": str(ssh_config_path),
                "ssh_key_path": "~/.ssh/id_ed25519",
                "known_hosts_check": True,
                "auth_mode": "key",
                "remote_base_dir": "/srv/work-b",
                "append_project_dir": False,
                "cpolar": {"tunnel_name": "gpu-b", "env_path": "~/.env"},
            },
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
        "backup": {"excludes": [".git", ".venv"]},
    }
    attempts: list[tuple[str, str, str]] = []

    monkeypatch.chdir(project_dir)
    (project_dir / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(config_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sync_remote.cli.resolve_connection_port",
        lambda config, explicit_port=None: "2222" if config.connection.host == "gpu-a" else "2200",
    )

    def fake_upload(*, remote_dir, port, config, **_kwargs):
        attempts.append((config.connection.host, remote_dir, port))
        return True

    monkeypatch.setattr("sync_remote.cli.sync_upload", fake_upload)

    exit_code = main(["upload", "--hosts", "gpu-b", "gpu-a"])

    assert exit_code == 0
    assert sorted(attempts) == [
        ("gpu-a", "/srv/work-a/demo", "2222"),
        ("gpu-b", "/srv/work-b", "2200"),
    ]
    saved_data = yaml.safe_load((project_dir / DEFAULT_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_data["servers"]["gpu-b"]["port"] is None
    ssh_config_contents = ssh_config_path.read_text(encoding="utf-8")
    assert "Host gpu-b" in ssh_config_contents
    assert "Port 22" in ssh_config_contents
    assert "Port 2200" not in ssh_config_contents


def test_version_prints_display_version(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sync_remote.cli.get_display_version", lambda: "0.3.0-main-2026-03-24")

    exit_code = main(["version"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "sync-remote 0.3.0-main-2026-03-24"


def test_update_delegates_to_self_update_runner(monkeypatch, capsys) -> None:
    recorded: dict[str, object] = {}

    def fake_run_self_update(*, channel: str | None):
        recorded["channel"] = channel
        return True, "已更新到 release 0.4.3"

    monkeypatch.setattr("sync_remote.cli.run_self_update", fake_run_self_update)

    exit_code = main(["update", "--channel", "release"])

    assert exit_code == 0
    assert recorded["channel"] == "release"
    captured = capsys.readouterr()
    assert "已更新到 release 0.4.3" in captured.out
