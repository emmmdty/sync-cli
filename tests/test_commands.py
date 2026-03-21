from __future__ import annotations

from pathlib import Path

from sync_remote.cli import main
from sync_remote.config import (
    BackupSettings,
    ConnectionSettings,
    CpolarSettings,
    ProjectConfig,
    ProjectSettings,
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
