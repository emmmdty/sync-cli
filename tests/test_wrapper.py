from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from sync_remote.cli import main


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_to_remote_module", ROOT / "sync_to_remote.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

_normalize_args = MODULE._normalize_args


def test_normalize_args_recognizes_new_command_names() -> None:
    assert _normalize_args(["switch", "gpu-b"]) == ["switch", "gpu-b"]
    assert _normalize_args(["del", "gpu-a"]) == ["del", "gpu-a"]
    assert _normalize_args(["upload-all-gpu"]) == ["upload-all-gpu"]
    assert _normalize_args(["version"]) == ["version"]
    assert _normalize_args(["update", "--channel", "main"]) == ["update", "--channel", "main"]
    assert _normalize_args(["target", "list"]) == ["target", "list"]
    assert _normalize_args(["config", "validate"]) == ["config", "validate"]
    assert _normalize_args(["port-sync", "--json"]) == ["port-sync", "--json"]


def test_wrapper_help_uses_wrapper_prog_name_and_mentions_canonical_commands(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sync_remote.cli.sys.argv", ["sync_to_remote.py"])

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: sync_to_remote.py" in captured.out
    assert "兼容入口:" in captured.out
    assert "`sync-remote` 和 `sr` 仍是推荐命令名" in captured.out
    assert "SSH-first 远程开发同步 CLI" in captured.out
