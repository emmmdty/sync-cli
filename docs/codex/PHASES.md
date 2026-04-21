# Codex staged execution plan for `sync-cli`

This file is the execution contract for phased, autonomous repo modification.

## Global rules

- Prefer small, verifiable phases.
- Do not move to the next phase until the current phase is accepted.
- Use dedicated phase worktrees when possible.
- Merge back to `main` after each accepted phase.
- Remove phase worktrees and delete phase branches after merge.
- Final state must be one clean `main` branch and no leftover worktrees.

## Recommended shell pattern

Assume the main repo is checked out on `main`.

```bash
export WT_ROOT="${WT_ROOT:-../sync-cli-codex-worktrees}"
mkdir -p "$WT_ROOT"

# Example phase worktree
git worktree add "$WT_ROOT/phase-01" -b codex/phase-01-stabilize main
```

If Codex is not allowed to write outside the repo, relaunch it with an additional writable directory, for example:
```bash
codex --profile repo-autonomous --add-dir .. 
```

If running phase-by-phase, it is also acceptable to start Codex directly in each phase worktree.

---

## Phase 0 — Baseline and safety rails

### Goals
- capture the current repo baseline
- confirm current test status
- identify existing command surface and compatibility obligations
- prepare progress tracking

### Required actions
- inspect package metadata, command entrypoints, docs, transports, tests, CI
- run the current test suite
- create or update `docs/codex/PROGRESS.md` from the template
- record obvious risks and unsafe behaviors
- do not make broad product changes in this phase

### Acceptance
- current tests executed and results recorded
- `docs/codex/PROGRESS.md` exists and is meaningful
- no accidental product-surface breakage introduced

---

## Phase 1 — Stability and safety fixes

### Goals
Fix unsafe or misleading behavior before larger refactors.

### Scope
At minimum, address:
- archive-mode partial sync safety
- `doctor` / `status` mutation hazards
- clearer failure paths for transports and diagnostics
- regression tests for fixed-port and dynamic-port branches
- regression tests for no unintended config mutation

### Required actions
- add or tighten tests around the unsafe boundary before or together with code changes
- if a feature cannot be made safe immediately, reject it explicitly rather than behaving misleadingly
- preserve the old public commands as aliases if new canonical names are introduced later

### Acceptance
Run, at minimum:
```bash
uv sync --group dev
uv run pytest -q
```

If you add new helper scripts or checks, run them too.

Phase-specific acceptance evidence must include:
- which bug / hazard was fixed
- which tests were added
- why the new behavior is safer

### Merge gate
Do not merge unless:
- tests pass
- behavior is safer than before
- compatibility impact is documented

---

## Phase 2 — CLI and config normalization

### Goals
Professionalize the command tree and normalize configuration without breaking existing users silently.

### Scope
At minimum, implement or stage:
- canonical v2 command tree
- compatibility aliases and deprecation messaging
- config validation / migration / explanation flow
- explicit modeling for fixed port vs dynamic port/provider
- exit codes and structured output where appropriate
- improved help text with examples

### Required actions
- keep old aliases working unless explicitly deprecated with docs and tests
- add tests for parser / help / config migration / compatibility
- update docs in lockstep with command changes

### Acceptance
At minimum:
```bash
uv run pytest -q
```

And additionally validate:
- new help output
- compatibility aliases
- config migration / validation / explanation path
- README and help consistency for changed commands

### Merge gate
Do not merge unless:
- old commands still work or are clearly deprecated
- config migration is tested
- help and docs are aligned

---

## Phase 3 — Watch, UX, docs, and release readiness

### Goals
Improve sync experience, observability, and docs while preserving product boundaries.

### Scope
Only after Phases 1 and 2 are stable:
- improve watch implementation or add a safer backend selection model
- improve status / plan / preview ergonomics
- strengthen Windows + WSL behavior where feasible
- rewrite README and docs into a coherent Chinese-first bilingual set
- add troubleshooting and migration docs
- add release-note structure

### Required actions
- avoid speculative overengineering
- do not ship broad two-way sync in this phase
- keep diagnostics read-only by default
- keep remote-side effects explicit and previewable

### Acceptance
At minimum:
```bash
uv run pytest -q
```

Also run any added doc consistency or smoke checks.

Phase evidence must include:
- user-facing improvements
- docs added or rewritten
- any dependency changes and why they are justified

### Merge gate
Do not merge unless:
- tests pass
- docs are coherent
- the product boundary remains narrow and explicit

---

## Optional Phase 4 — Limited pull / snapshot / recovery hardening

### Goals
Strengthen safe pull / recovery primitives without claiming full two-way sync.

### Scope
Allowed:
- snapshot / restore
- drift detection
- safe pull / fetch improvements
- limited mirror mode if heavily guarded

Not allowed by default:
- silent bidirectional conflict resolution
- broad default delete propagation
- vague “supports two-way sync” claims without state model and tests

### Acceptance
- targeted tests for snapshot / restore / drift
- explicit docs for risk and behavior
- no default-destructive behavior

---

## Final cleanup phase

### Required actions
- ensure all accepted phase branches are merged into `main`
- remove all phase worktrees
- delete all temporary phase branches
- run final tests on `main`
- update `docs/codex/PROGRESS.md` with final outcome
- confirm `git status --short` is clean on `main`

### Final acceptance
- only `main` remains as the working branch
- no leftover worktrees
- no uncommitted changes
- final report written
