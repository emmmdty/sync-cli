# sync-remote 使用手册

这份文档按“先跑起来，再理解细节”的顺序写，适合第一次接触这个工具的人。

## 1. 安装

推荐直接安装 GitHub 上的版本：

```bash
uv tool install git+https://github.com/emmmdty/sync-cli.git
```

安装后先确认命令可用：

```bash
sr --help
sr version
```

如果你是在仓库里开发：

```bash
uv sync --group dev
uv run sr --help
```

## 2. 最快上手

最常见的使用方式，是在项目目录里生成一份 `sync-remote.yaml`，之后都围绕这份配置同步。

### 第一步：先确认 SSH 本身没问题

先手动试一次 SSH：

```bash
ssh gpu-a
```

如果这一步不通，先别急着跑 `sync-remote`。先把 `~/.ssh/config`、密钥和网络连通性处理好。

### 第二步：进入项目目录并初始化

```bash
cd /path/to/your-project
sr init
```

`init` 会做这些事：

- 在当前目录生成或更新 `sync-remote.yaml`
- 优先读取你本机的 `~/.ssh/config`
- 如果当前目录已经有配置，会把新服务器追加进去，并把它设成默认服务器

### 第三步：先检查，再上传

```bash
sr doctor
sr status
sr up
```

推荐理解成这样：

- `doctor` 看你的本机环境是否够用
- `status` 看这次实际会连哪台机器、用哪个端口、远端目录是什么
- `up` 才是真正上传

### 第四步：切换到另一台服务器

```bash
sr switch gpu-b
sr up
```

如果一个项目要同步到多台机器，这就是最常用的日常流程。

## 3. 项目内命令

下面这些命令都依赖当前目录里的 `sync-remote.yaml`。

### `sr init`

初始化或追加服务器配置。

常见用法：

```bash
sr init
```

### `sr doctor`

检查本机依赖和 SSH 相关文件是否就绪。首次配置失败时，优先跑这个命令。

```bash
sr doctor
```

### `sr status`

显示当前默认服务器、生效配置、SSH 文件状态、远端目录和端口解析结果。

```bash
sr status
```

### `sr up`

上传当前项目到默认服务器。

```bash
sr up
```

常见变体：

```bash
sr up --dry-run
sr up --hosts gpu-a gpu-b
sr up --sync-path src README.md
```

### `sr dl`

把远端目录打包后下载到当前目录，不会自动解压。

```bash
sr dl
sr dl --output ./remote-snapshot.tar.gz
```

### `sr op`

先上传，再通过 VS Code Remote SSH 打开远端目录。

```bash
sr op
sr op --watch
```

### `sr watch`

先传一次，再持续监听本地改动并自动同步。

```bash
sr watch
sr wt --debounce-ms 1500
```

### `sr upload-all-gpu`

把当前目录并发上传到配置里的所有服务器。某一台失败，不会阻塞其他服务器继续执行。

```bash
sr upload-all-gpu
```

### `sr backup`

把当前目录打成一个备份压缩包。

```bash
sr backup
sr backup --output ../my-project-backup.tar.gz
```

### `sr switch` 和 `sr del`

切换默认服务器或删除当前项目中的某个服务器配置。

```bash
sr switch gpu-b
sr del gpu-b
```

## 4. 任意目录更新 SSH 端口

`sr port-sync` 是这次版本里最适合单独用的一条命令。它不看当前项目目录，也不会读取或生成 `sync-remote.yaml`。

它只做这件事：

- 读取 `~/.ssh/config`
- 读取 `~/.env` 中的 `CPOLAR_USER` 和 `CPOLAR_PASS`
- 登录 cpolar
- 找到匹配的 tunnel
- 把命中的 SSH 配置块里的 `Port` 改成最新端口

### 默认匹配规则

1. 先按 SSH 配置块的 `HostName` 命中目标
2. 如果你没有显式传 `--tunnel`，默认把该 SSH 配置块的 `User` 当成 tunnel 名
3. 如果同一个 tunnel 名在 cpolar 中出现多次，会继续按 hostname 精确匹配

