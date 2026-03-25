# sync-remote

远程同步命令行工具，用来把当前项目目录同步到远端服务器，并提供下载、备份、环境检查、实时同步、VS Code Remote 打开和自更新能力。

主命令是 `sync-remote`，同时提供简写别名 `sr`。

## 适用场景

- 需要在本地项目目录和远端开发机之间高频同步代码
- 已经使用 SSH 或 VS Code Remote SSH，希望把日常同步流程命令化
- 同时维护多台服务器，希望在同一份项目配置里切换默认目标或批量上传
- 远端 SSH 端口可能通过 Cpolar 等隧道动态变化
- 希望在任意项目目录里快速初始化配置，而不是复制脚本到每个仓库

## 功能特性

- `init` 会生成或更新当前目录的 `sync-remote.yaml`
- 已有配置时再次执行 `init` 会追加服务器，并把新服务器设为默认值
- 支持 `switch`、`del`、`status` 管理多服务器配置
- `upload`、`download`、`open`、`watch`、`doctor` 默认都作用于当前默认服务器
- `upload-all-gpu` 可按顺序上传到配置中的所有服务器，失败不会中断后续任务
- 支持 `key` 和 `password` 两种认证模式
- 支持 `auto` 和 `fixed` 两种 SSH 端口模式
- 支持 `version` 查看当前版本，`update` 从 GitHub 自更新
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
sr switch gpu-b
sr up
```

5. 上传到所有已配置服务器：

```bash
sr upload-all-gpu
```

6. 查看版本并按 Release 通道更新：

```bash
sr version
sr update --channel release
```

## 命令一览

| 功能 | 长命令 | 简写 |
| --- | --- | --- |
| 初始化或追加服务器 | `sync-remote init` | `sr init` |
| 上传 | `sync-remote upload` | `sr up` |
| 下载 | `sync-remote download` | `sr dl` |
| 备份 | `sync-remote backup` | `sr backup` |
| 打开远端目录 | `sync-remote open` | `sr op` |
| 实时同步 | `sync-remote watch` | `sr wt` |
| 切换默认服务器 | `sync-remote switch` | `sr switch` |
| 删除服务器 | `sync-remote del` | `sr del` |
| 上传到所有服务器 | `sync-remote upload-all-gpu` | `sr upload-all-gpu` |
| 查看版本 | `sync-remote version` | `sr version` |
| 自动更新 | `sync-remote update` | `sr update` |
| 查看配置状态 | `sync-remote status` | `sr status` |
| 环境自检 | `sync-remote doctor` | `sr doctor` |

更多参数说明可直接查看帮助：

```bash
sync-remote --help
sync-remote upload --help
sync-remote switch --help
sync-remote update --help
```

## 配置说明

运行 `sync-remote init` 后，会在当前目录生成或更新 `sync-remote.yaml`。

- `init` 会优先扫描本机 `~/.ssh/config`，可直接复用已有 Host，也可在流程中新增 Host
- 如果当前目录已经有配置，再次执行 `init` 会追加新的服务器，并把最后追加的 Host 设为 `default_host`
- `upload`、`download`、`open`、`watch`、`doctor` 都读取 `default_host`
- `switch` 只切换默认服务器，不改其他配置
- `del` 删除指定服务器；删除默认服务器时，会把最后一个剩余服务器设为默认
- 读取顺序是 `sync-remote.yaml` 优先，找不到时回退到旧配置 `sync_config.yaml`
- 旧版单服务器配置仍可读取，但新的写回结构统一是 `version: 2`

端口模式：

- `auto`：优先从 Cpolar 获取端口，失败时回退 `~/.ssh/config`
- `fixed`：直接使用配置中的固定端口，不访问 Cpolar

远端目录默认由两部分组成：

- `project.remote_base_dir`
- 当前工作目录名

例如当前目录名为 `demo-project`，远端基础目录为 `/srv/projects`，则默认远端目录为：

```text
/srv/projects/demo-project
```

### `version: 2` 多服务器示例

```yaml
version: 2
project:
  remote_base_dir: /srv/projects
  append_project_dir: true
default_host: gpu-b
servers:
  gpu-a:
    user: alice
    host: gpu-a
    hostname: gpu-a.internal
    port_mode: fixed
    port: 2222
    ssh_config_path: ~/.ssh/config
    ssh_key_path: ~/.ssh/id_ed25519
    known_hosts_check: true
    auth_mode: key
    cpolar:
      tunnel_name: ""
      env_path: ~/.env
  gpu-b:
    user: bob
    host: gpu-b
    hostname: example.tcp.vip.cpolar.cn
    port_mode: auto
    port: null
    ssh_config_path: ~/.ssh/config
    ssh_key_path: ~/.ssh/id_ed25519
    known_hosts_check: true
    auth_mode: password
    cpolar:
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
- `sr switch gpu-a` 会把默认服务器切到 `gpu-a`
- `sr del gpu-b` 会删除 `gpu-b` 并把剩余服务器设为默认
- `sr upload-all-gpu` 会依次上传到 `gpu-a` 和 `gpu-b`

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
sr switch
sr switch gpu-a
```

### 删除某台服务器

```bash
sr del
sr del gpu-b
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
sync-remote open --watch
```

### 批量上传到所有服务器

```bash
sr upload-all-gpu
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
