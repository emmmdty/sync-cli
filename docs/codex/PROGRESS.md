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
- Phase: Phase 0
- Branch: `codex/phase-00-baseline`
- Worktree: `/home/tjk/myProjects/sync-cli/.worktrees/phase-00-baseline`
- Goal: capture the baseline, track Codex phase docs in-repo, and leave integration `main` ready for Phase 1.
- Planned acceptance:
  - baseline tests executed and recorded
  - `docs/codex/PROGRESS.md` exists and is meaningful
  - no product behavior changes introduced in Phase 0

## Completed phases

### Phase 0
- Summary:
- Tests:
- Merge result:
- Cleanup result:

### Phase 1
- Summary:
- Tests:
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
- `status` and dynamic-port resolution currently mutate config/SSH state and must be made read-only by default in Phase 1.
- `port-sync` needs to be introduced without widening the product scope.
- Final cleanup must distinguish Codex-created worktrees/branches from pre-existing user worktrees/branches that were explicitly preserved.

## Final cleanup checklist
- [ ] all accepted phases merged to `main`
- [ ] temporary branches deleted
- [ ] temporary worktrees removed
- [ ] final tests run on `main`
- [ ] `git status --short` is clean
