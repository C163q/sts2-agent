# 开箱拒绝恢复的完整返回

19份真实stdio MCP完整structuredContent，均无图片。除loot_treasure结果，也保留拒绝后直接继续、旅行、领取奖励、选牌及结束回合的回执。实现及验证范围见[实施记录](../2026-11-06-treasure-loot-recovery-implementation.md)。

禁用、离屏和延迟效果由既有隔离测试设施注入，不作为自然复现。原[17份审阅样本](../2026-11-06-loot-treasure-examples/README.md)保留修复前行为。每份的实际工具、参数、来源与SHA-256见[manifest.json](manifest.json)。

| 完整 JSON | 场景 | 工具 |
| --- | --- | --- |
| [default-complete.full.json](default-complete.full.json) | 正常默认开箱与领取 | `loot_treasure` |
| [open-only.full.json](open-only.full.json) | 只开箱，金币事件 | `loot_treasure` |
| [already-open.full.json](already-open.full.json) | 已开箱的具体原因及可保留许可 | `loot_treasure` |
| [direct-take.default.json](direct-take.default.json) | 拒绝后直接领取，default | `loot_treasure` |
| [empty-chest.full.json](empty-chest.full.json) | 空箱正常完成，events为空 | `loot_treasure` |
| [empty-or-collected.full.json](empty-or-collected.full.json) | 当前无可领取遗物 | `loot_treasure` |
| [direct-proceed.full.json](direct-proceed.full.json) | 拒绝后直接继续 | `proceed` |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖的具体原因 | `loot_treasure` |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖的具体原因 | `loot_treasure` |
| [direct-travel.full.json](direct-travel.full.json) | 地图覆盖拒绝后直接旅行 | `travel_to_node` |
| [extra-rewards.full.json](extra-rewards.full.json) | 额外奖励中断，保持原生边界 | `loot_treasure` |
| [direct-claim.full.json](direct-claim.full.json) | 覆盖拒绝后直接领取奖励 | `claim_reward` |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖的具体原因 | `loot_treasure` |
| [direct-select.full.json](direct-select.full.json) | 覆盖拒绝后直接选择卡牌 | `select_card` |
| [disabled.full.json](disabled.full.json) | 人工禁用遗物的具体原因 | `loot_treasure` |
| [offscreen.full.json](offscreen.full.json) | 人工离屏图标保留读取，拒绝点击 | `loot_treasure` |
| [wrong-scene.full.json](wrong-scene.full.json) | 无宝箱房的具体原因 | `loot_treasure` |
| [direct-end-turn.full.json](direct-end-turn.full.json) | 无宝箱拒绝后直接结束回合 | `end_turn` |
| [map-after-obtain.full.json](map-after-obtain.full.json) | 等待人工延迟遗物效果完成后返回 | `loot_treasure` |
