# 遗物图标状态与筛选实测

对应[实施记录](../2026-11-04-relic-inspection-implementation.md)，保存 13 份完整真实 stdio MCP 返回，不裁剪字段。实际参数、证据条目、源文件与结果 SHA-256、采样版本见 [manifest.json](manifest.json)。

- 普通图标：[full](normal.full.json)、[default](normal.default.json)、[summary](normal.summary.json)。full 明确保留两个 false，另两者省略。
- 激活发光且筛选原位置 3：[full](pulsing.filtered.full.json)、[default](pulsing.filtered.default.json)、[summary](pulsing.filtered.summary.json)。顶层 relic_indices 保留原位置，false 置灰标记在精简结果中省略。
- [置灰 default](grayed.filtered.default.json)、[无 shader 的 full](unknown-shader.filtered.full.json)、[无法悬停及筛选 note](hover-unavailable.filtered.full.json)。以上边界由测试夹具注入，真实读取该图标后返回，不代表自然游玩异常。
- [有效与越界混合](partial.filtered.summary.json)、[空筛选](empty.filtered.full.json)：映射与结果一一对应，越界合并。
- [隐藏遗物栏拒绝](error.hidden-inventory.json)：注入隐藏条件，返回具体错误并保留原动作许可；随后直接行动的完整证据见实施记录。
- [自然熔化后 full](wax-after.full.json)：通过原生出牌流程熔化，melted 与 grayed_out 独立表达。
