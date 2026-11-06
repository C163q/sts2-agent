# 事件详情与占卜文字观察实测样例

本目录为 Mod 0.76.0、MCP 0.78.0、schema 45 的 17 份完整返回和 4 张同次附图。来源为 .tmp/2026-11-07-event-inspection-text/gui-final/，manifest.json 记录实际调用、结果行索引、来源类别及 SHA-256。行索引从 0 开始；JSON 直接取对应 MCP 结果，没有补写或重算字段。

| 场景 | 样例 |
| --- | --- |
| 普通事件完整详情／摘要 | [full](event.full.json)、[summary](event.summary.json) |
| 基础观察共用静态摘要 | [full](observation-event.full.json)、[summary](observation-event.summary.json) |
| 明确拒绝 | [无事件](no-event.error.json)、[地图覆盖](event-map-covered.error.json) |
| 静态展示与悬停分离 | [离屏](event-offscreen.full.json)、[不可悬停](event-no-hover.full.json) |
| 占卜初始文字观察 | [get_observation.full](board-initial-observation.full.json) |
| 占卜可选图片 | [JSON](board-with-image.full.json)、[同次 PNG](board-with-image.full.png) |
| PNG 不可用仍能读文字 | [full](board-text-png-unavailable.full.json) |
| 原生单格揭开瓶底 | [full](board-potion-base.full.json) |
| 自然结算结束 | [summary](board-finished.summary.json) |
| 完整图案与同次附图 | [箱子](board-whole-box.full.json)、[卡牌](board-whole-card.full.json)、[诅咒](board-whole-curse.full.json)；对应 .png 文件同名 |
| 下半张牌不附隐藏稀有度 | [full](board-visible-card-lower-left.full.json) |

普通事件离屏／悬停样例使用可恢复的 UI 显示夹具；完整箱子／卡牌／诅咒及单独下半张牌使用可恢复的遮罩夹具。夹具改变图案展示，不执行原生奖励获取。瓶底单格、真实奖励结算和前进来自正常 divine 等原生操作。媒体失败样例只启用私有 PNG 失败夹具。

更多逐格、三个横幅及不同缩放的结果保留在证据目录；本目录只选择典型返回。[实现及验证范围](../2026-11-07-event-inspection-text-implementation.md)另行说明。
