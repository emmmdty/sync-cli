from __future__ import annotations

from pathlib import Path

import yaml

from sync_remote.config import DEFAULT_CONFIG_FILENAME, LEGACY_CONFIG_FILENAME, load_project_config
from sync_remote.operations import (
    build_remote_dir,
    default_backup_archive_path,
    default_download_archive_path,
)


def test_load_project_config_prefers_new_yaml(tmp_path: Path) -> None:
    new_config = {
        "version": 1,
        "project": {"remote_base_dir": "/srv/new", "append_project_dir": True},
        "connection": {
            "user": "alice",
            "host": "gpu-new",
            "hostname": "gpu-new.internal",
            "port_mode": "fixed",
            "port": 2222,
            "ssh_config_path": "~/.ssh/config",
            "ssh_key_path": "~/.ssh/id_ed25519",
            "known_hosts_check": True,
            "auth_mode": "password",
        },
        "cpolar": {"tunnel_name": "", "env_path": "~/.env"},
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": ["node_modules"]},
        "backup": {"excludes": [".git", ".venv"]},
    }
    legacy_config = {
        "targets": {
            "auto": {
                "ssh_host": "legacy-host",
                "user": "legacy-user",
                "base_dir": "/legacy/base",
                "append_project_dir": True,
            }
        }
    }

    (tmp_path / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / LEGACY_CONFIG_FILENAME).write_text(
        yaml.safe_dump(legacy_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    config, source_path = load_project_config(tmp_path)

    assert source_path == tmp_path / DEFAULT_CONFIG_FILENAME
    assert config.project.remote_base_dir == "/srv/new"
    assert config.connection.host == "gpu-new"
    assert config.connection.hostname == "gpu-new.internal"
    assert config.connection.port_mode == "fixed"
    assert config.connection.port == 2222
    assert config.connection.auth_mode == "password"


def test_load_project_config_supports_v2_servers_and_default_host(tmp_path: Path) -> None:
    new_config = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/new", "append_project_dir": True},
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
                "cpolar": {"tunnel_name": "prod-tunnel", "env_path": "~/.env.prod"},
            },
        },
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": ["node_modules"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    (tmp_path / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    config, source_path = load_project_config(tmp_path)

    assert source_path == tmp_path / DEFAULT_CONFIG_FILENAME
    assert config.version == 2
    assert config.default_host == "gpu-b"
    assert set(config.servers) == {"gpu-a", "gpu-b"}
    assert config.connection.host == "gpu-b"
    assert config.connection.hostname == "gpu-b.internal"
    assert config.connection.auth_mode == "password"
    assert config.cpolar.tunnel_name == "prod-tunnel"


def test_load_project_config_uses_server_specific_remote_dirs(tmp_path: Path) -> None:
    new_config = {
        "version": 2,
        "project": {"remote_base_dir": "/srv/legacy", "append_project_dir": True},
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
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": ["node_modules"]},
        "backup": {"excludes": [".git", ".venv"]},
    }

    (tmp_path / DEFAULT_CONFIG_FILENAME).write_text(
        yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    config, _source_path = load_project_config(tmp_path)

    assert config.project.remote_base_dir == "/srv/work-b"
    assert config.project.append_project_dir is False
    assert config.get_server("gpu-a").project.remote_base_dir == "/srv/work-a"
    assert config.get_server("gpu-a").project.append_project_dir is True
    assert config.get_server("gpu-b").project.remote_base_dir == "/srv/work-b"
    assert config.get_server("gpu-b").project.append_project_dir is False


def test_load_project_config_falls_back_to_legacy_mapping(tmp_path: Path) -> None:
    legacy_config = {
        "targets": {
            "auto": {
                "ssh_host": "cpolar-server",
                "user": "user",
                "base_dir": "/srv/legacy",
                "append_project_dir": True,
            }
        },
        "ssh": {
            "config_path": "~/.ssh/config",
            "key_path": "~/.ssh/id_ed25519",
            "known_hosts_check": True,
        },
        "cpolar": {"tunnel_name": "my-tunnel", "env_path": "~/.env"},
        "sync": {"transport": "rsync", "max_file_size_mb": 50, "excludes": [".git"]},
    }

    (tmp_path / LEGACY_CONFIG_FILENAME).write_text(
        yaml.safe_dump(legacy_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    config, source_path = load_project_config(tmp_path)

    assert source_path == tmp_path / LEGACY_CONFIG_FILENAME
    assert config.project.remote_base_dir == "/srv/legacy"
    assert config.connection.user == "user"
    assert config.connection.host == "cpolar-server"
    assert config.connection.hostname == ""
    assert config.connection.port_mode == "auto"
    assert config.connection.ssh_key_path == "~/.ssh/id_ed25519"
    assert config.connection.auth_mode == "key"
    assert config.cpolar.tunnel_name == "my-tunnel"


def test_remote_dir_and_archive_names_are_derived_from_cwd(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()

    remote_dir = build_remote_dir("/srv/work", project_dir)
    download_path = default_download_archive_path(project_dir, "20260319_231500")
    backup_path = default_backup_archive_path(project_dir, "20260319_231500")

    assert remote_dir == "/srv/work/demo-project"
    assert download_path == project_dir / "demo-project-20260319_231500.tar.gz"
    assert backup_path == tmp_path / "demo-project-backup-20260319_231500.tar.gz"
