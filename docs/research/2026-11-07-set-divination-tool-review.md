# set_divination_tool 核验与设计建议

> 当前状态：定稿已实现并完成验收、独立审阅及合入main；[实施记录](2026-11-07-divination-tool-view-implementation.md)及[十三份实际JSON](2026-11-07-divination-tool-view-examples/README.md)另存，下文现状及旧样本保留审阅基线。总流程见[工具清单](2026-11-02-mcp-tool-review.md)，源码与验证依据见[开发核验](2026-11-07-set-divination-tool-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确拒绝后，合法后续操作仍要求重新观察 | 中：无棋盘、页面覆盖或占卜结束时误用，之后结束回合、领取奖励、继续选牌或proceed也被阻断 | 点击前、画面未改变的明确拒绝保留已有许可，允许直接继续当前合法操作 | 已修复并完成验收 |
| 不同失败只显示统一的“操作不可用” | 中：无法判断应关闭地图／牌组、处理奖励／选牌、等待结算，还是占卜已经结束 | 区分页面、忙碌及工具按钮原因，给出对应操作提示；显示与执行复用检查 | 已修复并完成验收 |

两项属于已有[错误恢复与提示待办](../development/TODO.md#当前工具审阅结束后处理)。本地参数错误已保留已有许可，缺口在请求到达Mod后的明确拒绝。

## 审阅时的行为与参数

```json
{"tool": "small", "preset": "full"}
```

`tool`必填，仅接受big或small。big为按棋盘边界裁剪的3×3范围，small为一格。preset支持default/full，默认default。当前没有summary。

切换只改变选中的工具及按钮高亮；次数、已揭开的格子和资源保持不变。重复选择当前工具同样成功。实际揭开由divine完成。

审阅时调用需要已有观察许可；成功返回上下文、可用操作及transition，刷新许可后可以直接继续切换或揭开。完整棋盘和当前选中工具按需通过inspect_event或get_observation查看，切换回执不附图。

## 修复前典型JSON

[十二份完整实际返回](2026-11-07-set-divination-tool-examples/README.md)覆盖正常、重复、default、冷调用、覆盖、结束和错误后的后续操作；调用参数及来源逐份记录。

切换为small的当前完整full回执为：

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

切回big和重复选择的成功结构相同。这里events为空合理：切换没有产生资源或物品变化。当前这些回执没有普通null字段，default与full内容相同。

当前无棋盘、被覆盖或已经结束时，错误均为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

随后合法操作仍得到observation_required。已结束时本应能够直接proceed，却也会受这次误用影响。

## 统一为视图切换的依据

原生切换仅改变工具与高亮。项目已将其标为view，但仍要求先观察、记录动作并返回transition；set_selection_view等视图工具则可以直接检查当前页面，成功返回actions_only格式。这是现有接口差异，当前文档也明确记录了该例外。

建议与其他视图工具统一：

- 在当前可交互棋盘上可直接切换，无需为了取得许可先读一次观察。
- 成功返回get_observation.actions_only格式，省去transition；重复选择当前工具仍成功。
- 明确未交互的拒绝给具体原因并保留已有许可；首次拒绝不生成许可。
- 保持tool枚举及default/full，无需新增参数或summary。

定稿的成功格式示例如下，实际返回另见修复后样本：

```json
{
  "scene": "event",
  "screen": {"status": "visible", "view": "divination"},
  "available_actions": [
    "set_divination_tool", "divine", "inspect_ui", "inspect_potions",
    "inspect_relics", "inspect_deck", "inspect_map", "inspect_event"
  ]
}
```

定稿采用统一视图工具，因为它没有次数消耗或奖励结算，参数也无需引用从观察获得的动态ID。

## 建议范围

小范围整理占卜的页面检查和工具切换分支，共用按钮可操作条件，使tools[].enabled、available_actions和执行一致。静态棋盘、图案识别、教学及图片策略保持现有行为；divine的坐标、次数消耗和揭开回执留到其自身审阅。

工具提示可缩为“切换大／小占卜范围，不消耗次数”；通用错误恢复规则由服务说明提供。最终要求以下方输出定稿为准。

## 输出定稿

set_divination_tool统一为视图操作：不要求已有观察许可，在当前可交互棋盘上按原生按钮切换big/small；成功返回get_observation.actions_only格式并刷新许可，不返回transition或图片，不记录玩法事件。重复选择当前工具成功，保持次数、棋盘和资源不变。保留tool枚举与default/full，不新增summary或操作参数。

页面、忙碌及按钮不可用分别给具体原因，执行、tools[].enabled和available_actions共用检查。明确未交互的拒绝使用现有视图恢复规则；已有许可可直接继续合法操作，首次拒绝不生成许可。已交互、上下文改变、坏响应、未知结果或取消不恢复旧许可。成功前核对同一对局、棋盘和实际选中工具。

小范围拆出切换分支及共享页面／按钮检查；divine的状态核对、坐标、次数消耗、事件记录和结算回执保留现状，留待自身审阅。旧样本不覆盖，修复后另存实际JSON。
