from __future__ import annotations

import json
from pathlib import Path

import sync_remote.self_update as self_update_module
from sync_remote.self_update import (
    _is_supported_uv_tool_install,
    ReleaseInfo,
    choose_update_channel,
    get_display_version,
    normalize_base_version,
    run_self_update,
)


def test_normalize_base_version_strips_main_suffix() -> None:
    assert normalize_base_version("0.3.0-main-2026-03-24") == "0.3.0"
    assert normalize_base_version("0.3.0") == "0.3.0"


def test_choose_update_channel_prefers_main_when_release_is_older() -> None:
    assert choose_update_channel("0.3.0", "0.2.9", None) == "main"


def test_choose_update_channel_prefers_release_when_release_is_newer() -> None:
    assert choose_update_channel("0.3.0-main-2026-03-24", "0.3.1", None) == "release"


def test_choose_update_channel_honors_explicit_channel() -> None:
    assert choose_update_channel("0.3.0", "0.2.0", "release") == "release"
    assert choose_update_channel("0.3.0", None, "main") == "main"


def test_get_display_version_prefers_saved_main_state(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "sync-remote").mkdir()
    state_path = state_dir / "sync-remote" / "self-update.json"
    state_path.write_text(
        json.dumps({"display_version": "0.3.0-main-2026-03-24"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_STATE_HOME", str(state_dir))
    monkeypatch.setattr("sync_remote.self_update.get_installed_package_version", lambda: "0.3.0")

    assert get_display_version() == "0.3.0-main-2026-03-24"


def test_is_supported_uv_tool_install_accepts_uv_tool_shim_path(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "local-bin"
    tool_dir = tmp_path / "uv-tools" / "sync-remote" / "bin"
    bin_dir.mkdir(parents=True)
    tool_dir.mkdir(parents=True)

    target = tool_dir / "sr"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    shim = bin_dir / "sr"
    shim.symlink_to(target)

    monkeypatch.setattr("sync_remote.self_update._uv_tool_bin_dir", lambda: bin_dir)
    monkeypatch.setattr("sync_remote.self_update.sys.argv", [str(shim)])

    assert _is_supported_uv_tool_install() is True


def test_is_supported_uv_tool_install_accepts_bare_command_name_via_path_lookup(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "local-bin"
    tool_dir = tmp_path / "uv-tools" / "sync-remote" / "bin"
    bin_dir.mkdir(parents=True)
    tool_dir.mkdir(parents=True)

    target = tool_dir / "sync-remote"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    shim = bin_dir / "sync-remote"
    shim.symlink_to(target)

    monkeypatch.setattr("sync_remote.self_update._uv_tool_bin_dir", lambda: bin_dir)
    monkeypatch.setattr("sync_remote.self_update.sys.argv", ["sync-remote"])
    monkeypatch.setattr(self_update_module.shutil, "which", lambda name: str(shim) if name == "sync-remote" else None)

    assert _is_supported_uv_tool_install() is True


def test_is_supported_uv_tool_install_rejects_non_uv_tool_command_path(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "local-bin"
    other_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)

    executable = other_dir / "sr"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr("sync_remote.self_update._uv_tool_bin_dir", lambda: bin_dir)
    monkeypatch.setattr("sync_remote.self_update.sys.argv", [str(executable)])

    assert _is_supported_uv_tool_install() is False


def test_run_self_update_uses_release_upgrade_when_invoked_via_uv_tool_shim(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "local-bin"
    tool_dir = tmp_path / "uv-tools" / "sync-remote" / "bin"
    bin_dir.mkdir(parents=True)
    tool_dir.mkdir(parents=True)

    target = tool_dir / "sr"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    shim = bin_dir / "sr"
    shim.symlink_to(target)

    recorded: dict[str, object] = {}

    def fake_install(spec: str):
        recorded["spec"] = spec
        return True, "更新完成"

    monkeypatch.setattr("sync_remote.self_update._uv_tool_bin_dir", lambda: bin_dir)
    monkeypatch.setattr("sync_remote.self_update.sys.argv", [str(shim)])
    monkeypatch.setattr("sync_remote.self_update.fetch_latest_release_info", lambda: ReleaseInfo(version="0.6.1", ref="v0.6.1"))
    monkeypatch.setattr("sync_remote.self_update.get_display_version", lambda: "0.6.0")
    monkeypatch.setattr("sync_remote.self_update._run_uv_tool_install", fake_install)
    monkeypatch.setattr("sync_remote.self_update._clear_state", lambda: recorded.setdefault("cleared", True))

    ok, message = run_self_update(channel="release")

    assert ok is True
    assert recorded["spec"] == "git+https://github.com/emmmdty/sync-cli.git@v0.6.1"
    assert recorded["cleared"] is True
    assert message == "已更新到 release 0.6.1"
