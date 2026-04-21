# sync-remote (English)

SSH-first remote development sync CLI for pushing the current project into a remote development machine over SSH.

`sync-remote` is the canonical command name and `sr` is the short alias.

## What It Is

- SSH-first remote development sync CLI
- Project-scoped config stored in `sync-remote.yaml`
- Safe-by-default diagnostics: `status` and `doctor` do not mutate config
- Explicit support for fixed ports and dynamic provider-resolved ports
- Canonical v2-style command tree: `target`, `config`, and explicit `port-sync`

## Quickstart

```bash
sr init
sr config validate
sr target list
sr up
sr port-sync --json
```

## Canonical Commands

- `sr target list`
- `sr target use gpu-b`
- `sr target remove gpu-b`
- `sr config validate`
- `sr config explain`
- `sr config migrate --apply`
- `sr port-sync --json`
- `sr port-sync --apply --write-ssh-config`

## Compatibility Aliases

Legacy commands still work for existing users:

- `sr switch gpu-b`
- `sr del gpu-b`
- `sr upload-all-gpu`

## Docs

- Chinese guide: `README.md`
- Migration: `docs/MIGRATION.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Release notes template: `docs/RELEASE_NOTES.md`
