# travel_to_node 修复后的典型 JSON

以下为真实 stdio MCP 完整 structuredContent。来源是 Mod 0.69.1、MCP 0.71.1、schema 41，隔离 DLL d43d0d187331cf38918f751d8bd9b7439f8d2e9b3683fd0540c178ceaf6f6671；[实施记录](../2026-11-05-travel-recovery-implementation.md)说明原生流程与验证边界。测试夹具准备局面，旅行由公开工具实际执行。

| 场景 | 完整 JSON |
| --- | --- |
| 赐福鹿角首回合，三张眩晕加入抽牌堆，随后抽牌 | [antler.full.json](antler.full.json) |
| 普通火堆 | [rest.full.json](rest.full.json) |
| 普通战斗 | [combat.full.json](combat.full.json) |
| 飞鞋跳线，显式 default | [flight.default.json](flight.default.json) |
| 地图未打开，保留已有许可 | [map-closed.full.json](map-closed.full.json) |
| 非候选节点，保留已有许可 | [not-selectable.full.json](not-selectable.full.json) |
| 地图被牌组覆盖，提示 close_card_view | [covered.full.json](covered.full.json) |
| 绘图模式，保留已有许可 | [drawing.full.json](drawing.full.json) |
| 已滚动后地图变化，不恢复许可 | [after-scroll.full.json](after-scroll.full.json) |

[manifest.json](manifest.json) 保存原参数、证据下标、图像块计数和文件 SHA-256。九份样本图像块均为 0，JSON 未手工删字段。赐福鹿角的生成去向仅为 draw，不包含随机插入位置或堆内顺序；同一张眩晕随后被抽到时沿用 card.id。

[修复前 10 份审阅样本](../2026-11-05-travel-to-node-examples/README.md)保留原样，不能把其中统一拒绝原因和 get_observation 恢复提示当作修复后行为。
