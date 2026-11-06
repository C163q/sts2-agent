# close_shop 核验与设计建议

> 当前状态：场景核验完成，进入设计讨论；工具行为未修改，未核销。问题与建议如下，详细证据见[开发核验](2026-11-07-close-shop-development-notes.md)。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 点击前拒绝后，合法操作仍被要求观察 | 中：商品页本就关闭时误用close_shop，随后open_shop被要求观察；选牌中误用后，取消也被要求观察 | 明确尚未点击且未改变UI的拒绝保留已有许可，可直接纠正或选择合法动作 | 已实测，待确认后修复 |
| 不同失败只显示“操作不可用” | 中：无法区分没有商店、商品页已关闭、地图／牌组覆盖、等待选牌／奖励或动画未结束 | 返回具体原因和对应工具提示，与可用操作及返回按钮状态共用关闭条件 | 覆盖与关闭等原因已实测，动画分支按源码核对，待修复 |

两项属于已有[错误恢复与诊断待办](../development/TODO.md#当前工具审阅结束后处理)，与open_shop已修复的问题同类。本地参数错误已经能保留已有许可。

## 当前行为与参数

仅接受通用preset:default/full，默认default；没有操作参数。需要已有成功观察提供许可，相关inspect工具也可以提供。

工具点击已展开商品页的原生返回按钮，等待收回动画完成，返回商人画面。普通商人和假商人的公开场景都为shop；后续重新打开使用open_shop，离开房间使用proceed。成功回执已是精简格式：scene、screen、available_actions、transition；单纯关闭没有资源／物品变化时events:[]合理。

地图／牌组覆盖时先关闭对应查看页，删牌或自动购物的选择先处理选择，购买触发的子奖励先处理奖励。领主阳伞自行打开的商品页可以在其流程结束后正常关闭。

## 建议

维持无操作参数、default/full及现有成功回执，无需summary。建议修复两项错误问题，并在现有共用商店页面检查上增加关闭检查，让实际执行、available_actions和返回按钮的enabled共用。

关闭分支可与open_shop一样从购买监听中分开，保留原生按钮、动画等待与场景有效性检查；这是本工具需要的小范围整理，不必提前改造购买流程。首次没有许可、状态过期和点击后的未知结果仍须观察。

工具说明可精简为“Close shop inventory and return to the merchant.”；当前说明已经表达了相同用途，参数和返回不需要进一步扩展。

## 典型JSON与验证范围

[十二份实际完整JSON](2026-11-07-close-shop-examples/README.md)保留十一份full、一份default，包含普通关闭、假商人、删牌／奖励后关闭、阳伞，以及拒绝与随后合法操作被要求观察的示例。普通关闭的full为：

```json
{
  "scene": "shop",
  "screen": {"status": "visible"},
  "available_actions": [
    "open_shop", "proceed", "inspect_ui", "inspect_potions",
    "inspect_relics", "inspect_deck", "inspect_map"
  ],
  "transition": {
    "stop_reason": "action_completed",
    "complete": true,
    "events": []
  }
}
```

其他存档的药水可能使操作列表增加药水相关工具。商品页已关闭时误用close_shop，目前返回：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

随后open_shop得到observation_required，虽然拒绝期间没有UI交互、状态快照也未变化。六类GUI与33项相关Python通过；正常关闭后直接原生读回仅用于核验页面及资源，没有刷新MCP会话许可，后续重新打开／前进确实使用关闭回执续接。

多人、第三方商店、任意人工并发切页、真实超时及中途退出不新增穷举；按钮滑动与动画等待另核对目标源码。具体证据与未验证边界见开发核验。
