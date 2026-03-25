from __future__ import annotations

import json

from sync_remote.self_update import choose_update_channel, get_display_version, normalize_base_version


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
