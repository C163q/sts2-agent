# open_shop 核验与设计建议

> 当前状态：场景核验完成，进入设计讨论；工具行为尚未修改，未核销。问题与建议如下，开发证据见[开发核验](2026-11-07-open-shop-development-notes.md)。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 点击前拒绝后，合法操作仍被要求重新观察 | 中：商品页已打开时误用open_shop，随后close_shop被要求观察；删牌选择中误用后，取消也被要求观察 | 明确尚未点击且未改变UI的拒绝保留已有许可，可直接选择合法动作 | 已实测，待确认后修复 |
| 不同失败只显示“操作不可用” | 中：无法区分无商店、已经打开、地图／牌组覆盖或等待选牌；LLM缺少下一步依据 | 返回具体原因及对应工具提示，并与available_actions共用打开条件 | 已实测，待确认后修复 |

两项均属于已有[错误恢复与诊断待办](../development/TODO.md#当前工具审阅结束后处理)。参数在MCP本地校验失败时已经能保留已有许可。正常打开及重新打开未发现重复购买、资源变化或返回仍处于展开动画的问题。

## 当前参数和返回

只接受通用preset:default/full，默认default；没有操作参数。需要已有成功观察提供的许可，相关inspect工具也能提供。成功返回scene、screen、available_actions和transition，已经与actions_only加动作反馈的格式一致。

普通商人和假商人沿用各自原生点击流程，公开场景都为shop。成功等待商品页展开后返回action_completed，下一次立即观察可读库存。单纯打开没有资源／物品变化，因此events:[]合理。商品和价格由inspect_shop或get_observation读取。

领主阳伞会自行打开商品页并购买；自动购物进入删牌选择时，应先完成选择。完成后关闭商品页，再次open_shop使用普通打开流程。

## 典型JSON

[完整返回及来源](2026-11-07-open-shop-examples/README.md)保留实际full和default结果。成功的最小示例为：

```json
{
  "scene": "shop",
  "screen": {"status": "visible"},
  "available_actions": [
    "buy_item", "close_shop", "inspect_ui", "inspect_potions",
    "inspect_relics", "inspect_deck", "inspect_map", "inspect_shop"
  ],
  "transition": {
    "stop_reason": "action_completed",
    "complete": true,
    "events": []
  }
}
```

这是普通商店的实际完整full返回；其他存档的药水可能使available_actions增加药水相关工具。

当前已经打开时，再调用返回：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

其后close_shop得到observation_required；这就是第一项待修复问题。

## 建议定稿范围

维持零操作参数及default/full，回执已足够精简，无需summary或自动读取商品参数。建议只修复上述两项，并小范围整理商店动作条件：在共用商店页面检查基础上，单独提供打开条件及具体原因，让执行与available_actions复用。

打开、关闭、购买目前共用一个动作函数，但本轮只需整理打开分支；购买监听、扣费与补货流程留在各自工具核验时处理。已点击后的异常、过期状态和超时继续要求观察；不能把点击前的安全恢复扩大到这些情况。

未新增多人、第三方商店、任意人工并发切页、真实超时以及动画中途调用的GUI测试；动画等待与状态变化分支另核对源码。详细验证范围及数量见开发核验。
