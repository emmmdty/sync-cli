# sync-remote

远程同步命令行工具，用来把当前项目目录同步到远端服务器，并提供下载、备份、环境检查、实时同步、VS Code Remote 打开和自更新能力。

主命令是 `sync-remote`，同时提供简写别名 `sr`。

English quickstart: [README.en.md](README.en.md)

## 适用场景

- 需要在本地项目目录和远端开发机之间高频同步代码
- 已经使用 SSH 或 VS Code Remote SSH，希望把日常同步流程命令化
- 同时维护多台服务器，希望在同一份项目配置里切换默认目标或批量上传
- 远端 SSH 端口可能通过 Cpolar 等隧道动态变化
- 希望在任意项目目录里快速初始化配置，而不是复制脚本到每个仓库

## 功能特性

- `init` 会生成或更新当前目录的 `sync-remote.yaml`
- 已有配置时再次执行 `init` 会追加服务器，并把新服务器设为默认值
- 规范命令树使用 `target`、`config` 和显式 `port-sync`
- 支持 `target list`、`target use`、`target remove` 管理多目标配置
- 支持 `config validate`、`config explain`、`config migrate` 检查和规范化配置
- `doctor`、`status` 默认只读，不会静默改写项目配置或 SSH config
- `status --json`、`doctor --json` 可输出结构化诊断结果，适合脚本或 CI 检查
- `upload`、`download`、`open`、`watch`、`doctor` 默认都作用于当前默认服务器
- `upload --hosts` 可一次上传到一个或多个指定服务器
- `upload --all-targets` 会并发上传到配置中的所有服务器，失败不会中断后续任务
- `port-sync` 默认只预览动态端口解析结果，显式 `--apply` 后才会写回项目配置
- `watch` 默认使用安全的轮询后端；可显式指定 `--watch-backend poll`
- 支持 `key` 和 `password` 两种认证模式
- 支持 `auto` 和 `fixed` 两种 SSH 端口模式
- 支持 `version` 查看当前版本，`update` 从 GitHub 自更新
- 兼容命令仍保留，但推荐优先使用 `target`、`config` 和显式 `port-sync`
- 兼容旧入口 `sync_to_remote.py`

## 安装

### 本地安装

```bash
uv tool install .
```

### 开发态安装

```bash
uv tool install --editable .
```

### 仓库内直接运行

```bash
uv run sync-remote --help
uv run sr --help
```

## 首次使用前准备

必须准备：

- `Python 3.10+`
- `uv`
- `ssh`
- 本机 SSH 私钥和公钥
- 远端服务器已写入你的公钥

按需准备：

- 使用 `open` 时需要 VS Code 和 `code` 命令
- 希望获得更好的增量上传体验时建议安装 `rsync`
- 使用 `password` 认证模式时需要安装 `sshpass`
- 使用 `auto` 端口模式时需要准备含 `CPOLAR_USER` 和 `CPOLAR_PASS` 的环境变量文件

推荐首次检查顺序：

```bash
sr --help
sr init
sr doctor
sr status
```

## 快速开始

1. 初始化或追加当前目录的服务器配置：

```bash
sr init
```

2. 检查默认服务器和本机依赖：

```bash
sr status
sr doctor
```

3. 上传到当前默认服务器：

```bash
sr up
```

4. 切换默认服务器后再次上传：

```bash
sr target list
sr target use gpu-b
sr up
```

5. 上传到所有已配置服务器：

```bash
sr up --all-targets
```

6. 校验并解释当前配置：

```bash
sr config validate
sr config explain
```

7. 预览动态端口同步结果；确认后再显式应用：

```bash
sr port-sync --json
sr port-sync --apply --write-ssh-config
```

8. 只上传到指定服务器：

```bash
sr up --hosts gpu-a gpu-b
```

9. 查看版本并按 Release 通道更新：

```bash
sr version
sr update --channel release
```

## 命令一览

### 规范命令

