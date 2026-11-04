# 药水预设与筛选的真实返回

对应[实施记录](../2026-11-04-potion-inspection-implementation.md)。以下为隔离游戏经真实 stdio MCP 返回的完整 structuredContent，仅格式化 JSON，未手工改写字段。不可悬停条件由测试夹具关闭入口，不表示自然游玩复现。

- [full](combat.full.json)、[summary](combat.summary.json)：满栏，两个格挡药水共享解释。
- [筛选第三槽](filtered.full.json)：结果映射与 Block 提示都保持原槽位 2。
- [不可悬停 full](unhoverable-filtered.full.json)、[default](unhoverable-filtered.default.json)：保留名称，正文 null／省略；note 引用原槽位。
- [只选空槽](empty-slot.full.json)：空槽与映射保留，hover_tips 为 []，没有其他槽位的 Block 解释。

版本、Mod DLL SHA-256、原始调用参数与证据位置见[清单](manifest.json)。
