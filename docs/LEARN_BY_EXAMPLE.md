# sync-remote 案例式教程

这份文档按“我今天要完成什么”来教你，而不是按内部模块来讲解。

建议先在一个普通项目目录里跟着做一遍，再把它用到真实项目。

## 它是什么，不是什么

用户目标：先理解产品边界，避免带着错误预期开始使用。

精确命令：

```bash
sr --help
```

预期结果：

- 你会看到这是一个 SSH-first 远程开发同步 CLI
- 你会看到它围绕 `init`、`upload`、`open`、`watch`、`target`、`config`、`port-sync` 工作
- 你不会看到它宣称自己是通用双向同步平台

常见错误：

- 把它当成默认双向同步工具
- 期待 `watch` 自动删除远端多余文件
- 期待它替你处理复杂冲突合并

深入阅读：

- `README.md`
- `docs/TROUBLESHOOTING.md`

## 前置准备与安装

用户目标：确保本机具备能跑通主流程的最小依赖。

精确命令：

```bash
uv tool install .
sr version
```

预期结果：

- `uv tool install .` 安装 `sync-remote` 和 `sr`
- `sr version` 输出当前安装版本号

常见错误：

- 没装 `uv`
- 用 `uv run` 验证时误以为已经全局安装
- 之后要用 `open`、`watch`、`password` 模式，却没有提前准备 `code`、`rsync`、`sshpass`

深入阅读：

- `README.md` 的“安装”和“首次使用前准备”

## 第一次初始化

用户目标：在项目目录生成第一份项目级配置。

精确命令：

```bash
sr init
```

预期结果：

- 当前目录会生成或更新 `sync-remote.yaml`
- 如果已有 `~/.ssh/config` 中的 Host，可在初始化时复用
- 如果当前目录已有配置，再跑一次会追加新目标，并把新目标设为默认

常见错误：

- 在错误目录里初始化，结果把配置写进了不该管理的目录
- 还没准备 SSH key / SSH Host 就直接开始
- 把初始化理解成“全局配置”；实际上它是项目级配置

深入阅读：

- `sr init --help`
- `README.md` 的“配置说明”

## 检查环境 / doctor

用户目标：在真正连接前先检查本机依赖和关键文件状态。

精确命令：

```bash
sr doctor
sr doctor --json
```

预期结果：

- 文本输出会告诉你 `ssh`、`rsync`、`code`、`sshpass`、配置文件、SSH key、SSH alias、端口解析状态
- JSON 输出适合脚本或 CI
- 默认不会改写项目配置，也不会改写 SSH config

常见错误：

- 看到 `sshpass: MISSING` 就以为一定坏了；只有 password 认证才需要它
- 把 `doctor` 当成修复命令；它默认只是诊断
- 没看建议字段就直接重试

深入阅读：

- `sr doctor --help`
- `docs/TROUBLESHOOTING.md`

## 理解目标服务器

用户目标：知道“目标服务器”在这个工具里是什么意思。

精确命令：

```bash
sr target list
sr target list --json
sr config explain
```

预期结果：

- `target list` 会显示当前默认目标和全部目标列表
- `config explain` 会告诉你当前配置文件来源、当前版本、规范化写回版本、默认目标和目标列表

常见错误：

- 把目标服务器理解成全局机器列表；它实际上是“当前项目里的目标集合”
- 只看 `README` 不看 `config explain`
- 修改默认目标后忘了重新确认

深入阅读：

- `sr target list --help`
- `sr config explain --help`

## 切换目标服务器

用户目标：把当前项目的默认目标切到另一台机器。

精确命令：

```bash
sr target use gpu-b
```

预期结果：

- 默认目标切换到 `gpu-b`
- 后续不显式指定目标时，`up`、`open`、`watch`、`status`、`doctor` 都会使用它

常见错误：

- 还在用 `sr switch gpu-b`，但没意识到它是兼容命令
- 切换后没有再跑 `sr status`
- 误以为切换会修改其他目标配置

深入阅读：

- `sr target use --help`
- 兼容入口：`sr switch --help`

## 固定端口目标

用户目标：理解固定端口目标的最简单工作流。

精确命令：

```bash
sr status
```

预期结果：

- 当目标是固定端口模式时，输出会直接显示配置中的固定端口
- 不需要 `port-sync`

常见错误：

- 固定端口目标也去跑 `port-sync --apply`
- SSH Host、HostName、端口三者关系没理清

深入阅读：

- `README.md` 的“端口模式”
- `sr status --help`

## 动态端口目标

用户目标：安全地处理动态端口，而不是让诊断命令偷偷写配置。

精确命令：

```bash
sr port-sync --json
sr port-sync --apply --write-ssh-config
```

预期结果：

- 第一个命令只预览：告诉你解析出的端口，以及项目配置/SSH config 是否会变化
- 第二个命令才真正写回项目配置；加上 `--write-ssh-config` 时，才会同步更新 SSH config

常见错误：

- 把 `status` / `doctor` 当成端口同步命令
- 忘了先 preview 就直接 apply
- 不想改 SSH config 却多加了 `--write-ssh-config`

