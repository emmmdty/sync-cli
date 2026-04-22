# Codex progress log

## 2026-04-22 follow-up audit: diagnostics/update help alignment
- Branch: `fix/audit-followup`
- Worktree: `/home/tjk/myProjects/sync-cli/.worktrees/audit-followup`
- Baseline tests executed before edits:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q`
  - Result: `109 passed in 0.98s`
- Additional evidence collected:
  - root and wrapper help already reflected canonical commands and compatibility aliases correctly
  - README and tutorial links were already present and covered the expected beginner workflows
  - remaining gaps were concentrated in leaf help wording, not in command behavior
- Concrete follow-up findings:
  - `sync-remote update --help` said auto-update only supported `uv tool install`, while README documented both `uv tool install` and `uv tool install --editable`
  - `status --help` and `doctor --help` did not explicitly say they are read-only, even though the product rules and README rely on that safety promise
  - `status --help` and `doctor --help` examples did not show the supported `--json` form, which made the machine-readable path less discoverable
- Changes implemented:
  - aligned `update --help` with the documented supported install modes
  - added explicit read-only wording to `status --help` and `doctor --help`
  - added `sr status --json` and `sr doctor --json` examples to those help surfaces
  - tightened `tests/test_help.py` to lock the updated contracts
- Verification:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_help.py::test_status_help_describes_report_contents tests/test_help.py::test_doctor_help_describes_checks tests/test_help.py::test_update_help_describes_channels -q`
  - Result: `3 passed in 0.11s`

## 2026-04-22 audit: help / docs / learnability sync
- Branch: `fix/docs-help-audit`
- Worktree: `/home/tjk/myProjects/sync-cli/.worktrees/audit-help-docs`
- Root preservation: original root worktree on `main` stayed untouched because it was already dirty.
- Baseline tests executed before major edits:
  - `uv run pytest -q`
  - Result: `88 passed in 0.98s`
- Concrete audit findings:
  - root help did not clearly distinguish canonical commands from compatibility aliases
  - `target use`, `target remove`, `target port-sync`, `config validate`, `config explain`, and `config migrate` lacked beginner-safe behavior notes and real examples
  - wrapper help used the wrong program identity path unless invoked through explicit wrapper context, and did not explain that `sync_to_remote.py` is only a compatibility entrypoint
  - README / README.en had no prominent beginner path and no case-based tutorial link
  - no scenario tutorial existed that taught fixed-port vs dynamic-port workflows, preview/apply behavior, safe recovery, and legacy alias boundaries
  - no lightweight regression test checked tutorial links, tutorial coverage, or whether documented core commands still exposed `--help`
- Changes implemented:
  - synchronized root help, canonical subcommand help, and wrapper help around canonical commands, compatibility aliases, examples, and safe preview/apply wording
  - clarified product positioning as an SSH-first remote-development sync CLI in Chinese help and README text
  - added bilingual beginner tutorials: `docs/LEARN_BY_EXAMPLE.md` and `docs/LEARN_BY_EXAMPLE.en.md`
  - added README and README.en “Start Here / 新手先看” sections linking the tutorial
  - updated migration and troubleshooting docs to point beginners back to the tutorial path
  - added regression coverage for help contracts, wrapper help, tutorial links, tutorial section coverage, and documented command help entrypoints
- Verification:
  - `uv run pytest tests/test_help.py tests/test_wrapper.py tests/test_docs_consistency.py tests/test_packaging.py -q`
  - Result: `44 passed in 0.26s`
  - `uv run pytest -q`
  - Result: `109 passed in 0.76s`
