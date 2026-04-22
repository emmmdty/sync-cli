# sync-remote Learn by Example

This guide teaches the tool through concrete workflows instead of internal architecture.

If you are new, follow it once inside a disposable local project directory before you use it in a real repo.

## What It Is and Is Not

Goal: set the right expectations before you start.

Exact command:

```bash
sr --help
```

Expected result:

- You see an SSH-first remote development sync CLI
- You see commands centered around `init`, `upload`, `open`, `watch`, `target`, `config`, and `port-sync`
- You do not see a claim that this is a generic bidirectional sync platform

Common mistakes:

- Expecting automatic bidirectional sync
- Expecting `watch` to delete extra remote files by default
- Expecting the tool to resolve conflicts for you

Go deeper:

- `README.en.md`
- `docs/TROUBLESHOOTING.md`

## Prerequisites and Installation

Goal: make sure your local machine has the minimum dependencies for the main workflow.

Exact command:

```bash
uv tool install .
sr version
```

Expected result:

- `uv tool install .` installs `sync-remote` and `sr`
- `sr version` prints the installed version

Common mistakes:

- Not having `uv`
- Verifying with `uv run` and assuming that means the tool is globally installed
- Planning to use `open`, `watch`, or password auth without `code`, `rsync`, or `sshpass`

Go deeper:

- `README.en.md`

## First-Time Setup

Goal: create the first project-scoped config file.

Exact command:

```bash
sr init
```

Expected result:

- The current directory gets a `sync-remote.yaml`
- Existing SSH Hosts from `~/.ssh/config` can be reused
- Running `init` again appends another target and makes it the default target

Common mistakes:

- Running `init` in the wrong directory
- Starting before SSH keys or SSH Hosts are ready
- Treating the config as global instead of project-scoped

Go deeper:

- `sr init --help`

## Check Your Environment with doctor

Goal: inspect local dependencies and key files before you try to connect.

Exact command:

```bash
sr doctor
sr doctor --json
```

Expected result:

- Text output shows `ssh`, `rsync`, `code`, `sshpass`, config files, SSH keys, aliases, and port resolution status
- JSON output is suitable for scripts or CI
- The command is read-only by default

Common mistakes:

- Assuming `sshpass: MISSING` always means the setup is broken
- Treating `doctor` like a repair command
- Ignoring the suggested next steps

Go deeper:

- `sr doctor --help`
- `docs/TROUBLESHOOTING.md`

## Understand Targets

Goal: understand what a target means in this tool.

Exact command:

```bash
sr target list
sr target list --json
sr config explain
```

Expected result:

- `target list` shows the current default target and all configured targets
- `config explain` shows how the CLI interprets the config right now

Common mistakes:

- Treating targets like a global machine registry
- Reading only the README and skipping `config explain`

Go deeper:

- `sr target list --help`
- `sr config explain --help`

## Switch Targets

Goal: change the default target for the current project.

Exact command:

```bash
sr target use gpu-b
```

Expected result:

- The default target becomes `gpu-b`
- Later `up`, `open`, `watch`, `status`, and `doctor` calls use it unless you override the target explicitly

Common mistakes:

- Using `sr switch gpu-b` without realizing it is a compatibility alias
- Forgetting to confirm the new default target with `sr status`

Go deeper:

- `sr target use --help`
- Compatibility alias: `sr switch --help`

## Fixed-Port Workflow

Goal: understand the simplest fixed-port case.

Exact command:

```bash
sr status
```

Expected result:

- A fixed-port target reports the configured port directly
- No explicit `port-sync` step is needed

Common mistakes:

- Running `port-sync --apply` for a fixed-port target
- Mixing up SSH Host, HostName, and port

Go deeper:

- `README.en.md`
- `sr status --help`

## Dynamic-Port Workflow

Goal: handle dynamic ports safely with preview first.

Exact command:

```bash
sr port-sync --json
sr port-sync --apply --write-ssh-config
```

Expected result:

- The first command previews the resolved port and whether config files would change
- The second command applies the project config update, and updates SSH config only when `--write-ssh-config` is present

Common mistakes:

- Treating `status` or `doctor` like implicit sync commands
- Applying changes before reviewing preview output
- Updating SSH config when you only wanted a project-config change

Go deeper:

- `sr port-sync --help`
- `sr target port-sync --help`
- `docs/MIGRATION.md`

## Push Sync Workflow

