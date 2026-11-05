# claim_reward 修复后完整返回

真实 stdio MCP 的完整 structuredContent，共 18 份，17 份 full、1 份 default，图片数均为零。原生测试扰动只用于 scroll-failed，说明见[实施记录](../2026-11-05-claim-reward-recovery-implementation.md)。[原 15 份样本](../2026-11-05-claim-reward-examples/README.md)保留修复前行为。

除领取回执，还保留拒绝后直接执行跳过、旅行、结束回合的回执，便于核对无需额外观察。每份的实际工具、调用参数、来源与 SHA-256 见 [manifest.json](manifest.json)。

| 完整 JSON | 场景 | 工具 |
| --- | --- | --- |
| [gold.default.json](gold.default.json) | 金币领取，default | `claim_reward` |
| [direct-potion.full.json](direct-potion.full.json) | 重复领取被拒绝后直接取得药水 | `claim_reward` |
| [relic.full.json](relic.full.json) | 取得遗物并永久升级卡牌 | `claim_reward` |
| [card-choice.full.json](card-choice.full.json) | 打开卡牌选择，pending/choice_required | `claim_reward` |
| [full-belt.full.json](full-belt.full.json) | 药水满槽仍返回 not_claimed | `claim_reward` |
| [nested-rewards.full.json](nested-rewards.full.json) | 嵌套奖励保持 pending/action_completed | `claim_reward` |
| [unknown-id.full.json](unknown-id.full.json) | 奖励 ID 无效，保留许可并提示当前入口 | `claim_reward` |
| [already-claimed.full.json](already-claimed.full.json) | 奖励已消失，保留许可 | `claim_reward` |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖，提示 close_map 并保留许可 | `claim_reward` |
| [direct-travel.full.json](direct-travel.full.json) | 拒绝后直接原生旅行 | `travel_to_node` |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖，提示 inspect_selection | `claim_reward` |
| [direct-skip.full.json](direct-skip.full.json) | 拒绝后直接跳过卡牌奖励 | `selection_option` |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖，提示 close_card_view | `claim_reward` |
| [wrong-scene.full.json](wrong-scene.full.json) | 无奖励页的固定原因 | `claim_reward` |
| [direct-end-turn.full.json](direct-end-turn.full.json) | 无奖励页拒绝后直接结束回合 | `end_turn` |
| [scroll-choice.full.json](scroll-choice.full.json) | 成功滚动后打开画面外卡牌奖励 | `claim_reward` |
| [scroll-failed.full.json](scroll-failed.full.json) | 人为制造滚动后失败，要求观察 | `claim_reward` |
| [after-scroll-failed.full.json](after-scroll-failed.full.json) | 滚动后失败，已有许可已清除 | `claim_reward` |
