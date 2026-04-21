# Release Notes Template / 发布说明模板

## Release Checklist

- [ ] `uv run pytest -q` 通过
- [ ] README 与 CLI 帮助一致
- [ ] `status` / `doctor` 仍保持默认只读
- [ ] `port-sync` 的 preview / apply 行为已验证
- [ ] 固定端口与动态端口路径都已覆盖测试
- [ ] 兼容别名仍可用，或已写明弃用路径

## 建议发布摘要

### 中文

- 新增或强化的安全行为
- CLI / 配置结构变化
- 向后兼容说明
- 已知限制与未覆盖范围

### English

- Safety improvements
- CLI or config normalization changes
- Compatibility notes
- Known limits and intentionally deferred scope