Goal: push the local project to the default target or multiple targets.

Exact command:

```bash
sr up
sr up --dry-run
sr up --hosts gpu-a gpu-b
sr up --all-targets
```

Expected result:

- `sr up` pushes to the default target
- `--dry-run` previews the upload
- `--hosts` targets an explicit list
- `--all-targets` is the canonical batch form; `sr upload-all-gpu` is the compatibility alias

Common mistakes:

- Expecting default remote deletion behavior
- Using `--sync-path` without `rsync`
- Writing new docs that still teach `upload-all-gpu` first

Go deeper:

- `sr upload --help`

## Watch Workflow

Goal: keep syncing after local file changes.

Exact command:

```bash
sr watch
sr wt --sync-path src
sr wt --debounce-ms 1500
```

Expected result:

- The command performs one initial upload
- Then it prints the watch plan and keeps polling for changes
- `--sync-path` narrows the watch scope to project-relative paths

Common mistakes:

- Passing raw Windows absolute paths such as `C:\repo\src`
- Expecting local deletions to remove remote files automatically
- Ignoring the console output after a sync failure

Go deeper:

- `sr watch --help`
- `docs/TROUBLESHOOTING.md`

## Open the Remote Project

Goal: upload first, then open the remote directory in VS Code Remote SSH.

Exact command:

```bash
sr op
sr op --watch
sr op --dry-run
```

Expected result:

- `sr op` uploads first and then opens the remote directory with the local `code` command
- `--watch` continues into the watch loop after opening
- `--dry-run` previews the upload and does not open VS Code

Common mistakes:

- Not having the `code` command available
- Running `open` before the SSH alias is usable
- Expecting an “open without upload” mode

Go deeper:

- `sr open --help`

## Validate, Explain, and Migrate Config

Goal: understand when to use `validate`, `explain`, and `migrate`.

Exact command:

```bash
sr config validate
sr config explain
sr config migrate --json
sr config migrate --apply
```

Expected result:

- `validate` confirms the config can be read
- `explain` shows how the CLI interprets it
- `migrate --json` previews the normalized form
- `migrate --apply` writes the current canonical schema back

Common mistakes:

- Applying without reviewing preview output first
- Treating `validate` as a repair command
- Forgetting to run `sr status` after a migration

Go deeper:

- `sr config validate --help`
- `sr config explain --help`
- `sr config migrate --help`

## Troubleshooting

Goal: follow a stable sequence when something goes wrong.

Exact command:

```bash
sr doctor
sr status
sr port-sync --json
```

Expected result:

- You inspect dependencies, config, SSH alias state, and port resolution before deciding whether you need to apply port changes

Common mistakes:

- Blaming the remote machine first
- Ignoring hints from `doctor` and `status`
- Updating SSH config before previewing port resolution

Go deeper:

- `docs/TROUBLESHOOTING.md`

## Legacy Aliases

Goal: know which commands still exist and which ones should stay out of new onboarding.

Exact command:

```bash
sr switch gpu-b
sr del gpu-b
sr upload-all-gpu
python sync_to_remote.py --help
```

Expected result:

- Those entrypoints still work
- New onboarding and automation should prefer `target use`, `target remove`, `upload --all-targets`, and `sync-remote` / `sr`

Common mistakes:

- Teaching legacy aliases in new tutorials
- Assuming “still works” means “still preferred”

Go deeper:

- `README.en.md`
- `README.md`

## Daily Workflow

Goal: use a simple daily sequence that is easy to repeat.

Exact command:

```bash
sr status
sr up
sr op
sr wt --sync-path src
```

Expected result:

- Confirm target and port first
- Push changes
- Open the remote directory when needed
- Use watch only when continuous sync is actually useful

Common mistakes:

- Skipping `status`
- Forgetting that the default target changed earlier
- Leaving `watch` running when you do not need it

Go deeper:

- `README.en.md`

## Safe Recovery

Goal: check the obvious things before you decide the tool is at fault.

Exact command:

```bash
sr status
sr doctor
sr config explain
sr port-sync --json
```

Expected result:

- You confirm the current default target, remote directory, SSH alias state, port resolution, and config source before making changes

Common mistakes:

- Running commands in the wrong project directory
- Uploading without confirming the current default target
- Repeatedly retrying when the dynamic-port environment file is missing

Go deeper:

- `docs/TROUBLESHOOTING.md`
- `docs/MIGRATION.md`
