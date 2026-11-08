# 工具行为固定样本

本目录为输出回放测试保存固定输入与期望值。数据来自提交 `a9eb4d7` 的合成单元夹具，用作[重构计划](../../../docs/superpowers/plans/2026-11-03-tool-architecture-refactor.md)的行为基线；状态令牌统一替换为 `fixture-state`。真实游戏证据见各接口的图形验证记录。

| 文件 | 用途 |
| --- | --- |
| states.json | 各场景的原生响应输入 |
| expected.json | 去重后的固定期望输出 |
| cases.json | MCP 工具的成功、拒绝、预设、筛选、事件、共享提示与占卜媒体用例 |
| cli_cases.json | 文件客户端默认输出、完整状态及预设用例 |

回放使用独立保存的期望值，生产代码只生成待比较的实际输出。改变期望值前核对接口要求并说明差异；经确认的接口变化在[回放测试](../../python/test_tool_contracts.py)中以明确的局部差异处理，新增能力由专项测试覆盖。

差异包括遗物提示的原下标关联、原生静态 summary、close_card_view 的 actions_only、牌堆 opened.summary 省略底部固定 message，以及牌组空原生参数的 null／空对象兼容。各项豁免仅作用于指定字段和用例；自然动画、真实禁用控件与跨房间 GUI 行为另由图形测试验证。
