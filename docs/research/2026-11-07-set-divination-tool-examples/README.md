# set_divination_tool 典型返回

以下十二份为提交bd493fc下新启动的隔离游戏实测，经实际MCP stdio获得的完整structuredContent；十一份full、一份default。场景由测试夹具准备，切换和揭开均使用原生流程。
切换为小范围、重复选择和切回大范围的实际成功回执相同；当前结果不附带整个棋盘，也不显示当前tool字段。
冷调用样本来自事件初始页面中的新会话；after-rejection样本是随后调用proceed的实际错误。

调用参数、来源行（从0开始）、原始响应路径和SHA-256见[manifest](manifest.json)；验证范围见[开发核验](../2026-11-07-set-divination-tool-development-notes.md)。

| 完整JSON | 场景 |
| --- | --- |
| [switch-small.full.json](switch-small.full.json) | 切换为小范围 |
| [same-tool.full.json](same-tool.full.json) | 重复选择当前工具 |
| [switch-big.default.json](switch-big.default.json) | 切换为大范围，default回执 |
| [cold-call.full.json](cold-call.full.json) | 该MCP会话尚未观察 |
| [no-board.full.json](no-board.full.json) | 无占卜棋盘时拒绝 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时拒绝 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖时拒绝 |
| [finished.full.json](finished.full.json) | 占卜结束后拒绝 |
| [rewards-covered.full.json](rewards-covered.full.json) | 奖励页面覆盖时拒绝 |
| [selection-covered.full.json](selection-covered.full.json) | 奖励选牌覆盖时拒绝 |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后合法proceed仍要求观察 |
| [invalid-tool.full.json](invalid-tool.full.json) | 非法tool在MCP本地拒绝 |
