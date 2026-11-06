# open_shop 核验与设计建议

> 当前状态：已按定稿实现并通过约定验收，等待独立审阅及合入；以下现状与样本保留审阅基线，最终要求见输出定稿。开发证据见[开发核验](2026-11-07-open-shop-development-notes.md)。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。修复实现及当前验收见[实施记录](2026-11-07-shop-opening-recovery-implementation.md)，[十五份修复后JSON](2026-11-07-shop-opening-fixed-examples/README.md)另存；下文现状及旧样本保留修复前基线。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 点击前拒绝后，合法操作仍被要求重新观察 | 中：商品页已打开时误用open_shop，随后close_shop被要求观察；删牌选择中误用后，取消也被要求观察 | 明确尚未点击且未改变UI的拒绝保留已有许可，可直接选择合法动作 | 已修复并通过验收 |
| 不同失败只显示“操作不可用” | 中：无法区分无商店、已经打开、地图／牌组覆盖或等待选牌；LLM缺少下一步依据 | 返回具体原因及对应工具提示，并与available_actions共用打开条件 | 已修复并通过验收 |

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

## 输出定稿

维持无操作参数、default/full及现有精简成功回执；不新增summary。成功仍使用原生商人点击，等待就绪并返回transition；商品由后续观察读取。

打开检查与available_actions共用OpenUnavailableReason。与详情共用页面覆盖判断，区分无商店、非单人、地图打开／收回、牌组、选牌、奖励、其他覆盖、过渡和库存动画；打开分支另区分已经打开、药水瞄准、交易／遗物任务、卡牌／资源动画、动作队列、输入阻挡和不可用商人。

相同快照下，明确点击前拒绝提供未提交证明，公开具体原因，保留已有许可并返回recovery:choose_legal_action。没有许可时仍须先成功观察；过期状态和点击后失败不续接许可。原始接口传入多余参数也使用明确未提交拒绝；MCP本地参数错误继续保留许可。

小范围重构限于共用页面检查和打开分支，将打开与购买监听分开；关闭、购买的行为和恢复语义留待其各自审阅。验证原有五类场景，并回归普通购买、送货员和删牌流程。旧样本保持不变，修复后样本另存。
