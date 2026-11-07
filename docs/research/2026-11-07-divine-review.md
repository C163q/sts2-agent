# divine 核验与设计建议

> 当前状态：定稿已实现并完成验收，待独立审阅及合入；[实施记录](2026-11-07-divination-recovery-implementation.md)与[十八份修复后JSON](2026-11-07-divination-recovery-examples/README.md)另存，下文现状与十七份旧JSON保留审阅基线。总流程见[工具清单](2026-11-02-mcp-tool-review.md)，源码与原问题依据见[开发核验](2026-11-07-divine-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 点击前明确拒绝后，合法操作仍要求重新观察 | 中：重复揭开已清除的格子后，改选覆盖格也被阻止；无棋盘、页面覆盖或结束时误用也影响合法后续动作 | 画面未改变、明确未点击的拒绝保留已有许可 | 已修复并完成验收 |
| 不同失败只显示统一的“操作不可用” | 中：无法判断是格子已经清除、页面被覆盖、动画未结束，还是占卜已经结束 | 区分页面、结算和目标格原因，给对应操作提示 | 已修复并完成验收 |

两项属于已有[错误恢复与提示待办](../development/TODO.md#当前工具审阅结束后处理)。MCP本地参数错误已保留已有许可，缺口在Mod点击前的明确拒绝。

## 当前参数与用途

```json
{"x": 5, "y": 5, "preset": "full"}
```

x、y必填，均为0–10的整数；左上角为(0,0)，x向右、y向下。目标必须是当前文字棋盘中的覆盖格`#`。按当前选中的工具揭开：big以目标为中心揭开按棋盘边界裁剪的3×3，small揭开一格；两者均消耗一次次数。使用set_divination_tool切换范围。

preset支持default/full，默认default。成功返回上下文、可用操作及transition；更新后的次数、图案和碎片按需用inspect_event或get_observation查看。回执不附图。

## 原生结算

完整揭开金币、药水、卡牌或遗物图案后，要等次数耗尽才展示奖励，领取后才真正获得；图案成为`S`并不表示已经获得奖励。诅咒例外：完整揭开后立即将Doubt加入牌组，相应card_added进入该次回执。

次数归零后，调用等待原生奖励或后续可交互边界。奖励页出现时使用inspect_rewards、claim_reward或proceed继续；奖励选牌使用inspect_selection等工具。占卜彻底结束后使用proceed。

## 典型场景与完整返回

[十七份实际JSON](2026-11-07-divine-examples/README.md)包含十六份full、一份default；参数与来源逐份记录。

| 场景 | 实测结果 |
| --- | --- |
| small正常揭开、big中央或边缘揭开 | 消耗一次；按当前范围清除覆盖，action_completed；没有物品取得时events为空 |
| 成功后直接再次揭开 | 无需重新观察即可继续；新棋盘仍可按需查看 |
| 次数耗尽且没有待领奖励 | action_completed，当前可用操作改为proceed等 |
| 次数耗尽后展示奖励 | scene为rewards，action_completed；领取前没有金币或遗物获得事件 |
| 完整揭开诅咒 | 立即记录card_added、pile:deck；实测为Doubt |
| 误点已清除格、无棋盘、覆盖页或已结束 | 通用illegal_action，随后合法动作仍要求观察；对应前述两项问题 |

正常揭开一格的完整full回执为：

```json
{
  "scene": "event",
  "screen": {"status": "visible", "view": "divination"},
  "available_actions": [
    "set_divination_tool", "divine", "inspect_ui", "inspect_potions",
    "inspect_relics", "inspect_deck", "inspect_map", "inspect_event"
  ],
  "transition": {"stop_reason": "action_completed", "complete": true, "events": []}
}
```

该回执中没有普通null字段，default与full内容相同。events为空表示此次没有已接入的资源或物品变化；次数与棋盘不在当前事件类型中，使用观察读取。

诅咒样本的events为以下内容，完整上下文见[实际返回](2026-11-07-divine-examples/curse.full.json)：

```json
[
  {"card": {"id": 3, "name": "Doubt"}, "pile": "deck", "type": "card_added", "sequence": 1}
]
```

当前误点已清除格的完整错误为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

同样的错误也用于无棋盘、覆盖页与结束后的调用；它无法指明正确的恢复操作。

## 建议范围

维持坐标、default/full及现有精简动作回执；无需新增summary或筛选参数。一次调用揭开一次，新的图案和资源变化可供下一次决策。

修复前述两项时，复用已有占卜页面检查，并集中提供揭开操作和目标格的拒绝原因：无棋盘、地图／牌组／奖励／选牌覆盖、结算等待、已结束，以及目标已清除或不可交互。available_actions与执行共用可操作条件。

重构限于占卜揭开检查与动作分支，沿用现有动作拒绝恢复机制。过期观察、点击后异常和未知结果仍要求重新读取；原生扣次数、文字棋盘、图案识别及奖励流程保持现有职责。

工具提示可简述为“使用当前占卜工具揭开一个覆盖格，消耗一次次数；可能停在奖励或选择界面”。坐标方向和范围由参数说明承担。

## 输出定稿

保留必填整数坐标x/y（0–10）、当前big/small范围、default/full及现有精简动作回执，不新增summary、筛选或操作参数。成功记录真实可见的资源／物品变化，次数和新棋盘按需观察；没有新图片需求。

复用占卜页面检查，集中判断揭开可用性和目标格原因；available_actions与执行共用条件。无棋盘、地图／牌组／奖励／选牌覆盖、结算等待、占卜结束、已清除或不可交互格分别给出具体原因及对应工具提示。就绪检查保持独立，静态棋盘与图案读取保持原有职责。

当前快照匹配、点击前且UI未改变的明确拒绝保留已有许可，返回choose_legal_action，允许直接继续合法操作；原始参数拒绝也提供未提交保证。首次无许可、过期快照、点击后异常、坏响应、取消及未知结果不生成或恢复许可。

重构限于揭开检查和对应动作分支，沿用原生按钮、扣次数、奖励、事件记录与停止边界。旧JSON保留，修复后另存实际结果，验证连续揭开和拒绝后的合法后续操作。