- Remaining known gaps:
  - troubleshooting remains a compact bilingual note rather than separate full Chinese and English documents
  - this audit intentionally did not widen product scope into pull/recovery automation or bidirectional sync semantics

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
- Phase: Final cleanup (complete)
- Branch: `main`
- Worktree: `/home/tjk/myProjects/sync-cli/.worktrees/codex-main-integration`
- Goal: accepted phases merged, optional Phase 4 deferred intentionally, and Codex-created phase branches/worktrees cleaned up while preserved external worktrees remain untouched by design.
- Planned acceptance:
  - full test suite passes on `main`
  - Phase 3 work is merged and reverified on `main`
  - Phase 4 is explicitly deferred
  - final cleanup evidence is recorded

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
- Merge result: merged `codex/phase-01-stabilize` into integration `main`
- Cleanup result: removed the `codex/phase-01-stabilize` worktree and deleted the phase branch

### Phase 2
- Summary: introduced canonical `target`, `config`, and `port-sync` command trees; added `upload --all-targets`; normalized write-back to v3 `default_target` / `targets` config; kept legacy `switch`, `del`, and `upload-all-gpu` as compatibility aliases; added JSON output and explicit preview/apply flows for config migration and port sync; updated README/help to document the new canonical surface and the read-only default for diagnostics.
- Tests:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_config.py::test_load_project_config_supports_v3_targets_and_default_target tests/test_config.py::test_write_project_config_normalizes_to_v3_targets_schema tests/test_commands.py::test_target_list_json_reports_default_target tests/test_commands.py::test_target_use_updates_default_target_and_persists_config tests/test_commands.py::test_upload_all_targets_dispatches_to_all_targets tests/test_commands.py::test_config_validate_and_explain_json tests/test_commands.py::test_config_migrate_preview_json_does_not_write_file tests/test_commands.py::test_config_migrate_apply_writes_v3_schema tests/test_commands.py::test_target_port_sync_preview_json_does_not_write_by_default tests/test_commands.py::test_target_port_sync_apply_updates_config_and_ssh_when_opted_in tests/test_wrapper.py::test_normalize_args_recognizes_new_command_names -q` -> `11 passed in 0.48s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_cli_init.py -q` -> `7 passed in 0.34s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_help.py tests/test_packaging.py -q` -> `21 passed in 0.64s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q` -> `82 passed in 2.47s`
- Merge result: merged `codex/phase-02-cli-config` into integration `main`
- Cleanup result: removed the `codex/phase-02-cli-config` worktree and deleted the phase branch

### Phase 3
- Summary: made watch mode more legible and explicit by adding a safe `--watch-backend` selector, startup watch-plan output, and normalized `sync-path` handling for Windows-style separators; added read-only `--json` output for `status` and `doctor` with actionable hints; added English quickstart plus migration, troubleshooting, and release-note docs to make the repo release-ready without widening product scope.
- Tests:
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_transport.py tests/test_help.py tests/test_commands.py -q` -> `59 passed in 3.23s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest tests/test_packaging.py -q` -> `5 passed in 0.05s`
  - `PYTHONPATH=$PWD/src /home/tjk/myProjects/sync-cli/.venv/bin/python -m pytest -q` -> `88 passed in 1.80s`
- Merge result: merged `codex/phase-03-watch-docs` into integration `main`
- Cleanup result: removed the `codex/phase-03-watch-docs` worktree and deleted the phase branch

### Phase 4 (optional)
- Summary: deferred intentionally. Snapshot / pull / recovery hardening would need additional state-model decisions and risk widening the product beyond a safe SSH remote-development sync CLI in this run.
- Tests: not started
- Merge result: not applicable
- Cleanup result: not applicable

## Open risks / deferred items
- Phase 4 snapshot / pull / recovery hardening is deferred to keep scope narrow and avoid accidental two-way-sync semantics.
- Pre-existing user worktrees and the preserved dirty root worktree were intentionally left untouched; final cleanliness is verified in the dedicated integration `main` worktree.

## Final cleanup checklist
- [x] all accepted phases merged to `main`
- [x] temporary branches deleted
- [x] temporary phase worktrees removed
- [x] final tests run on `main`
- [x] `git status --short` is clean
