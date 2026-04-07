# sync-remote

把本地项目目录同步到远端 Linux 服务器的命令行工具。它适合已经能用 SSH 登录服务器，但不想每次都手写 `rsync`、`scp`、打包下载和端口更新命令的人。

主命令是 `sync-remote`，简写别名是 `sr`。

## 这工具能做什么

- 在项目目录生成 `sync-remote.yaml`，然后用一条命令上传、下载、打开远端目录、持续同步
- 给同一个项目维护多台服务器，并切换默认目标
- 在真正上传前，先用 `doctor` 和 `status` 看清楚当前会连到哪台机器
- 在任何目录直接更新 `~/.ssh/config` 的端口，适配 Cpolar 动态端口

## 两种使用方式

### 项目内命令

先在项目目录运行 `sr init`，会生成 `sync-remote.yaml`。后续这套命令都围绕当前项目工作：

- `sr init`
- `sr doctor`
- `sr status`
- `sr up`
- `sr dl`
- `sr op`
- `sr watch`
- `sr switch`

### 任意目录命令

`sr port-sync` 不依赖项目 YAML。在任何目录都可以直接读取 `~/.ssh/config` 和 `~/.env`，把命中的 SSH `Port` 更新成当前的 Cpolar 端口。

## 安装

### 推荐安装

```bash
uv tool install git+https://github.com/emmmdty/sync-cli.git
```

安装完成后可直接运行：

```bash
sr --help
sr version
```

### 在仓库里开发或本地调试

```bash
git clone https://github.com/emmmdty/sync-cli.git
cd sync-cli
uv sync --group dev
uv run sr --help
```

## 使用前准备

- `Python 3.10+`
- `uv`
- `ssh`
- 你的 SSH 公钥已经放到远端服务器上，能先手动 `ssh <host>` 登录
- 如果你要自动同步 Cpolar 端口，需要 `~/.env` 中存在 `CPOLAR_USER` 和 `CPOLAR_PASS`
- 如果你要用 `open`，本机需要 VS Code 和 `code` 命令
- 如果你要用 `password` 认证模式，本机需要 `sshpass`
- 如果你想获得更快的增量上传，建议安装 `rsync`

## 5 分钟上手

1. 先确认 SSH 本身能连上：

```bash
ssh gpu-a
```

2. 进入你的项目目录，初始化配置：

```bash
sr init
```

3. 先做环境和配置检查：

```bash
sr doctor
sr status
```

4. 上传当前项目：

```bash
sr up
```

5. 如果你维护多台机器，切换默认服务器后再次上传：

```bash
sr switch gpu-b
sr up
```

## 快速更新 SSH 端口

假设你的 `~/.ssh/config` 中有这一段：

```sshconfig
Host gpu-a
  HostName gpu-a.internal
  User pc3048
  Port 22
```

当 Cpolar 端口变化后，可以在任何目录执行：

```bash
sr port-sync --hostname gpu-a.internal
```

默认会把 SSH 配置块里的 `User` 当成 Cpolar tunnel 名来匹配。

如果你的 SSH `User` 不是 cpolar tunnel 名，请显式传 `--tunnel`：

```bash
sr port-sync --hostname gpu-a.internal --tunnel pc3048
```

如果 cpolar 中存在多个同名 tunnel，工具会继续按 hostname 精确匹配，不会误取第一条。

## 常用命令

| 场景 | 命令 |
| --- | --- |
| 初始化当前项目配置 | `sr init` |
| 查看当前项目配置和端口解析结果 | `sr status` |
| 做环境排查 | `sr doctor` |
| 上传当前项目到默认服务器 | `sr up` |
| 下载远端目录压缩包 | `sr dl` |
| 上传后用 VS Code 打开远端目录 | `sr op` |
| 持续监听本地改动并同步 | `sr watch` |
| 切换默认服务器 | `sr switch <host>` |
| 上传到所有已配置服务器 | `sr upload-all-gpu` |
| 备份当前目录 | `sr backup` |
| 在任何目录更新 SSH 端口 | `sr port-sync --hostname gpu-a.internal` |
| 查看当前版本 | `sr version` |
| 更新到最新 Release | `sr update --channel release` |

## 下一步看哪里

- [完整使用手册](docs/usage.md)
- [MIT License](LICENSE)

## 更新

```bash
sr version
sr update --channel release
```

如果你当前不是通过 `uv tool install` 安装，也可以手动更新：

```bash
uv tool install --upgrade git+https://github.com/emmmdty/sync-cli.git@v0.5.0
```
