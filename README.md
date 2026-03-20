# sync-remote

远程同步命令行工具，用来把当前项目目录同步到远端服务器，并提供下载、备份、环境检查和 VS Code Remote 打开能力。

项目主命令是 `sync-remote`，同时提供简写命令 `sr`。

## 适用群体

这个工具主要适合以下用户：

- 需要在本地项目目录和远端服务器目录之间高频同步代码的开发者
- 已经通过 SSH / VS Code Remote SSH 连接远端机器，希望把日常同步操作命令化的用户
- 远端 SSH 端口会变化，希望工具能自动获取最新端口并继续工作的用户
- 希望在任意目录快速初始化同步配置，而不是把脚本复制到每个项目目录中的用户
- 需要同时具备上传、下载、备份、自检和远端打开能力的小型团队或个人开发者

## 功能特性

- 在任意目录生成本地配置文件 `sync-remote.yaml`
- 增量上传当前目录到远端目录
- 适合通过 Cpolar 等隧道暴露 SSH，且公网端口经常变化的场景
- 将远端目录打包下载为 `tar.gz`
- 将当前目录备份到上级目录
- 上传后直接用 VS Code Remote SSH 打开远端目录
- 检查依赖、配置、SSH 配置文件、公钥和端口解析状态
- 兼容旧入口 `sync_to_remote.py`

## 安装

### 本地安装

```bash
uv tool install .
```

### 开发态安装

源码会实时生效，适合持续开发这个工具：

```bash
uv tool install --editable .
```

### 仓库内直接运行

```bash
uv run sync-remote --help
uv run sr --help
```

## 新电脑首次使用准备

在一台新电脑上首次使用本工具，建议先确认下面这些准备项。

### 必须准备

- `Python 3.10+`
- `uv`
- `ssh`
- 本机 SSH 私钥和公钥
- 远端服务器已添加你的 SSH 公钥

### 按需准备

- 如果要使用 `open`，需要安装 VS Code 和 `code` 命令
- 如果希望获得更好的增量上传体验，建议安装 `rsync`
- 如果使用 `auto` 端口模式，还需要准备 Cpolar 账号，以及包含 `CPOLAR_USER` 和 `CPOLAR_PASS` 的环境变量文件

### 推荐首次检查顺序

```bash
sr --help
sr init
sr doctor
sr status
```

如果 `doctor` 里出现缺失项，先补齐本机依赖、SSH 配置、公钥或端口解析环境，再执行 `sr up`。

### 如果缺少配置，怎么补

#### 1. 没有 SSH 密钥

先在本机生成一对新的 SSH 密钥：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

生成后，默认会得到：

- `~/.ssh/id_ed25519`
- `~/.ssh/id_ed25519.pub`

#### 2. 远端服务器还没有你的公钥

如果远端已经能通过密码登录，可以直接执行：

```bash
ssh-copy-id user@hostname
```

如果没有 `ssh-copy-id`，也可以手动把公钥内容追加到远端的 `~/.ssh/authorized_keys`。

#### 3. 没有 `~/.ssh/config`

可以自己创建一个最小配置，例如：

```sshconfig
Host remote-server
  HostName example.com
  User user
  Port 22
  IdentityFile ~/.ssh/id_ed25519
```

保存后可以先验证：

```bash
ssh remote-server
```

#### 4. 没有 `code` 命令

如果要使用 `sr op` 或 `sync-remote open`，需要让 VS Code 的命令行可用。

常见做法是在 VS Code 里打开命令面板，然后执行：

```text
Shell Command: Install 'code' command in PATH
```

#### 5. 没有 `rsync`

没有 `rsync` 时，工具会自动回退到 `archive` 模式，但 `--sync-path` 这类精细同步能力会受限。

如果当前机器暂时没有 `rsync`，仍然可以这样用：

```bash
sr up --transport archive
```

#### 6. 没有 Cpolar 环境变量文件

如果你要用 `auto` 端口模式，需要准备一个环境变量文件，例如 `~/.env`：

```bash
CPOLAR_USER=你的账号
CPOLAR_PASS=你的密码
```

然后在 `sr init` 时选择 `auto`，并把环境变量文件路径填成 `~/.env`。

如果你没有 Cpolar，或者不想依赖动态端口解析，可以直接在初始化时选择 `fixed` 模式，手动填写 SSH 端口。

## 快速开始

1. 初始化当前目录配置：

```bash
sync-remote init
```

2. 检查本机环境和配置解析结果：

