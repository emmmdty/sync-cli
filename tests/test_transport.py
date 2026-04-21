from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from sync_remote.config import (
    BackupSettings,
    ConnectionSettings,
    CpolarSettings,
    ProjectConfig,
    ProjectSettings,
    SyncSettings,
)
from sync_remote.transport import (
    build_rsync_command,
    download_remote_archive,
    get_port_from_cpolar,
    normalize_sync_paths,
    sync_upload_archive,
    sync_upload_rsync,
)


def build_config(*, excludes: tuple[str, ...] = (".git",), max_file_size_mb: int = 50) -> ProjectConfig:
    return ProjectConfig(
        version=1,
        project=ProjectSettings(remote_base_dir="/srv/work", append_project_dir=True),
        connection=ConnectionSettings(
            user="alice",
            host="gpu",
            hostname="gpu.internal",
            port_mode="fixed",
            port=2222,
            ssh_config_path="~/.ssh/config",
            ssh_key_path="~/.ssh/id_ed25519",
            known_hosts_check=True,
            auth_mode="key",
        ),
        cpolar=CpolarSettings(tunnel_name="", env_path="~/.env"),
        sync=SyncSettings(transport="rsync", max_file_size_mb=max_file_size_mb, excludes=excludes),
        backup=BackupSettings(excludes=(".git", ".venv", ".*")),
    )


