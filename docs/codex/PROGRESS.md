# Codex progress log

## Baseline
- Current branch: preserved root on `main` is dirty and left untouched; phased execution starts from isolated worktrees.
- Current version / package facts observed: package `sync-remote` version `0.4.3`; entrypoints `sync-remote` and `sr`; compatibility wrapper `sync_to_remote.py`.
- Current public commands observed: `init`, `upload`/`up`, `download`/`dl`, `backup`, `open`/`op`, `watch`/`wt`, `switch`, `del`, `upload-all-gpu`, `version`, `update`, `status`, `doctor`.
- Current config shape: readers support legacy `sync_config.yaml` plus `sync-remote.yaml` with `version: 1` and `version: 2`; active model mirrors `default_host` into top-level `project`, `connection`, and `cpolar`.
- Current tests executed:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q`
  - Result: `66 passed in 1.58s`
- Baseline result: clean test baseline confirmed in `codex/phase-00-baseline`; `docs/codex/PHASES.md` and `docs/codex/PROGRESS_TEMPLATE.md` added as tracked repo docs for phased execution.
- Known risks observed at baseline:
  - `status` persists resolved auto ports back into YAML and fixture SSH config.
  - dynamic-port resolution in `transport.py` mutates SSH config as a side effect.
  - `doctor` / `status` are documented as diagnostics but share write-through resolution helpers.
  - `port-sync` is required by repo instructions but absent from the current CLI.
  - fresh-worktree `uv sync` is blocked in this sandbox because the lockfile registry points to a network mirror; phase verification uses the existing repo `.venv` plus worktree `PYTHONPATH`.

## Active phase
- Phase: Phase 1
- Branch: `codex/phase-01-stabilize`
- Worktree: `/home/tjk/myProjects/sync-cli/.worktrees/codex-main-integration/.worktrees/phase-01`
- Goal: remove implicit config and SSH writes from diagnostics and runtime port resolution, with regression coverage for read-only behavior.
- Planned acceptance:
  - diagnostics remain read-only by default
  - runtime port resolution no longer mutates YAML or SSH config
  - full test suite passes after regression coverage is added

## Completed phases

### Phase 0
- Summary: added tracked `docs/codex/PHASES.md`, `docs/codex/PROGRESS_TEMPLATE.md`, and baseline `docs/codex/PROGRESS.md`; confirmed current command surface, config shape, test baseline, and known safety hazards.
- Tests: `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q` -> `66 passed in 1.58s`
- Merge result: merged `codex/phase-00-baseline` into integration `main`
- Cleanup result: removed `codex/phase-00-baseline` worktree and deleted the phase branch

### Phase 1
- Summary: made `status`, `doctor`, and multi-host upload port resolution read-only by default; removed implicit SSH-config writes from `get_port_from_cpolar()` and removed CLI-side write-through persistence for resolved auto ports.
- Tests:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_commands.py::test_status_does_not_persist_resolved_auto_port_to_yaml_or_ssh_config tests/test_commands.py::test_doctor_does_not_persist_resolved_auto_port_to_yaml_or_ssh_config tests/test_commands.py::test_upload_hosts_does_not_persist_auto_port_resolution tests/test_transport.py::test_get_port_from_cpolar_does_not_update_ssh_config -q` -> `4 passed in 0.41s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q` -> `69 passed in 2.43s`
- Merge result:
- Cleanup result:

### Phase 2
- Summary:
- Tests:
- Merge result:
- Cleanup result:

### Phase 3
- Summary:
- Tests:
- Merge result:
- Cleanup result:

### Phase 4 (optional)
- Summary:
- Tests:
- Merge result:
- Cleanup result:

## Open risks / deferred items
- `port-sync` needs to be introduced without widening the product scope.
- Final cleanup must distinguish Codex-created worktrees/branches from pre-existing user worktrees/branches that were explicitly preserved.

## Final cleanup checklist
- [ ] all accepted phases merged to `main`
- [ ] temporary branches deleted
- [ ] temporary worktrees removed
- [ ] final tests run on `main`
- [ ] `git status --short` is clean