| 功能 | 长命令 | 常用写法 |
| --- | --- | --- |
| 初始化或追加服务器 | `sync-remote init` | `sr init` |
| 上传 | `sync-remote upload` | `sr up` |
| 下载 | `sync-remote download` | `sr dl` |
| 备份 | `sync-remote backup` | `sr backup` |
| 打开远端目录 | `sync-remote open` | `sr op` |
| 实时同步 | `sync-remote watch` | `sr wt` |
| 查看目标列表 | `sync-remote target list` | `sr target list` |
| 切换默认目标 | `sync-remote target use` | `sr target use gpu-b` |
| 删除目标 | `sync-remote target remove` | `sr target remove gpu-b` |
| 预览或应用端口同步 | `sync-remote port-sync` | `sr port-sync --json` |
| 校验配置 | `sync-remote config validate` | `sr config validate` |
| 解释配置 | `sync-remote config explain` | `sr config explain` |
| 迁移配置 | `sync-remote config migrate` | `sr config migrate --apply` |
| 查看版本 | `sync-remote version` | `sr version` |
| 自动更新 | `sync-remote update` | `sr update` |
| 查看配置状态 | `sync-remote status` | `sr status` |
| 环境自检 | `sync-remote doctor` | `sr doctor` |

### 兼容别名

| 历史命令 | 当前建议 |
| --- | --- |
| `sr switch gpu-b` | `sr target use gpu-b` |
| `sr del gpu-b` | `sr target remove gpu-b` |
| `sr upload-all-gpu` | `sr up --all-targets` |

更多参数说明可直接查看帮助：

```bash
sync-remote --help
sync-remote upload --help
sync-remote target --help
sync-remote config --help
sync-remote port-sync --help
sync-remote update --help
```

## 文档导航

- 英文快速参考：`README.en.md`
- 迁移说明：`docs/MIGRATION.md`
- 故障排查：`docs/TROUBLESHOOTING.md`
- 发布说明模板：`docs/RELEASE_NOTES.md`

## 配置说明

运行 `sync-remote init` 后，会在当前目录生成或更新 `sync-remote.yaml`。

- `init` 会优先扫描本机 `~/.ssh/config`，可直接复用已有 Host，也可在流程中新增 Host
- 如果当前目录已经有配置，再次执行 `init` 会追加新的服务器，并把最后追加的 Host 设为 `default_target`
- 每个 `target` 都有自己的远端目录配置，追加 Host 时不再默认和其他 Host 共用同一个远端目录
- `upload`、`download`、`open`、`watch`、`doctor` 都读取 `default_target`
- `target use` 只切换默认目标，不改其他配置
- `target remove` 删除指定目标；删除默认目标时，会把最后一个剩余目标设为默认
- 读取顺序是 `sync-remote.yaml` 优先，找不到时回退到旧配置 `sync_config.yaml`
- 旧版单服务器配置仍可读取，但新的写回结构统一是 `version: 3`

端口模式：

- `auto`：优先从 Cpolar 获取端口，失败时回退 `~/.ssh/config`
- `fixed`：直接使用配置中的固定端口，不访问 Cpolar
- `status`、`doctor` 默认只读；如果需要把解析结果写回配置，使用 `sr port-sync --apply`
- 如果还需要同时更新 `~/.ssh/config`，显式追加 `--write-ssh-config`

远端目录默认由两部分组成：

- `targets.<name>.project.remote_base_dir`
- 当前工作目录名

例如当前目录名为 `demo-project`，某台服务器的远端基础目录为 `/srv/projects`，则该服务器默认远端目录为：

```text
/srv/projects/demo-project
```

### `version: 3` 规范化多目标示例

