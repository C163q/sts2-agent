# close_card_view 完整返回示例

核验结论见[专项记录](../2026-11-04-close-card-view-review.md)，实际参数、来源条目和校验值见 [manifest](manifest.json)。

每份 JSON 都是完整真实 MCP structuredContent；19 份为专项新采样，消耗堆关闭复用相同 Mod／MCP 与相同 DLL 的牌堆实测，不冒充新采样。成功 default/full 均为已定稿的 actions_only；名称带 full 表示实际 preset，未人为补 null。

| 示例 | 内容 | 证据类型 |
| --- | --- | --- |
| [deck.full.json](deck.full.json) | 关闭牌组后返回战斗：full | real_stdio |
| [deck.default.json](deck.default.json) | 关闭牌组后返回战斗：default | real_stdio |
| [draw.full.json](draw.full.json) | 关闭抽牌堆 | real_stdio |
| [discard.full.json](discard.full.json) | 关闭弃牌堆 | real_stdio |
| [map.full.json](map.full.json) | 牌组关闭后保留底下地图 | real_stdio |
| [battlefield.full.json](battlefield.full.json) | 返回待处理选择的战场视图 | real_stdio |
| [event.full.json](event.full.json) | 返回事件背景 | real_stdio |
| [error-main-menu.json](error-main-menu.json) | 主菜单没有浏览页 | real_stdio |
| [error-no-view.json](error-no-view.json) | 可操作战斗中没有浏览页 | real_stdio |
| [error-repeat.json](error-repeat.json) | 连续关闭第二次拒绝 | real_stdio |
| [error-map-only.json](error-map-only.json) | 单独地图不能由此工具关闭 | real_stdio |
| [error-selection.json](error-selection.json) | 直接显示的选牌不能关闭 | real_stdio |
| [error-summary.json](error-summary.json) | 不支持 summary，本地拒绝 | real_stdio |
| [error-unknown-field.json](error-unknown-field.json) | 额外参数在 IPC 前拒绝 | real_stdio |
| [error-next-turn.json](error-next-turn.json) | 无页面拒绝后已有许可丢失 | real_stdio |
| [error-next-selection.json](error-next-selection.json) | 选牌覆盖拒绝后已有许可丢失 | real_stdio |
| [direct-play.full.json](direct-play.full.json) | 成功关闭后无需再观察直接出牌 | real_stdio |
| [direct-selection-view.full.json](direct-selection-view.full.json) | 成功关闭后直接返回选择 | real_stdio |
| [continued-selection.full.json](continued-selection.full.json) | 重新观察后同一选项恢复可用 | real_stdio |
| [exhaust.full.json](exhaust.full.json) | 关闭消耗堆，同一版本／同一 DLL 的既有真实返回 | reused_stdio |
