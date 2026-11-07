# 对话推进修复后的实际返回

Mod0.78.2、MCP0.80.2、schema46；24份实际MCP structuredContent，23份full、1份default，均未裁剪。调用参数、证据行及SHA-256见[manifest.json](manifest.json)。

[输出定稿](../2026-11-07-advance-dialogue-review.md#输出定稿)；[实施与验证](../2026-11-07-dialogue-recovery-implementation.md)。

| 文件 | 场景 |
| --- | --- |
| [ancient-first.full.json](ancient-first.full.json) | 先古推进到下一句 |
| [ancient-to-gifts.full.json](ancient-to-gifts.full.json) | 先古推进到馈赠 |
| [ancient.default.json](ancient.default.json) | 实际default推进 |
| [no-dialogue.full.json](no-dialogue.full.json) | 错误房间的具体原因 |
| [direct-end-turn.full.json](direct-end-turn.full.json) | 拒绝后直接结束回合 |
| [gifts-ready.full.json](gifts-ready.full.json) | 当前应选择馈赠 |
| [direct-gift.full.json](direct-gift.full.json) | 拒绝后直接选择馈赠 |
| [gift-finished.full.json](gift-finished.full.json) | 已领取，应前进 |
| [direct-proceed.full.json](direct-proceed.full.json) | 拒绝后直接前进 |
| [map-covered.full.json](map-covered.full.json) | 提示关闭地图 |
| [direct-close-map.full.json](direct-close-map.full.json) | 直接关闭地图 |
| [deck-covered.full.json](deck-covered.full.json) | 提示关闭牌组 |
| [selection-covered.full.json](selection-covered.full.json) | 提示处理当前选择 |
| [direct-preview.full.json](direct-preview.full.json) | 拒绝后直接预览卡牌包 |
| [rewards-covered.full.json](rewards-covered.full.json) | 提示处理当前奖励 |
| [direct-reward-proceed.full.json](direct-reward-proceed.full.json) | 拒绝后直接处理奖励 |
| [stale.full.json](stale.full.json) | 外部推进后拒绝旧观察 |
| [after-stale.full.json](after-stale.full.json) | 过期拒绝不恢复许可 |
| [architect-map-covered.full.json](architect-map-covered.full.json) | 建筑师地图覆盖 |
| [architect-deck-covered.full.json](architect-deck-covered.full.json) | 建筑师牌组覆盖 |
| [architect-advance.full.json](architect-advance.full.json) | 建筑师推进到最终按钮 |
| [architect-final.full.json](architect-final.full.json) | 建筑师最终按钮提示proceed |
| [architect-direct-proceed.full.json](architect-direct-proceed.full.json) | 拒绝后直接原生前进并run_won |
| [terminal-no-permission.full.json](terminal-no-permission.full.json) | 胜利后不续接玩法许可 |