def test_build_rsync_command_does_not_use_append_verify() -> None:
    command = build_rsync_command(
        build_config(),
        port="2222",
        source="/tmp/local/",
        destination="alice@gpu:/srv/work/demo/",
        excludes=(".git",),
    )

    assert "--append-verify" not in command
    assert "--modify-window=-1" in command


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync is required for this regression test")
def test_rsync_overwrites_same_size_file_modified_within_same_second(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    destination_dir = tmp_path / "dst"
    source_dir.mkdir()
    destination_dir.mkdir()

    source_file = source_dir / "file.txt"
    source_file.write_text("abc123\n", encoding="utf-8")

    subprocess.run(["rsync", "-az", str(source_dir) + "/", str(destination_dir) + "/"], check=True)

    source_file.write_text("xyz123\n", encoding="utf-8")
    command = build_rsync_command(
        build_config(),
        port="2222",
        source=str(source_dir) + "/",
        destination=str(destination_dir) + "/",
        excludes=(),
    )

    subprocess.run(command, check=True)

    assert (destination_dir / "file.txt").read_text(encoding="utf-8") == "xyz123\n"


@pytest.mark.parametrize(
    ("relative_path", "contents", "excludes", "max_size_mb"),
    [
        ("ignored.log", "ignore me\n", ("*.log",), 50),
        ("large.bin", "x" * 8, (), 0),
    ],
)
def test_sync_upload_rsync_sync_path_skips_excluded_or_oversized_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
    contents: str,
    excludes: tuple[str, ...],
    max_size_mb: int,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    target = project_dir / relative_path
    target.write_text(contents, encoding="utf-8")

    called: dict[str, object] = {"mkdir": False, "rsync": False}

    def fake_ensure_remote_directory(*args, **kwargs):
        called["mkdir"] = True
        return True

    def fake_run_rsync_command(*args, **kwargs):
        called["rsync"] = True
        return True

    monkeypatch.setattr("sync_remote.transport.ensure_remote_directory", fake_ensure_remote_directory)
    monkeypatch.setattr("sync_remote.transport.run_rsync_command", fake_run_rsync_command)

    result = sync_upload_rsync(
        local_dir=project_dir,
        remote_dir="/srv/work/demo",
        port="2222",
        config=build_config(excludes=excludes, max_file_size_mb=max_size_mb),
        excludes=excludes,
        dry_run=False,
        list_excluded=False,
        sync_paths=(relative_path,),
        max_size_bytes=max_size_mb * 1024 * 1024,
        password=None,
    )

    assert result is True
    assert called == {"mkdir": False, "rsync": False}


def test_sync_upload_rsync_sync_path_directory_preserves_excludes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "demo"
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (src_dir / "debug.log").write_text("secret\n", encoding="utf-8")

    captured: dict[str, object] = {}

    monkeypatch.setattr("sync_remote.transport.ensure_remote_directory", lambda *args, **kwargs: True)

    def fake_build_rsync_command(config, *, port, source, destination, excludes):
        captured["excludes"] = excludes
        return ["rsync", source, destination]

    monkeypatch.setattr("sync_remote.transport.build_rsync_command", fake_build_rsync_command)
    monkeypatch.setattr("sync_remote.transport.run_rsync_command", lambda *args, **kwargs: True)

    result = sync_upload_rsync(
        local_dir=project_dir,
        remote_dir="/srv/work/demo",
        port="2222",
        config=build_config(excludes=("*.log",)),
        excludes=("*.log",),
        dry_run=False,
        list_excluded=False,
        sync_paths=("src",),
        max_size_bytes=50 * 1024 * 1024,
        password=None,
    )

    assert result is True
    assert captured["excludes"] == ("*.log",)


def test_normalize_sync_paths_accepts_windows_style_relative_separators(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True)
    target = src_dir / "app.py"
    target.write_text("print('hi')\n", encoding="utf-8")

    normalized = normalize_sync_paths(project_dir, ("src\\app.py",), require_exists=True)

    assert normalized == [("src/app.py", target.resolve())]


def test_normalize_sync_paths_rejects_windows_absolute_paths_with_wsl_hint(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    with pytest.raises(ValueError, match="Windows 绝对路径"):
        normalize_sync_paths(project_dir, ("C:\\Users\\alice\\demo\\src\\app.py",), require_exists=False)


def test_sync_upload_archive_uses_current_directory_when_remote_parent_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "app.py").write_text("print('hi')\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_ensure_remote_directory(config, port, target_dir, *, password=None):
        captured["target_dir"] = target_dir
        return True

    def fake_run(command, capture_output=False, env=None):
        if command[0] == "ssh":
            captured["extract_command"] = command[-1]
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("sync_remote.transport.ensure_remote_directory", fake_ensure_remote_directory)
    monkeypatch.setattr("sync_remote.transport.generate_secure_temp_name", lambda *args, **kwargs: "sync_test.tar.gz")
    monkeypatch.setattr("sync_remote.transport.subprocess.run", fake_run)

    result = sync_upload_archive(
        local_dir=project_dir,
        remote_dir="demo",
        port="2222",
        config=build_config(),
        excludes=(),
        dry_run=False,
        list_excluded=False,
        max_size_bytes=50 * 1024 * 1024,
        password=None,
    )

    assert result is True
    assert captured["target_dir"] == "."
    assert "cd ." in captured["extract_command"]


def test_download_remote_archive_uses_current_directory_when_remote_parent_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "demo.tar.gz"
    captured: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        def communicate(self):
            output_path.write_bytes(b"archive")
            return (b"", b"")

    def fake_popen(command, stdout=None, stderr=None, env=None):
        captured["remote_tar_command"] = command[-1]
        return FakeProcess()

    monkeypatch.setattr("sync_remote.transport.subprocess.Popen", fake_popen)

    result = download_remote_archive(
        local_dir=tmp_path,
        remote_dir="demo",
        port="2222",
        output_path=output_path,
        config=build_config(),
        password=None,
    )

    assert result is True
    assert "cd ." in captured["remote_tar_command"]


def test_get_port_from_cpolar_does_not_update_ssh_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ssh_config_path = tmp_path / "ssh_config"
    ssh_config_path.write_text(
        "Host gpu\n"
        "  HostName gpu.internal\n"
        "  User alice\n"
        "  Port 22\n"
        "  IdentityFile ~/.ssh/id_ed25519\n",
        encoding="utf-8",
    )
    config = ProjectConfig(
        version=1,
        project=ProjectSettings(remote_base_dir="/srv/work", append_project_dir=True),
        connection=ConnectionSettings(
            user="alice",
            host="gpu",
            hostname="gpu.internal",
            port_mode="auto",
            port=None,
            ssh_config_path=str(ssh_config_path),
            ssh_key_path="~/.ssh/id_ed25519",
            known_hosts_check=True,
            auth_mode="key",
        ),
        cpolar=CpolarSettings(tunnel_name="gpu", env_path=str(tmp_path / ".env")),
        sync=SyncSettings(transport="rsync", max_file_size_mb=50, excludes=(".git",)),
        backup=BackupSettings(excludes=(".git", ".venv", ".*")),
    )

    class FakeResponse:
        def __init__(self, *, status_code: int, url: str, text: str = "", payload=None):
            self.status_code = status_code
            self.url = url
            self.text = text
            self._payload = payload

        def json(self):
            return self._payload

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, timeout=10, headers=None):
            if url.endswith("/login"):
                return FakeResponse(status_code=200, url=url)
            return FakeResponse(
                status_code=200,
                url=url,
                text=(
                    "<tr><td>gpu</td><td>tcp://ignored</td>"
                    "<td><a>example.tcp.vip.cpolar.cn:2300</a></td></tr>"
                ),
            )

        def post(self, url, data=None, headers=None, timeout=10):
            return FakeResponse(status_code=200, url="https://dashboard.cpolar.com/dashboard")

    updated_ports: list[str] = []

    monkeypatch.setenv("CPOLAR_USER", "user")
    monkeypatch.setenv("CPOLAR_PASS", "pass")
    monkeypatch.setattr("sync_remote.transport.requests.Session", lambda: FakeSession())
    monkeypatch.setattr("sync_remote.transport.update_ssh_port_in_config", lambda port, config: updated_ports.append(port))

    assert get_port_from_cpolar(config) == "2300"
    assert updated_ports == []