```yaml
version: 3
default_target: gpu-b
targets:
  gpu-a:
    project:
      remote_base_dir: /srv/gpu-a
      append_project_dir: true
    ssh:
      user: alice
      host: gpu-a
      hostname: gpu-a.internal
      ssh_config_path: ~/.ssh/config
      ssh_key_path: ~/.ssh/id_ed25519
      known_hosts_check: true
      auth_mode: key
    port:
      kind: fixed
      value: 2222
  gpu-b:
    project:
      remote_base_dir: /srv/gpu-b
      append_project_dir: true
    ssh:
      user: bob
      host: gpu-b
      hostname: example.tcp.vip.cpolar.cn
      ssh_config_path: ~/.ssh/config
      ssh_key_path: ~/.ssh/id_ed25519
      known_hosts_check: true
      auth_mode: password
    port:
      kind: provider
      resolved: null
      provider:
        type: cpolar
        tunnel_name: prod-tunnel
        env_path: ~/.env.prod
sync:
  transport: rsync
  max_file_size_mb: 50
  excludes:
    - .git
    - .venv
backup:
  excludes:
    - .git
    - .venv
```

上面这份配置里：

- `sr up`、`sr status`、`sr doctor` 默认都会走 `gpu-b`
- `sr target use gpu-a` 会把默认服务器切到 `gpu-a`
- `sr target remove gpu-b` 会删除 `gpu-b` 并把剩余服务器设为默认
- `sr up --hosts gpu-a gpu-b` 会并发上传到 `gpu-a` 和 `gpu-b`
- `sr up --all-targets` 会并发上传到所有已配置服务器
- `sr config validate` 会检查配置能否被正确读取
- `sr config migrate --apply` 会把旧结构规范化写回为 `version: 3`
- `sr port-sync --json` 只预览端口解析结果，不会写配置
- `sr port-sync --apply --write-ssh-config` 才会同时更新项目配置和 SSH config

如果你同时维护 `~/.ssh/config`，可写成：

```sshconfig
Host gpu-a
  HostName gpu-a.internal
  User alice
  Port 2222
  IdentityFile ~/.ssh/id_ed25519

Host gpu-b
  HostName example.tcp.vip.cpolar.cn
  User bob
  Port 22
  IdentityFile ~/.ssh/id_ed25519
```

## 典型工作流

### 上传到默认服务器

```bash
sr up
```

### 仅预览上传内容

```bash
sr up --dry-run
```

### 切换默认服务器

```bash
sr target list
sr target use gpu-a
```

### 删除某台服务器

```bash
sr target remove gpu-b
```

### 下载远端快照

```bash
sr dl
```

### 上传后打开远端目录

```bash
sr op
```

### 持续监听本地改动

```bash
sr watch
sr watch --watch-backend poll
sync-remote open --watch
```

### 批量上传到所有服务器

```bash
sr up --all-targets
```

### 批量上传到指定服务器

```bash
sr up --hosts gpu-a gpu-b
```

### 检查和迁移配置

```bash
sr config validate
sr config explain
sr config migrate --apply
sr status --json
sr doctor --json
```

### 预览或应用端口同步

```bash
sr port-sync --json
sr port-sync --apply --write-ssh-config
```

### 查看版本并自更新

```bash
sr version
sr update
sr update --channel main
sr update --channel release
```

`update` 只支持通过 `uv tool install` 或 `uv tool install --editable` 安装的命令自动更新。  
如果当前是仓库内 `uv run`、源码直接执行或其他安装方式，命令会给出手动更新指令，不会原地改写当前源码目录。

## 兼容旧入口

仓库仍保留 `sync_to_remote.py`，但它本身只是兼容包装层，会把旧调用方式转发到新的 `sync-remote` CLI。

推荐直接使用：

- `sync-remote`
- `sr`

例如下面这些旧用法仍然可以继续工作：

```bash
python sync_to_remote.py
python sync_to_remote.py upload
python sync_to_remote.py switch gpu-b
```

## 开发与测试

安装开发依赖：

```bash
uv sync --locked --group dev
```

运行测试：

```bash
uv run pytest -q
```

构建包：

```bash
uv build
```

## 许可证

本项目使用 MIT License。
