# 独立复用顶栏摘要

> 当前状态：本轮实现与验证已完成。共用顶栏已接入所有场景，定向 18 项及 Python 全套 461 项通过；页面主体与顶栏摘要已分离，无本任务遗留。

## 范围与依据

基线为 0b47a68，MCP 从 0.50.1 更新为 0.50.2；Mod 0.49.1 和 schema 31 不变。本轮修正摘要分工，不涉及游戏 API、原生读取或动作许可。

原浏览占位直接返回整份 default，且非战斗页面在顶栏压缩前提前返回，导致同一个顶栏随底层场景和覆盖页改变摘要格式。现将四字段摘要抽至 [top_bar_summary.py](../../src/sts2_mcp/output/top_bar_summary.py)，由 [observation_summary](../../src/sts2_mcp/output/observation_presets.py) 在场景分派前统一调用；浏览占位只保留页面主体的 default 内容。

所有 summary 的顶栏遵守同一契约，规则统一维护在[观察预设](../development/observation.md#mcp-输出预设)。default、full、actions_only 和 top_bar 预设保持原有行为。隐藏顶栏和未知遗物数量不补齐，0 和药水空槽保留。非战斗正文、选择预览的未知值和占卜图片不受顶栏精简影响。

## 验证与边界

- 新增跨场景／页面及隐藏顶栏、未知数量检查，调整浏览和非战斗摘要断言；先在旧实现中复现失败，再使用共用处理通过。
- 复用前轮游戏 v0.107.1 的 full 样本验证输出，涵盖原浏览样本及顶栏修复后的地图、牌组、三类牌堆、事件和换幕。未重新运行 GUI 或原生构建，不把纯投影验证称为新的游戏实测。
- 相应 GUI 验证器已更新为分别检查页面主体与共用顶栏，供后续游戏回归使用。
- 定向 18 项通过；Python 全套 461 项通过（35.147 秒）。验证了共用白名单、隐藏／未知值边界、占卜图片及其他预设不变；游戏 full 输入与新输出各自保持原对象不变。文档、JSON 和 diff 校验通过。日志位于 `.tmp/2026-11-02-shared-top-bar-summary/`；原占位范围问题见[本地报告](../../.tmp/2026-11-02-shared-top-bar-summary-report.md)。

本轮只需重连 MCP，无须更换 Mod。

## 当前投影示例

以先前真实 MCP 的[战斗地图 full](2026-11-02-top-bar-visibility-examples/combat-map.full.json)为输入，经本轮代码生成完整的 [default](2026-11-02-top-bar-visibility-examples/combat-map.default.json) 和 [summary](2026-11-02-top-bar-visibility-examples/combat-map.summary.json)。两个输出仅顶栏字段范围不同；它们是当前投影结果，不是新执行的 GUI 请求。
