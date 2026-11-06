# inspect_event 当前返回结构样例

这两份为**历史游戏数据经当前读取器重放**的完整 full JSON，不是当前版本新采集的游戏结果。当前代码基线为 b1afbaa。

- [普通事件](event.full.json)：主体来自 .tmp/2026-10-31-divination/event-basic.json 第 1 行索引的 inspect_event.result。
- [占卜](divination.full.json)：主体来自 .tmp/2026-10-31-divination/full-run1.json 第 2 行索引的 inspect_event.result。原调用另有 PNG 内容块；此目录只记录 JSON，原图片位于该证据目录的 full-run1/02-inspect_event.png。

行索引从 0 开始。重放为原主体补入最近一次在前结果的 screen，以及当前 schema_version:44，调用当前 decode_success("inspect_event", state)；schema_version 不对外返回。原事件正文、选项、占卜棋盘等主体沿用原值，没有补入新的碎片数据。manifest.json 记录来源及输出 SHA-256。

用途是核对当前工具的返回字段与 null 位置；不代表当前版本重新完成游戏、截图传输或全部场景验收。设计与核验边界见[审阅](../2026-11-07-inspect-event-review.md)。
