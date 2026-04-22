# Migration / 迁移说明

如果你是第一次使用，而不是在迁移旧配置，先看场景式教程：

- 中文教程：[LEARN_BY_EXAMPLE.md](LEARN_BY_EXAMPLE.md)
- English tutorial: [LEARN_BY_EXAMPLE.en.md](LEARN_BY_EXAMPLE.en.md)

## 迁移目标

本仓库已经把新的规范写回格式统一到 `version: 3`，核心变化是：

- `default_host` -> `default_target`
- `servers` -> `targets`
- 每个目标拆分为 `project`、`ssh`、`port`
- 动态端口改为显式 `provider` 模型

## 推荐迁移步骤

1. 先检查当前配置是否可读取：

```bash
sr config validate
```

2. 查看当前配置是如何被解释的：

```bash
sr config explain
```

3. 预览规范化后的结果：

```bash
sr config migrate --json
```

4. 确认后写回：

```bash
sr config migrate --apply
```

5. 如需显式刷新动态端口，再运行：

```bash
sr port-sync --json
sr port-sync --apply --write-ssh-config
```

## Compatibility

- `switch` 仍兼容，但推荐改用 `target use`
- `del` 仍兼容，但推荐改用 `target remove`
- `upload-all-gpu` 仍兼容，但推荐改用 `upload --all-targets`

## Migration

The v3 config format keeps the product narrow: project-scoped SSH sync, fixed or provider-resolved ports, and explicit write actions only.

If you are onboarding from scratch instead of migrating an older config, start with:

- Chinese tutorial: [LEARN_BY_EXAMPLE.md](LEARN_BY_EXAMPLE.md)
- English tutorial: [LEARN_BY_EXAMPLE.en.md](LEARN_BY_EXAMPLE.en.md)

Recommended order:

1. `sr config validate`
2. `sr config explain`
3. `sr config migrate --json`
4. `sr config migrate --apply`
5. `sr port-sync --json` and only then `sr port-sync --apply --write-ssh-config` if you explicitly want that side effect