这一步很重要：如果 cpolar 里有多个同名 tunnel，工具不会再像旧版本那样误取第一条，而是按 hostname 找对应端口。

### 最常见的命令

```bash
sr port-sync
sr port-sync --hostname gpu-a.internal
sr port-sync --hostname gpu-a.internal --user alice
sr port-sync --hostname gpu-a.internal --tunnel pc3048
```

### 什么时候要显式传 `--tunnel`

如果你的 SSH `User` 不是 cpolar tunnel 名，请显式传 `--tunnel`。

例如：

```sshconfig
Host gpu-a
  HostName gpu-a.internal
  User root
  Port 22
```

但你在 cpolar 里的 tunnel 名其实叫 `pc3048`，那就应该这样写：

```bash
sr port-sync --hostname gpu-a.internal --tunnel pc3048
```

### `~/.env` 示例

```dotenv
CPOLAR_USER=your-cpolar-account
CPOLAR_PASS=your-cpolar-password
```

## 5. `sync-remote.yaml` 示例

下面是一份简化后的多服务器示例：

```yaml
version: 2
project:
  remote_base_dir: /srv/gpu-b
  append_project_dir: true
default_host: gpu-b
servers:
  gpu-a:
    remote_base_dir: /srv/gpu-a
    append_project_dir: true
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
    remote_base_dir: /srv/gpu-b
    append_project_dir: true
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
      tunnel_name: pc3048
      env_path: ~/.env
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

读这份配置时，可以只抓住三点：

- `default_host` 决定 `sr up`、`sr dl`、`sr op`、`sr watch` 默认作用于谁
- `servers.<host>` 存的是每台机器自己的 SSH 和目录信息
- `port_mode: auto` 表示优先去 Cpolar 取端口，`fixed` 表示直接使用写死的端口

## 6. 常见场景

### 场景 1：只同步一台固定端口服务器

这时最简单。初始化一次，之后日常用：

```bash
sr status
sr up
```

### 场景 2：同一个项目要同步到多台服务器

```bash
sr switch gpu-a
sr up
sr switch gpu-b
sr up
```

如果你就是要同时发到所有机器：

```bash
sr upload-all-gpu
```

### 场景 3：远端端口经常变，靠 Cpolar 暴露 SSH

优先用：

```bash
sr port-sync --hostname gpu-a.internal
```

如果你已经在项目配置里把端口模式设成 `auto`，项目内命令也会优先从 Cpolar 解析端口。

## 7. 排错

### `sr doctor` 先跑一遍

出现问题时，先执行：

```bash
sr doctor
sr status
```

这两条命令能帮你快速确认：

- SSH 配置文件是否存在
- 私钥和公钥是否存在
- SSH alias 是否存在
- cpolar 环境文件和凭证是否存在
- 当前项目到底会使用哪个端口

### `ssh <host>` 本身都不通

这不是 `sync-remote` 的问题，先处理这些基础项：

- `~/.ssh/config` 是否写对
- 远端机器是否在线
- 公钥是否已经放到远端
- 本机网络是否能访问目标地址

### `port-sync` 提示缺少凭证

检查 `~/.env` 是否存在，并确认里面至少有：

```dotenv
CPOLAR_USER=...
CPOLAR_PASS=...
```

### `port-sync` 没找到正确端口

优先检查这三件事：

- `--hostname` 是否和 SSH 配置块里的 `HostName` 一致
- tunnel 名是不是应该显式传 `--tunnel`
- cpolar 页面里是不是存在多个同名 tunnel

如果存在多个同名 tunnel，当前版本会按 hostname 精确匹配；如果 hostname 也对不上，工具会直接报未命中，而不是乱改端口。

## 8. 更新

推荐通过 release 通道更新：

```bash
sr version
sr update --channel release
```

如果你当前不是通过 `uv tool install` 安装，也可以手动升级：

```bash
uv tool install --upgrade git+https://github.com/emmmdty/sync-cli.git@v0.5.0
```
