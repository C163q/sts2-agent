# 牌堆筛选与基础观察的实际示例

全部为真实 stdio MCP 的完整 structuredContent，调用参数、来源与校验值见 [manifest](manifest.json)。实现及验证范围见[实施记录](../2026-11-04-pile-inspection-implementation.md)。

| 示例 | 内容 |
| --- | --- |
| [observation.full.json](observation.full.json) | 已打开抽牌页的基础观察：full |
| [inspect.full.json](inspect.full.json) | 抽牌详情：full |
| [filtered.full.json](filtered.full.json) | 筛选、重复及缺失 ID：full |
| [observation.default.json](observation.default.json) | 已打开抽牌页的基础观察：default |
| [filtered.default.json](filtered.default.json) | 筛选、重复及缺失 ID：default |
| [observation.summary.json](observation.summary.json) | 已打开抽牌页的基础观察：summary |
| [filtered.summary.json](filtered.summary.json) | 筛选、重复及缺失 ID：summary |
| [empty-filter.summary.json](empty-filter.summary.json) | 只裁剪输出，页面仍为 opened |
| [discard.full.json](discard.full.json) | 非空discard：full |
| [discard.summary.json](discard.summary.json) | 非空discard：summary |
| [exhaust.full.json](exhaust.full.json) | 非空exhaust：full |
| [exhaust.summary.json](exhaust.summary.json) | 非空exhaust：summary |
| [empty-pile.summary.json](empty-pile.summary.json) | 空堆保留原生反馈，并报告缺失 ID |
| [unavailable.summary.json](unavailable.summary.json) | 隐藏消耗入口：保留原因，不假报成员缺失 |
| [closed.full.json](closed.full.json) | 成功关闭返回 actions_only |
| [selection-rejected.json](selection-rejected.json) | 具体前置拒绝且保留旧许可 |
| [selection-continued.full.json](selection-continued.full.json) | 无额外观察直接操作成功 |
| [battlefield-observation.full.json](battlefield-observation.full.json) | 待处理选择被牌堆覆盖，静态列表及选择上下文并存 |
| [battlefield-repeat.full.json](battlefield-repeat.full.json) | 下层按钮隐藏，当前页仍可重复查看 |
