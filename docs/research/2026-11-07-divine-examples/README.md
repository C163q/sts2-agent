# divine 典型返回

以下十七份为项目f5edfb4、Mod0.77.0及MCP0.79.0下实际MCP stdio返回的完整structuredContent；十六份full、一份default。场景由隔离测试局准备，揭开和奖励均使用原生流程。
多数正常揭开只有上下文、可用操作和空事件transition；具体棋盘由inspect_event或get_observation读取。边缘样本的揭开范围另用前后文字棋盘核对。
诅咒在揭开后立即加入牌组；普通奖励在次数耗尽后展示，领取前没有获得事件。奖励选牌覆盖样本取自领取卡牌奖励后的错误调用。
direct-next样本与前一次揭开之间没有再次观察；after-rejection样本则展示当前缺口：已清除格拒绝后，改选合法格仍被要求观察。

参数、来源行（从0开始）、原始响应路径及SHA-256见[manifest](manifest.json)；范围与未验证事项见[开发核验](../2026-11-07-divine-development-notes.md)。

| 完整JSON | 场景 |
| --- | --- |
| [small.full.json](small.full.json) | 小范围揭开一格 |
| [big-edge.full.json](big-edge.full.json) | 大范围在左边缘裁剪 |
| [small.default.json](small.default.json) | default精简动作回执 |
| [finished.full.json](finished.full.json) | 次数耗尽并完成占卜 |
| [rewards.full.json](rewards.full.json) | 次数耗尽后展示奖励 |
| [curse.full.json](curse.full.json) | 诅咒立即加入永久牌组 |
| [cold-call.full.json](cold-call.full.json) | 未取得许可的首次揭开 |
| [invalid-coordinate.full.json](invalid-coordinate.full.json) | 布尔坐标在MCP本地拒绝 |
| [no-board.full.json](no-board.full.json) | 无占卜棋盘时拒绝 |
| [already-cleared.full.json](already-cleared.full.json) | 已清除格子拒绝 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时拒绝 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖时拒绝 |
| [finished-rejection.full.json](finished-rejection.full.json) | 已结束后拒绝 |
| [rewards-covered.full.json](rewards-covered.full.json) | 奖励覆盖时拒绝 |
| [selection-covered.full.json](selection-covered.full.json) | 奖励选牌覆盖时拒绝 |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后改选合法格仍要求观察 |
| [direct-next.full.json](direct-next.full.json) | 成功揭开后直接再次揭开 |
