#!/usr/bin/env python3
"""Compatibility wrapper for the new sync-remote CLI."""

from __future__ import annotations

import sys

from sync_remote.cli import main


KNOWN_COMMANDS = {
    "init",
    "upload",
    "up",
    "download",
    "dl",
    "backup",
    "open",
    "op",
    "watch",
    "wt",
    "status",
    "doctor",
}


def _normalize_args(argv: list[str]) -> list[str]:
    if not argv:
        return ["upload"]
    if argv[0] in {"-h", "--help"}:
        return argv
    if argv[0] in KNOWN_COMMANDS:
        return argv
    return ["upload", *argv]


if __name__ == "__main__":
    raise SystemExit(main(_normalize_args(sys.argv[1:])))
