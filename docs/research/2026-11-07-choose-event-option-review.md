# choose_event_option 核验与设计建议

> 当前状态：定稿已实现并完成验收，待独立审阅及合入；[实施记录](2026-11-07-event-option-recovery-implementation.md)与[十八份修复后JSON](2026-11-07-event-option-fixed-examples/README.md)另存，下文现状与旧样本保留审阅基线。总流程见[工具清单](2026-11-02-mcp-tool-review.md)，源码与测试依据见[开发核验](2026-11-07-choose-event-option-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确拒绝后，合法操作仍被要求重新观察 | 中：误选锁定、已替换或不存在的选项后，改选合法项也得到 observation_required；选牌、奖励及确认框中误用后，正常后续动作同样被阻断 | 点击前、画面未改变的拒绝保留已有许可，允许直接选择合法动作 | 已修复并完成验收 |
| 错误原因与下一步提示不够具体 | 中：没有事件、地图覆盖、选牌中、奖励中、确认框中、事件已完成、ID 不存在及选项锁定，均只返回同一个“操作不可用” | 区分当前页面、结算等待和选项自身原因，提示对应查看或操作工具；可用操作列表复用相同条件 | 已修复并完成验收 |

这两项属于已有[错误恢复与错误信息待办](../development/TODO.md#当前工具审阅结束后处理)。MCP 本地参数错误已能保留许可；缺口在请求到达 Mod 后、尚未点击的拒绝。

## 当前参数与适用范围

```json
{"option_id": 0, "preset": "default"}
```

- `option_id` 必填，是 get_observation 或 inspect_event 返回的选项 ID；接受非负的 32 位整数。它不是选项数组下标，翻页后使用新页面的 ID。
- `preset` 为 `default/full`，默认 `default`。动作回执已经足够精简，当前没有 `summary`。
- 点击一个启用的通用事件选项。完成后的独立前进按钮使用 proceed；先古之民、建筑师、占卜操作和确认框各用对应工具。
- 保留原生危险选项选择及后续流程。`lethal_warning` 是界面红色警告，瓶中精灵仍可能救活玩家。

## 典型场景与返回

[十六份完整 JSON](2026-11-07-choose-event-option-examples/README.md)均为当前基线实际 MCP 返回，涵盖正常变化、选择、奖励、确认框、占卜、进入战斗、死亡／复活和拒绝；参数及来源逐份记录。

| 场景 | 当前回执 | 后续查看或操作 |
| --- | --- | --- |
| 普通翻页或完成事件 | `action_completed`；生命、最大生命、金币等可见变化进入 events | 按需 inspect_event；完成后 proceed |
| 移除、升级等选牌 | `choice_required`；附 selection 的类型及状态 | inspect_selection、select_card、selection_option |
| 打开奖励页 | `action_completed`；尚未领取的奖励不生成获得事件 | inspect_rewards、claim_reward、proceed |
| Trial 打开确认框 | `action_completed`，screen.view 为 confirmation | get_observation 查看正文，respond_to_confirmation 作答 |
| 打开占卜 | `action_completed`，screen.view 为 divination；已支付金币进入 events | inspect_event、set_divination_tool、divine |
| 进入战斗 | 普通玩家回合为 `player_ready`；首回合自动效果要求选牌时为 `choice_required` | 战斗或选牌工具 |
| 危险选项 | 游戏确认整局失败时 `run_lost`；复活后继续事件则为 `action_completed` | 根据实际回执继续 |

普通进入战斗的 player_ready 分支按源码核对；新游戏实测覆盖了首回合选牌分支。详细边界见开发核验。

例如进入升级选牌，实际完整 full 回执为：

```json
{
  "scene": "event",
  "screen": {"status": "covered"},
  "available_actions": [
    "select_card", "inspect_ui", "inspect_potions", "inspect_relics", "inspect_selection"
  ],
  "selection": {"type": "deck_upgrade", "status": "visible"},
  "transition": {"stop_reason": "choice_required", "complete": true, "events": []}
}
```

这里 events 为空合理：打开选择界面时还没有升级卡牌。类似地，打开确认框、仅翻页或仅展示奖励时，可以没有资源／物品变化。选项效果已有变化时，实际回执能够记录；Abyssal Baths 的样例依次记录最大生命增加、当前生命随之增加、随后受伤。

当前选择锁定项的实际错误为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "The requested action is unavailable.",
    "recovery": "get_observation"
  }
}
```

随后选择启用项仍返回 observation_required，这正是第一项问题。

## 建议范围

建议维持单个 option_id、default/full 和现有精简动作回执，不增加参数或 summary。一次选择会进入新页面、选牌、奖励或战斗，下一步通常需要依据新画面决策，当前没有批量选择的需求。

修复以上两项时，集中整理事件的页面可操作条件与单个选项的拒绝原因，让执行、选项 enabled 和 available_actions 共用。覆盖页面分别提示 close_map、close_card_view、inspect_selection、inspect_rewards、inspect_event 或 respond_to_confirmation；事件已完成则提示 proceed；已替换 ID 和锁定项给出各自原因。

重构范围限于事件检查及对应动作分支，复用现有错误恢复机制。点击后异常、过期观察和未知结果仍要求重新读取；事件结算、战斗进入及可见变化记录保留现有共用流程。

验证应沿用已采集的典型分支，并将“拒绝后强制观察”的现状断言改为“合法后续动作直接成功”。还应补齐牌组覆盖及新错误原因的检查。

## 输出定稿

维持单个非负 Int32 option_id、default/full、原生按钮操作及现有精简回执，不新增summary或操作参数。

页面覆盖、动作忙碌与选项原因集中于EventInspection；执行、Read.enabled与available_actions共用。区分无事件、地图／牌组／选牌／奖励／占卜／确认框覆盖、结算等待、事件完成、目标ID已不存在、锁定及已用选项，并提供对应操作提示。静态显示、悬停和点击检查仍各自承担原有职责。

相同快照下、点击前且UI未改变的明确拒绝保留已有许可，返回具体原因和choose_legal_action；原始参数拒绝也提供未提交保证。本地参数错误保持原有恢复。首次无许可、stale_state、点击后异常及未知结果不生成或恢复许可。

沿用现有事件结算、战斗进入、选择边界和变化记录机制，小范围重构不改变正常成功回执。旧样本保留；修复后另存实际JSON，验证合法后续动作可直接继续。