```bash
sync-remote doctor
sync-remote status
```

3. 增量上传当前目录：

```bash
sync-remote upload
```

4. 上传后打开远端目录：

```bash
sync-remote open
```

## 命令一览

| 功能 | 长命令 | 简写 |
| --- | --- | --- |
| 初始化配置 | `sync-remote init` | `sr init` |
| 上传 | `sync-remote upload` | `sr up` |
| 下载 | `sync-remote download` | `sr dl` |
| 备份 | `sync-remote backup` | `sr backup` |
| 打开远端目录 | `sync-remote open` | `sr op` |
| 查看配置状态 | `sync-remote status` | `sr status` |
| 环境自检 | `sync-remote doctor` | `sr doctor` |

更多参数说明可直接查看帮助：

```bash
sync-remote --help
sync-remote upload --help
sync-remote download --help
sync-remote open --help
```

## 配置说明

运行 `sync-remote init` 后，会在当前目录生成 `sync-remote.yaml`。

配置读取顺序：

1. 优先读取 `sync-remote.yaml`
2. 若不存在，则回退读取旧配置 `sync_config.yaml`

端口模式说明：

- `auto`：优先从 Cpolar 获取端口，失败时回退 `~/.ssh/config`
- `fixed`：直接使用配置中的固定端口

远端目录默认由两部分组成：

- `project.remote_base_dir`
- 当前工作目录名

例如当前目录名为 `demo-project`，远端基础目录为 `/srv/projects`，则默认远端目录为：

```text
/srv/projects/demo-project
```

## 配置示例

下面给出两种常见配置示例，方便在新电脑上快速对照填写。

### `auto` 模式示例

适合通过 Cpolar 一类隧道暴露 SSH，公网端口会变化的场景。

对应的 `sync-remote.yaml` 可以长这样：

```yaml
version: 1
project:
  remote_base_dir: /srv/projects
  append_project_dir: true
connection:
  user: user
  host: cpolar-server
  hostname: example.tcp.vip.cpolar.cn
  port_mode: auto
  port: null
  ssh_config_path: ~/.ssh/config
  ssh_key_path: ~/.ssh/id_ed25519
  known_hosts_check: true
cpolar:
  tunnel_name: my-tunnel
  env_path: ~/.env
sync:
  transport: rsync
  max_file_size_mb: 50
backup:
  excludes:
    - .git
```

对应的 Cpolar 环境变量文件例如：

```bash
CPOLAR_USER=你的账号
CPOLAR_PASS=你的密码
```

在这个模式下，端口不是写死在配置里的，而是运行时自动解析。  
例如某次 `status` 里可能会看到解析结果：

```text
SSH HostName: example.tcp.vip.cpolar.cn
端口: 45678
```

### `fixed` 模式示例

适合远端 SSH 端口固定、你已经明确知道 `hostname` 和 `port` 的场景。

```yaml
version: 1
project:
  remote_base_dir: /srv/projects
  append_project_dir: true
connection:
  user: user
  host: remote-server
  hostname: example.com
  port_mode: fixed
  port: 22
  ssh_config_path: ~/.ssh/config
  ssh_key_path: ~/.ssh/id_ed25519
  known_hosts_check: true
cpolar:
  tunnel_name: my-tunnel
  env_path: ~/.env
sync:
  transport: rsync
  max_file_size_mb: 50
backup:
  excludes:
    - .git
```

如果你同时维护 `~/.ssh/config`，可以对应写成：

```sshconfig
Host remote-server
  HostName example.com
  User user
  Port 22
  IdentityFile ~/.ssh/id_ed25519
```

## 典型工作流

### 日常同步

```bash
sr up
```

### 仅预览上传内容

```bash
sr up --dry-run
```

### 下载远端快照

```bash
sr dl
```

### 备份当前目录

```bash
sr backup
```

### 上传后打开远端目录

```bash
sr op
```

## 兼容旧入口

仓库仍保留 `sync_to_remote.py`，但它本身已经不是主要入口。

`sync_to_remote.py` 只是兼容包装层。它会把旧调用方式转发到新的 `sync-remote` CLI，这样以前习惯直接运行脚本的用户不需要立刻改命令。

推荐直接使用新的正式入口：

- `sync-remote`
- `sr`

例如下面这些旧用法仍然可以继续工作：

```bash
python sync_to_remote.py
python sync_to_remote.py upload
```

## 开发与测试

安装开发依赖：

```bash
uv sync --group dev
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
