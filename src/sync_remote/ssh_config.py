from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fnmatch
import os
import re


@dataclass(frozen=True)
class SSHHostEntry:
    host: str
    hostname: str = ""
    user: str = ""
    port: str = ""
    identity_file: str = ""


def parse_ssh_config_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if re.match(r"^\s*Host\s+", line):
            if current:
                current["end"] = idx
                blocks.append(current)
            current = {
                "start": idx,
                "end": len(lines),
                "patterns": stripped.split()[1:],
                "hostname": None,
                "hostname_idx": None,
                "hostname_indent": None,
                "user": None,
                "user_idx": None,
                "user_indent": None,
                "port": None,
                "port_idx": None,
                "port_indent": None,
                "identity_file": None,
                "identity_file_idx": None,
                "identity_file_indent": None,
            }
            continue

        if current is None:
            continue

        hostname_match = re.match(r"^(\s*)HostName\s+(.+)$", line)
        if hostname_match and current["hostname"] is None:
            current["hostname"] = hostname_match.group(2).strip()
            current["hostname_idx"] = idx
            current["hostname_indent"] = hostname_match.group(1)

        user_match = re.match(r"^(\s*)User\s+(.+)$", line)
        if user_match and current["user"] is None:
            current["user"] = user_match.group(2).strip()
            current["user_idx"] = idx
            current["user_indent"] = user_match.group(1)

        port_match = re.match(r"^(\s*)Port\s+(\S+)", line)
        if port_match and current["port"] is None:
            current["port"] = port_match.group(2).strip()
            current["port_idx"] = idx
            current["port_indent"] = port_match.group(1)

        identity_match = re.match(r"^(\s*)IdentityFile\s+(.+)$", line)
        if identity_match and current["identity_file"] is None:
            current["identity_file"] = identity_match.group(2).strip()
            current["identity_file_idx"] = idx
            current["identity_file_indent"] = identity_match.group(1)

    if current:
        blocks.append(current)
    return blocks


def select_ssh_block(blocks: list[dict], remote_host: str) -> dict | None:
    for block in blocks:
        if any(pattern == remote_host for pattern in block["patterns"]):
            return block

    for block in blocks:
        for pattern in block["patterns"]:
            if fnmatch.fnmatch(remote_host, pattern):
                return block

    for block in blocks:
        if block.get("hostname") == remote_host:
            return block

    return None


def list_explicit_ssh_hosts(config_path: Path | str) -> list[str]:
    path = Path(config_path)
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    hosts: list[str] = []
    for block in parse_ssh_config_blocks(lines):
        for pattern in block["patterns"]:
            if "*" in pattern or "?" in pattern:
                continue
            hosts.append(pattern)
    return hosts


def read_ssh_host_entry(config_path: Path | str, host: str) -> SSHHostEntry | None:
    path = Path(config_path)
    if not path.exists():
        return None

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    block = select_ssh_block(parse_ssh_config_blocks(lines), host)
    if block is None:
        return None

    return SSHHostEntry(
        host=host,
        hostname=block.get("hostname") or "",
        user=block.get("user") or "",
        port=str(block.get("port") or ""),
        identity_file=block.get("identity_file") or "",
    )


def ensure_ssh_config_path(config_path: Path | str) -> Path:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    if not path.exists():
        path.write_text("", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def _line_ending(source: str) -> str:
    if source.endswith("\r\n"):
        return "\r\n"
    if source.endswith("\n"):
        return "\n"
    return "\n"


def _set_or_insert_property(lines: list[str], block: dict, field: str, label: str, value: str) -> None:
    index_key = f"{field}_idx"
    indent_key = f"{field}_indent"
    if block.get(index_key) is not None:
        idx = block[index_key]
        indent = block.get(indent_key) or "  "
        lines[idx] = f"{indent}{label} {value}{_line_ending(lines[idx])}"
        return

    insertion_idx = block["start"] + 1
    for known_field in ("hostname", "user", "port", "identity_file"):
        known_idx = block.get(f"{known_field}_idx")
        if known_idx is not None:
            insertion_idx = max(insertion_idx, known_idx + 1)
    host_line = lines[block["start"]] if lines else "Host placeholder\n"
    lines.insert(insertion_idx, f"  {label} {value}{_line_ending(host_line)}")


def upsert_ssh_host_entry(config_path: Path | str, entry: SSHHostEntry) -> Path:
    path = ensure_ssh_config_path(config_path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    blocks = parse_ssh_config_blocks(lines)
    block = None
    for candidate in blocks:
        if any(pattern == entry.host for pattern in candidate["patterns"]):
            block = candidate
            break

    if block is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(f"Host {entry.host}\n")
        if entry.hostname:
            lines.append(f"  HostName {entry.hostname}\n")
        if entry.user:
            lines.append(f"  User {entry.user}\n")
        if entry.port:
            lines.append(f"  Port {entry.port}\n")
        if entry.identity_file:
            lines.append(f"  IdentityFile {entry.identity_file}\n")
        path.write_text("".join(lines), encoding="utf-8")
        return path

    if entry.hostname:
        _set_or_insert_property(lines, block, "hostname", "HostName", entry.hostname)
    if entry.user:
        _set_or_insert_property(lines, block, "user", "User", entry.user)
    if entry.port:
        _set_or_insert_property(lines, block, "port", "Port", entry.port)
    if entry.identity_file:
        _set_or_insert_property(lines, block, "identity_file", "IdentityFile", entry.identity_file)

    path.write_text("".join(lines), encoding="utf-8")
    return path
