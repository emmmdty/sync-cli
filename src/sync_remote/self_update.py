from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import requests

REPOSITORY_GIT_URL = "https://github.com/emmmdty/sync-cli.git"
REPOSITORY_API_BASE = "https://api.github.com/repos/emmmdty/sync-cli"
PACKAGE_NAME = "sync-remote"
EXECUTABLE_NAMES = {"sync-remote", "sr"}


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    ref: str


def normalize_base_version(version: str) -> str:
    return version.split("-main-", maxsplit=1)[0]


def _version_key(version: str) -> tuple[int, ...]:
    normalized = normalize_base_version(version).lstrip("v")
    parts = normalized.split(".")
    return tuple(int(part) for part in parts if part.isdigit())


def choose_update_channel(current_version: str, latest_release: str | None, requested_channel: str | None) -> str:
    if requested_channel in {"main", "release"}:
        return requested_channel
    if latest_release is None:
        return "main"
    if _version_key(latest_release) < _version_key(current_version):
        return "main"
    return "release"


def _state_dir() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / PACKAGE_NAME


def _state_path() -> Path:
    return _state_dir() / "self-update.json"


def _load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(data: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def _clear_state() -> None:
    path = _state_path()
    if path.exists():
        path.unlink()


def get_installed_package_version() -> str:
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        project_file = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if project_file.exists():
            match = re.search(r'^version = "([^"]+)"$', project_file.read_text(encoding="utf-8"), re.MULTILINE)
            if match:
                return match.group(1)
        return "0.0.0"


def get_display_version() -> str:
    installed_version = get_installed_package_version()
    state = _load_state()
    display_version = state.get("display_version")
    if display_version and normalize_base_version(display_version) == normalize_base_version(installed_version):
        return display_version
    return installed_version


def _parse_release_info(raw_ref: str | None) -> ReleaseInfo | None:
    if not raw_ref:
        return None
    match = re.search(r"v?(\d+\.\d+\.\d+)", raw_ref)
    if match is None:
        return None
    return ReleaseInfo(version=match.group(1), ref=raw_ref)


def fetch_latest_release_info() -> ReleaseInfo | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": PACKAGE_NAME,
    }

    try:
        response = requests.get(f"{REPOSITORY_API_BASE}/releases/latest", headers=headers, timeout=10)
        if response.status_code == 200:
            release = _parse_release_info(response.json().get("tag_name"))
            if release is not None:
                return release
    except requests.RequestException:
        pass

    try:
        response = requests.get(f"{REPOSITORY_API_BASE}/tags?per_page=1", headers=headers, timeout=10)
        if response.status_code == 200:
            tags = response.json()
            if tags:
                return _parse_release_info(tags[0].get("name"))
    except requests.RequestException:
        return None

    return None


def _uv_tool_bin_dir() -> Path | None:
    result = subprocess.run(
        ["uv", "tool", "dir", "--bin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    return Path(value)


def _is_supported_uv_tool_install() -> bool:
    bin_dir = _uv_tool_bin_dir()
    if bin_dir is None:
        return False
    argv0 = Path(sys.argv[0])
    try:
        resolved = argv0.resolve()
    except OSError:
        return False
    return resolved.parent == bin_dir.resolve() and resolved.name in EXECUTABLE_NAMES


def _run_uv_tool_install(spec: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["uv", "tool", "install", "--upgrade", spec],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True, result.stdout.strip() or "更新完成"
    detail = result.stderr.strip() or result.stdout.strip() or "未知错误"
    return False, detail


def run_self_update(*, channel: str | None) -> tuple[bool, str]:
    if not _is_supported_uv_tool_install():
        return (
            False,
            "当前运行方式不支持自动更新；请使用 `uv tool install --upgrade git+https://github.com/emmmdty/sync-cli.git@<ref>` 手动更新。",
        )

    current_display = get_display_version()
    latest_release = fetch_latest_release_info()
    chosen_channel = choose_update_channel(
        current_display,
        latest_release.version if latest_release is not None else None,
        channel,
    )

    if chosen_channel == "release":
        if latest_release is None:
            return False, "未找到可用的 Release/Tag，无法按 release 通道更新。"
        ok, detail = _run_uv_tool_install(f"git+{REPOSITORY_GIT_URL}@{latest_release.ref}")
        if not ok:
            return False, f"Release 更新失败: {detail}"
        _clear_state()
        return True, f"已更新到 release {latest_release.version}"

    ok, detail = _run_uv_tool_install(f"git+{REPOSITORY_GIT_URL}@main")
    if not ok:
        return False, f"Main 更新失败: {detail}"

    display_version = f"{normalize_base_version(current_display)}-main-{date.today():%Y-%m-%d}"
    _write_state({"display_version": display_version, "channel": "main"})
    return True, f"已更新到 main {display_version}"
