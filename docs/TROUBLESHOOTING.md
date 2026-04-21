# Troubleshooting / 故障排查

## 故障排查

### 1. `doctor` 显示 `sshpass: MISSING`

- 仅当目标使用 `password` 认证时才需要 `sshpass`
- 如果你不希望安装 `sshpass`，可在初始化或配置调整后切回 `key` 模式

### 2. `status` 或 `doctor` 显示端口未解析

- 先运行 `sr port-sync --json` 预览端口解析结果
- 确认结果正确后，再运行 `sr port-sync --apply`
- 只有在你明确希望更新 SSH config 时，才追加 `--write-ssh-config`

### 3. 在 WSL 中使用了 Windows 风格绝对路径

- `sync-path` 建议使用项目相对路径，例如 `src/app.py`
- 如果必须引用 Windows 盘符，请改用 `/mnt/c/...` 形式
- `C:\...` 这类路径不会被静默转换，以避免误同步到项目外

### 4. `watch` 没有删除远端多余文件

- 这是当前产品边界的一部分，不做默认双向同步或删除传播
- 在 `rsync` 增量监听模式下，纯删除事件只会提示，不会自动删除远端文件

## English Notes

- Use `sr doctor --json` when you need machine-readable diagnostics.
- If port resolution fails, preview with `sr port-sync --json` before applying anything.
- On WSL, prefer repo-relative paths or `/mnt/<drive>/...` paths instead of raw `C:\...` inputs.
- `watch` is intentionally conservative and does not claim full bidirectional sync semantics.
