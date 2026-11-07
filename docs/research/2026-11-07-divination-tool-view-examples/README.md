# 占卜工具视图切换实际返回

以下十三份为隔离游戏的实际MCP stdio完整structuredContent，十二份full、一份default。棋盘由原生事件流程打开；冷切换样本在该MCP会话创建前已由测试准备打开棋盘，第一次公开调用就是set_divination_tool。
工具切换返回actions_only格式；揭开和proceed仍返回transition。重复工具保持快照不变，明确拒绝后的合法操作可直接继续，中间直接原生检查不刷新MCP许可。

调用参数、来源行（从0开始）及SHA-256见[manifest](manifest.json)；验证范围见[实施记录](../2026-11-07-divination-tool-view-implementation.md)。

| 完整JSON | 场景 |
| --- | --- |
| [cold-switch.full.json](cold-switch.full.json) | 无先前MCP观察直接切换 |
| [same-tool.full.json](same-tool.full.json) | 重复当前工具，快照不变 |
| [switch-big.default.json](switch-big.default.json) | 切回大范围，default |
| [direct-reveal.full.json](direct-reveal.full.json) | 冷切换后直接揭开，保留动作回执 |
| [cold-unavailable.full.json](cold-unavailable.full.json) | 首次无棋盘拒绝不生成许可 |
| [no-board.full.json](no-board.full.json) | 已有许可的无棋盘拒绝 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时提示close_map |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖时提示close_card_view |
| [finished.full.json](finished.full.json) | 结束后提示proceed |
| [rewards-covered.full.json](rewards-covered.full.json) | 奖励覆盖时提示inspect_rewards |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖时提示inspect_selection |
| [proceed-after-rejection.full.json](proceed-after-rejection.full.json) | 拒绝后直接proceed |
| [selection-after-rejection.full.json](selection-after-rejection.full.json) | 拒绝后直接跳过奖励选牌 |