深入阅读：

- `sr port-sync --help`
- `sr target port-sync --help`
- `docs/MIGRATION.md`

## 推送同步

用户目标：把当前项目推到默认目标，或一次推多个目标。

精确命令：

```bash
sr up
sr up --dry-run
sr up --hosts gpu-a gpu-b
sr up --all-targets
```

预期结果：

- `sr up` 推到当前默认目标
- `--dry-run` 只预览
- `--hosts` 指定一个或多个目标
- `--all-targets` 是规范写法；兼容命令是 `sr upload-all-gpu`

常见错误：

- 期待默认删除远端多余文件
- 在没装 `rsync` 时使用 `--sync-path`
- 不知道 `upload-all-gpu` 是兼容命令，还把它写进新文档

深入阅读：

- `sr upload --help`
- 兼容入口：`sr upload-all-gpu --help`

## 持续监听

用户目标：本地文件改动后自动继续推送。

精确命令：

```bash
sr watch
sr wt --sync-path src
sr wt --debounce-ms 1500
```

预期结果：

- 启动时先执行一次上传
- 然后进入监听计划，显示监听后端、监听范围和停止方式
- `--sync-path` 可以把监听范围收窄到项目内指定路径

常见错误：

- 用 Windows 原始绝对路径，例如 `C:\repo\src`
- 以为删除本地文件会自动删除远端文件
- 监听失败后没看控制台输出就直接重试

深入阅读：

- `sr watch --help`
- `docs/TROUBLESHOOTING.md`

## 打开远端项目

用户目标：先上传，再直接用 VS Code Remote SSH 打开远端目录。

精确命令：

```bash
sr op
sr op --watch
sr op --dry-run
```

预期结果：

- `sr op` 会先跑上传，再调用本机 `code` 打开远端目录
- `--watch` 会在打开后继续监听
- `--dry-run` 只预览上传，不会打开 VS Code

常见错误：

- 没安装 `code` 命令
- SSH alias 不可用却直接执行 `open`
- 想只打开而不先上传；这个工具不会跳过那一步

深入阅读：

- `sr open --help`

## 配置检查、解释与迁移

用户目标：知道什么时候该 validate、explain、migrate。

精确命令：

```bash
sr config validate
sr config explain
sr config migrate --json
sr config migrate --apply
```

预期结果：

- `validate` 检查能不能读
- `explain` 解释 CLI 看到的当前配置
- `migrate --json` 先预览规范化结果
- `migrate --apply` 才真正写回为当前规范版本

常见错误：

- 直接 `--apply`，没先看 preview
- 把 `validate` 当成修复命令
- 迁移后没重新跑 `sr status`

深入阅读：

- `sr config validate --help`
- `sr config explain --help`
- `sr config migrate --help`
- `docs/MIGRATION.md`

## 常见故障排查

用户目标：遇到最常见问题时，先按固定顺序排查。

精确命令：

```bash
sr doctor
sr status
sr port-sync --json
```

预期结果：

- 你能先确认依赖、配置、SSH alias、端口解析，再决定是不是要 apply 端口

常见错误：

- 一上来就怀疑远端机器坏了
- 不看 `doctor` / `status` 的建议字段
- 动态端口还没预览就直接改 SSH config

深入阅读：

- `docs/TROUBLESHOOTING.md`

## 兼容命令与何时不要用

用户目标：知道哪些命令还在，哪些命令不该写进新手路径。

精确命令：

```bash
sr switch gpu-b
sr del gpu-b
sr upload-all-gpu
python sync_to_remote.py --help
```

预期结果：

- 这些入口仍然能用
- 但新文档、新培训、新脚本应优先使用 `target use`、`target remove`、`upload --all-targets`、`sync-remote` / `sr`

常见错误：

- 在新教程里继续推广旧命令
- 看到兼容入口还能用，就以为它仍是规范路径

深入阅读：

- `README.md` 的“兼容旧入口”
- 各命令 `--help`

## 日常工作流

用户目标：给自己一个稳定、可重复的每日操作顺序。

精确命令：

```bash
sr status
sr up
sr op
sr wt --sync-path src
```

预期结果：

- 先确认目标和端口
- 再推送
- 需要远端编辑时用 `open`
- 需要持续同步时再进入 `watch`

常见错误：

- 跳过 `status`
- 默认目标已经变了却没发现
- 在不需要持续监听时也一直挂着 `watch`

深入阅读：

- `README.md`
- 本文前面的对应案例

## 安全恢复

用户目标：出问题时，先做安全检查，而不是直接把锅甩给工具。

精确命令：

```bash
sr status
sr doctor
sr config explain
sr port-sync --json
```

预期结果：

- 你能确认当前默认目标、远端目录、SSH alias、端口解析、配置来源
- 如果只是动态端口变了，你会先看到 preview，再决定要不要 apply

常见错误：

- 没搞清楚自己当前在哪个项目目录
- 没确认默认目标就上传
- 动态端口环境变量文件缺失，却反复重试上传

深入阅读：

- `docs/TROUBLESHOOTING.md`
- `docs/MIGRATION.md`
