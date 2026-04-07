from __future__ import annotations

from pathlib import Path

from sync_remote.ssh_config import (
    SSHHostEntry,
    list_explicit_ssh_entries,
    list_explicit_ssh_hosts,
    read_ssh_host_entry,
    update_ssh_port_for_hosts,
    upsert_ssh_host_entry,
)


def test_list_explicit_ssh_hosts_ignores_wildcards(tmp_path: Path) -> None:
    config_path = tmp_path / "config"
    config_path.write_text(
        (
            "Host gpu\n"
            "  HostName gpu.internal\n"
            "Host github.com\n"
            "  HostName github.com\n"
            "Host *.example.com\n"
            "  User wildcard\n"
        ),
        encoding="utf-8",
    )

    hosts = list_explicit_ssh_hosts(config_path)

    assert hosts == ["gpu", "github.com"]


def test_read_ssh_host_entry_returns_existing_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config"
    config_path.write_text(
        (
            "Host gpu\n"
            "  HostName gpu.internal\n"
            "  User alice\n"
            "  Port 2222\n"
            "  IdentityFile ~/.ssh/id_ed25519\n"
        ),
        encoding="utf-8",
    )

    entry = read_ssh_host_entry(config_path, "gpu")

    assert entry == SSHHostEntry(
        host="gpu",
        hostname="gpu.internal",
        user="alice",
        port="2222",
        identity_file="~/.ssh/id_ed25519",
    )


def test_list_explicit_ssh_entries_returns_all_non_wildcard_aliases(tmp_path: Path) -> None:
    config_path = tmp_path / "config"
    config_path.write_text(
        (
            "Host gpu-a gpu-a-alt\n"
            "  HostName shared.internal\n"
            "  User alice\n"
            "  Port 22\n"
            "Host *.example.com\n"
            "  User wildcard\n"
            "Host gpu-b\n"
            "  HostName gpu-b.internal\n"
            "  User bob\n"
            "  Port 2200\n"
        ),
        encoding="utf-8",
    )

    entries = list_explicit_ssh_entries(config_path)

    assert entries == [
        SSHHostEntry(host="gpu-a", hostname="shared.internal", user="alice", port="22", identity_file=""),
        SSHHostEntry(host="gpu-a-alt", hostname="shared.internal", user="alice", port="22", identity_file=""),
        SSHHostEntry(host="gpu-b", hostname="gpu-b.internal", user="bob", port="2200", identity_file=""),
    ]


def test_upsert_ssh_host_entry_updates_existing_block(tmp_path: Path) -> None:
    config_path = tmp_path / "config"
    config_path.write_text(
        (
            "Host gpu\n"
            "  HostName old.internal\n"
            "  User old-user\n"
            "  Port 22\n"
            "  IdentityFile ~/.ssh/old_key\n"
        ),
        encoding="utf-8",
    )

    upsert_ssh_host_entry(
        config_path,
        SSHHostEntry(
            host="gpu",
            hostname="gpu.internal",
            user="alice",
            port="2222",
            identity_file="~/.ssh/id_ed25519",
        ),
    )

    content = config_path.read_text(encoding="utf-8")
    assert "HostName gpu.internal" in content
    assert "User alice" in content
    assert "Port 2222" in content
    assert "IdentityFile ~/.ssh/id_ed25519" in content


def test_update_ssh_port_for_hosts_updates_all_selected_aliases(tmp_path: Path) -> None:
    config_path = tmp_path / "config"
    config_path.write_text(
        (
            "Host gpu-a\n"
            "  HostName shared.internal\n"
            "  User alice\n"
            "  Port 22\n"
            "Host gpu-b\n"
            "  HostName shared.internal\n"
            "  User bob\n"
            "  Port 23\n"
            "Host gpu-c\n"
            "  HostName gpu-c.internal\n"
            "  User carol\n"
            "  Port 24\n"
        ),
        encoding="utf-8",
    )

    update_ssh_port_for_hosts(config_path, hosts=("gpu-a", "gpu-b"), new_port="43001")

    content = config_path.read_text(encoding="utf-8")
    assert "Host gpu-a\n  HostName shared.internal\n  User alice\n  Port 43001\n" in content
    assert "Host gpu-b\n  HostName shared.internal\n  User bob\n  Port 43001\n" in content
    assert "Host gpu-c\n  HostName gpu-c.internal\n  User carol\n  Port 24\n" in content


def test_upsert_ssh_host_entry_creates_directory_and_file(tmp_path: Path) -> None:
    config_path = tmp_path / ".ssh" / "config"

    upsert_ssh_host_entry(
        config_path,
        SSHHostEntry(
            host="cpolar-server",
            hostname="example.tcp.vip.cpolar.cn",
            user="user",
            port="45678",
            identity_file="~/.ssh/id_ed25519",
        ),
    )

    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    assert "Host cpolar-server" in content
    assert "HostName example.tcp.vip.cpolar.cn" in content
    assert "User user" in content
    assert "Port 45678" in content
