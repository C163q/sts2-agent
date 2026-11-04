# 关闭错误恢复的实际返回

全部为真实 stdio MCP 完整 structuredContent；参数、来源条目及校验值见 [manifest](manifest.json)。实现、验证和未覆盖范围见[实施记录](../2026-11-04-close-card-view-implementation.md)。旧审阅样例保留原基线，不在这里改写。

| 示例 | 内容 |
| --- | --- |
| [no-view-rejected.json](no-view-rejected.json) | 没有浏览页：具体原因与 choose_legal_action |
| [turn-after-rejection.full.json](turn-after-rejection.full.json) | 拒绝后不额外观察，直接结束回合成功 |
| [closed.full.json](closed.full.json) | full 的成功最小返回 |
| [repeat-rejected.json](repeat-rejected.json) | 连续关闭第二次仍拒绝，但保留已有许可 |
| [closed.default.json](closed.default.json) | default 的成功最小返回 |
| [map-rejected.json](map-rejected.json) | 仅地图时不误关闭地图 |
| [map.full.json](map.full.json) | 关闭牌组后保留底下地图 |
| [selection-rejected.json](selection-rejected.json) | 当前为选择页：具体原因且保留许可 |
| [selection-continued.full.json](selection-continued.full.json) | 无额外观察，直接选择按钮成功 |
| [battlefield.full.json](battlefield.full.json) | 关闭牌堆返回选择战场视图 |
| [selection-view.full.json](selection-view.full.json) | 成功关闭后直接回到选择 |
