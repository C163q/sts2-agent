# divine 修复后典型返回

以下十八份均来自最终DLL的实际MCP stdio返回，十七份full、一份default；基线与验证范围见[实施记录](../2026-11-07-divination-recovery-implementation.md)。
明确拒绝提供具体原因及choose_legal_action，后续揭开、结束回合、领奖、跳过或前进均直接调用。公共JSON不包含内部执行证明或隐藏奖励位置。
claim-after-rejection样本取自先直接丢弃药水腾出槽位、再领取药水奖励的实际回执；奖励页展示仍不生成取得事件。旧审阅样本另存保留。

调用参数、来源行（从0开始）、原始响应路径及SHA-256见[manifest](manifest.json)。

| 完整JSON | 场景 |
| --- | --- |
| [reveal.full.json](reveal.full.json) | 正常小范围揭开 |
| [reveal.default.json](reveal.default.json) | default揭开回执 |
| [already-cleared.full.json](already-cleared.full.json) | 已清除格具体拒绝，保留许可 |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后直接揭开合法格 |
| [no-board.full.json](no-board.full.json) | 无棋盘具体拒绝 |
| [end-turn-after-rejection.full.json](end-turn-after-rejection.full.json) | 无棋盘拒绝后直接结束回合 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时提示close_map |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖时提示close_card_view |
| [finished.full.json](finished.full.json) | 占卜已结束时提示proceed |
| [proceed-after-rejection.full.json](proceed-after-rejection.full.json) | 已结束拒绝后直接前进 |
| [rewards-covered.full.json](rewards-covered.full.json) | 奖励覆盖时提示inspect_rewards |
| [claim-after-rejection.full.json](claim-after-rejection.full.json) | 拒绝后腾出药水槽并领取奖励 |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖时提示inspect_selection |
| [selection-after-rejection.full.json](selection-after-rejection.full.json) | 拒绝后直接跳过卡牌奖励 |
| [curse.full.json](curse.full.json) | 诅咒立即加入永久牌组 |
| [direct-next.full.json](direct-next.full.json) | 成功后无观察地连续揭开 |
| [rewards.full.json](rewards.full.json) | 次数归零后展示奖励，无取得事件 |
| [finished-reveal.full.json](finished-reveal.full.json) | 次数归零并完成占卜 |
