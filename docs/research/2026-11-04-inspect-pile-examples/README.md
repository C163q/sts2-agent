# inspect_pile 核验示例

核验基线与问题见[专项审阅](../2026-11-04-inspect-pile-review.md)。每份 JSON 为完整公开对象；调用参数、证据类型、原始文件／条目和校验值见 [manifest](manifest.json)。

`real_stdio` 是实际 MCP structuredContent；`native_projected` 是原生测试夹具返回经当前公开解码／full 投影，不代表自然游玩或真实 stdio 请求；`constructed` 是明确标识的实现整理。没有将 default 请求冒充 full 调用。

| 示例 | 场景 | 证据类型 |
| --- | --- | --- |
| [draw.full.json](draw.full.json) | 非空draw；full | real_stdio |
| [draw.default.json](draw.default.json) | 非空draw；default | real_stdio |
| [draw.summary.json](draw.summary.json) | 非空draw；summary | real_stdio |
| [discard.full.json](discard.full.json) | 非空discard；full | real_stdio |
| [discard.default.json](discard.default.json) | 非空discard；default | real_stdio |
| [discard.summary.json](discard.summary.json) | 非空discard；summary | real_stdio |
| [exhaust.full.json](exhaust.full.json) | 非空exhaust；full | real_stdio |
| [exhaust.default.json](exhaust.default.json) | 非空exhaust；default | real_stdio |
| [exhaust.summary.json](exhaust.summary.json) | 非空exhaust；summary | real_stdio |
| [empty-draw.full.json](empty-draw.full.json) | 实际点击空抽牌入口和气泡 | real_stdio |
| [empty-discard.full.json](empty-discard.full.json) | 实际点击空弃牌入口和气泡 | real_stdio |
| [hidden-keeps-deck.full.json](hidden-keeps-deck.full.json) | 隐藏目标保留已有牌组页 | real_stdio |
| [error-filter.json](error-filter.json) | card_ids 目前不受支持，本地拒绝 | real_stdio |
| [error-map.json](error-map.json) | 地图挡住入口时拒绝 | real_stdio |
| [observation-discard.full.json](observation-discard.full.json) | 牌堆已打开，基础观察尚无列表 | real_stdio |
| [observation-exhaust.full.json](observation-exhaust.full.json) | 消耗页已打开，基础观察尚无列表 | real_stdio |
| [hidden-exhaust.full.json](hidden-exhaust.full.json) | 隐藏入口；full | real_stdio |
| [observation-draw.full.json](observation-draw.full.json) | 已打开抽牌页的基础观察；full | real_stdio |
| [hidden-exhaust.default.json](hidden-exhaust.default.json) | 隐藏入口；default | real_stdio |
| [observation-draw.default.json](observation-draw.default.json) | 已打开抽牌页的基础观察；default | real_stdio |
| [hidden-exhaust.summary.json](hidden-exhaust.summary.json) | 隐藏入口；summary | real_stdio |
| [observation-draw.summary.json](observation-draw.summary.json) | 已打开抽牌页的基础观察；summary | real_stdio |
| [draw-replaces-deck.full.json](draw-replaces-deck.full.json) | 非空抽牌页替换牌组 | real_stdio |
| [empty-closes-draw.full.json](empty-closes-draw.full.json) | 空弃牌关闭已有抽牌页 | real_stdio |
| [error-main-menu.json](error-main-menu.json) | 主菜单拒绝 | real_stdio |
| [error-event.json](error-event.json) | 非战斗事件拒绝 | real_stdio |
| [error-selection.json](error-selection.json) | 显示选牌时拒绝 | real_stdio |
| [error-after-rejection.json](error-after-rejection.json) | 明确前置拒绝后，旧许可丢失 | real_stdio |
| [closed.full.json](closed.full.json) | 成功关闭是 actions_only | real_stdio |
| [constructed-disabled.full.json](constructed-disabled.full.json) | 实现整理的禁用入口，非自然实测 | constructed |
| [long-draw.full.json](long-draw.full.json) | 原生测试夹具生成的长列表及上下文费用，由当前公开 full 投影 | native_projected |

抽牌页列表是原生显示顺序，不能据此预测抽取顺序。基础观察样本仍缺牌堆列表，正是待补缺口；closed 样本则已采用 actions_only，不能用旧验证脚本的完整观察断言判断其错误。
