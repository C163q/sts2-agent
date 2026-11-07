# respond_to_confirmation 核验与设计建议

> 当前状态：定稿已实现并完成验收、独立审阅及合入main，终态断言缺口已补齐；[实施记录](2026-11-07-confirmation-response-recovery-implementation.md)与[十七份修复后JSON](2026-11-07-confirmation-response-fixed-examples/README.md)另存，下文现状及十二份旧JSON保留审阅基线。总流程见[工具清单](2026-11-02-mcp-tool-review.md)，原问题依据见[开发核验](2026-11-07-respond-to-confirmation-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确拒绝后，合法后续操作仍要求重新观察 | 中：没有受支持确认框时误用，之后合法动作也被阻断；取消后重复响应也有同类问题 | 点击前、画面未改变的明确拒绝保留已有许可 | 已修复并完成验收 |
| 失败原因与下一步不够具体 | 中：没有确认框、非Trial来源的同类弹窗、页面未就绪与按钮不可用，均只显示“操作不可用” | 按当前页面、弹窗支持范围、等待及按钮原因给具体提示 | 已修复；普通场景及禁用按钮已实测，忙碌分支按源码确认 |
| 文档与独立旧验证器仍预期终态空动作列表 | 低：项目已支持结算查看工具，照旧断言验证会误判 | 文档按实际返回同步，迁移旧验证器的断言与运行入口 | 已迁移共享隔离流程并完成验收 |
| 两按钮均不可交互时仍列出响应工具 | 中：仅禁用按钮的测试夹具已复现，基础观察会因工具列表与enabled矛盾而失败；未在自然流程复现 | 列出工具前检查至少一个可交互按钮 | 已修复并经夹具验收 |

前两项属于已有[错误恢复与提示待办](../development/TODO.md#当前工具审阅结束后处理)。MCP本地参数错误已保留许可，缺口在Mod点击前拒绝。

## 当前参数与用途

```json
{"option": "cancel", "preset": "full"}
```

option必填，接受confirm或cancel；preset为default/full，默认default。

工具响应当前单人Trial事件打开的原生“放弃本局”弹窗：confirm点击Yes并放弃当前局，cancel点击No并回到事件。按钮文案可由get_observation的confirmation.options查看。弹窗只需标题、正文及两个选项，无独立详情工具。

选牌确认使用selection_option，结算按钮使用run_result_option。其他来源的同类弹窗目前按未知模态处理。

## 当前成功行为

取消走原生关闭流程，等待遮罩退出后返回action_completed，可直接再次选择Trial选项。取消本身没有资源或物品效果，events为空。

确认走原生RunManager.Abandon，等待放弃任务及整局失败信号，到达run_lost后返回。它会结束当前局，不自动推进结算；后续信息由结算工具读取。

同样文字的新弹窗具有不同状态令牌。玩家或其他调用关闭旧弹窗并重开后，旧观察不能用于响应新弹窗；当前代码已有来源和实例检查。

## 典型场景与完整返回

[十二份完整实际JSON](2026-11-07-respond-to-confirmation-examples/README.md)包括十一份full、一份default。地图／牌组误用等相同错误结构不重复保存，场景覆盖见开发核验。

取消的完整full回执为：

```json
{
  "scene": "event",
  "screen": {"status": "visible"},
  "available_actions": [
    "choose_event_option", "inspect_ui", "inspect_potions", "inspect_relics",
    "inspect_deck", "inspect_map", "inspect_event"
  ],
  "transition": {"stop_reason": "action_completed", "complete": true, "events": []}
}
```

default内容相同。确认放弃的完整full回执为：

```json
{
  "scene": "run_result",
  "screen": {"status": "visible", "view": "run_result"},
  "available_actions": ["inspect_ui", "inspect_run_result", "inspect_potions", "inspect_relics"],
  "transition": {"stop_reason": "run_lost", "complete": true, "events": []}
}
```

此时保留实际可读的查看工具，旧玩法许可不续接。该样本events为空；确认框覆盖时顶栏不可读，私有生命归零数据只用于核验原生放弃，没有加入公开返回。

当前无确认框、取消后重复响应或非Trial来源弹窗的完整错误均为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

之后合法结束回合或重开Trial确认框也会得到observation_required。替换弹窗则正确返回stale_state；读取新弹窗后可以取消。

## 建议范围

保留option枚举、default/full和现有精简动作回执，无需summary或筛选参数。工具提示保留“Trial确认框、confirm放弃本局、cancel返回事件”即可。

先修复两项拒绝问题，并小范围集中确认框页面、动作和按钮检查，让执行、选项enabled及available_actions共用。原生弹窗来源、实例令牌、取消退出等待及确认后的失败边界继续沿用。对应迁移旧验证器，使其适配现有精简回执、事件摘要和终态查看工具，并接入自有实例的验证流程。

明确点击前拒绝可直接纠正或继续合法操作；首次无许可、过期观察、点击后异常、坏响应与未知结果仍要求读取当前状态。这里继续复用现有许可恢复机制。

## 输出定稿

仅响应当前单人Trial事件实际打开的放弃确认框，保留option:confirm|cancel、default/full及精简动作回执。confirm走原生放弃并等待run_lost，cancel走原生关闭并等待返回事件；保留来源绑定、模态实例代次、状态令牌、事件记录及终态查看工具，不新增summary或操作参数。

集中页面、动作与单个按钮的拒绝原因：没有受支持弹窗、未知来源、地图／牌组等覆盖、界面／事件／放弃等待及按钮不可交互。执行、options.enabled及available_actions共用可操作条件，至少一个按钮可交互才列出respond_to_confirmation，Ready保持独立。

当前状态匹配、明确点击前且UI未改变的拒绝保留已有许可，公开原因并返回choose_legal_action，可直接继续合法操作。原始参数拒绝也提供未提交保证；首次无许可、过期、已交互、未知／坏响应及调用被取消时不生成或恢复许可。

迁移verify_confirmation.py的精简回执、事件摘要及终态查看断言，接入共享的自有实例与独立验证启动流程；保留取消、确认、替换及非Trial来源验证。新增仅测试模式／Trial场景可用的按钮状态夹具，验证单按钮拒绝和两按钮不可交互时的工具列表；夹具不进入公开工具目录。旧样本保留，修复后另存实际JSON。
