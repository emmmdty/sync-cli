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
