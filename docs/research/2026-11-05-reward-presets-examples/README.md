# 奖励预设与筛选的真实返回

以下是 Mod 0.70.0、MCP 0.72.0、schema 41 的真实 stdio MCP 完整 structuredContent。测试 DLL 为 d9475a7e92e93bd2fbb0941167475fb6ad900ffdeece7d23d9d66db9f040a6fd，来源及验证边界见[实施记录](../2026-11-05-reward-inspection-presets-implementation.md)。

| 场景 | JSON |
| --- | --- |
| 奖励 full，保留普通 null 和悬停说明 | [basic.full.json](basic.full.json) |
| 相同页面 summary，静态奖励行 | [basic.summary.json](basic.summary.json) |
| full 按 ID 筛选，保留选中行的悬停说明及缺失 ID 错误 | [filtered.full.json](filtered.full.json) |
| summary 按相同 ID 筛选 | [filtered.summary.json](filtered.summary.json) |
| [] 筛选，保留整页标题和前进按钮 | [empty-filter.summary.json](empty-filter.summary.json) |
| 互斥奖励 summary，保留组身份 | [linked.summary.json](linked.summary.json) |
| 原生空奖励页 summary | [empty.summary.json](empty.summary.json) |
| get_observation.full，奖励部分为静态行并保留 null | [observation.full.json](observation.full.json) |
| get_observation.summary，奖励部分与 basic.summary 一致 | [observation.summary.json](observation.summary.json) |
| 牌组覆盖时的 summary／[] 请求，返回具体拒绝及 choose_legal_action | [deck-covered.summary.json](deck-covered.summary.json) |
| 无奖励列表且无已有许可时的具体拒绝 | [no-rewards.full.json](no-rewards.full.json) |

[manifest.json](manifest.json) 保存实际调用参数、原始文件与数组下标、图像块计数和 SHA-256；11 份样本图像块均为 0。[原审阅样本](../2026-11-05-inspect-rewards-examples/README.md)作为修复前基线保留。截图、领取后续和其他覆盖验证的证据保存在实施记录所列目录。
