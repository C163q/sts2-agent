# selection_option 审阅

> 当前状态：现状核验完成，待设计确认。25 组游戏情形和 42 项相关 Python 检查通过，提供 81 份完整返回；两项错误处理问题尚未修复，工具未核销。开发证据及未验证范围见[开发核验记录](2026-11-05-selection-option-development-notes.md)。

## 优先处理的问题

| 问题 | 优先级与影响 | 建议及状态 |
| --- | --- | --- |
| 点击前拒绝也要求重新观察 | 中。按钮不存在、确认条件未满足或页面被覆盖时，没有点击任何按钮，却会丢失已有观察许可；紧接着的合法动作仍可能得到 `observation_required` | 仅对已确认没有交互、状态仍有效的前置拒绝保留已有许可。状态过期、发生过交互或结果不确定仍须重新读取；待定稿 |
| 对外错误缺少具体原因 | 中。没有选择、查看战场、页面覆盖及按钮不可用等情况，对外均是 `The requested action is unavailable.`，LLM 无法判断该如何继续 | 公开准确且简短的固定原因和对应恢复方式，区分按钮未提供和已提供但未启用；待定稿 |

## 工具用途与参数

`selection_option` 点击当前选牌页面已经提供且启用的按钮。它处理确认、返回预览、放弃整个选择、跳过候选和奖励替代按钮，也处理选整包与结果页关闭。点击事件选项、领取奖励入口等由其他工具负责。

| 参数 | 当前行为 |
| --- | --- |
| `option_id` | 必填，非空白字符串，最长 128 字符；使用当前 `selection.options[].id` 的准确值 |
| `preset` | 默认 `default`，可用 `full`；没有 `summary` |

例如奖励页面可能列出：

```json
[
  {"id": "skip", "text": "Skip", "enabled": true},
  {"id": "alternative:1", "text": "Sacrifice", "enabled": true}
]
```

`alternative:1` 是控制用 ID，`Sacrifice` 才是显示名称。浮木对应的名称为 `Reroll`；编号按当次页面生成，不能把 `alternative:1` 固定解释为某种效果。旧文档中的“治疗”来自尚未核实的源码注释，已更正；当前确认的替代按钮见开发记录。

## 按钮含义

| 按钮 | 适用场景与行为 |
| --- | --- |
| `confirm` | 提交手牌、普通网格、牌堆等选择，进入或提交移除／附魔／变牌预览，提交升级预览，或关闭仅展示卡牌的结果页；含义取决于当前页面 |
| `cancel_preview` | 返回预览前的候选页，清除原生已选项；不是放弃整个选择 |
| `cancel` | 只在原生允许时放弃整个选择；不能用它代替没有提供的跳过按钮 |
| `skip` | 跳过可跳过的三选一或卡牌奖励候选；奖励场景会返回仍含该奖励入口的列表，不等于放弃整个奖励列表 |
| `bundle:N` | 选择整包并展开确认预览；真正入牌组发生在确认后 |
| `alternative:N` | 执行当次 `text` 所指的奖励替代操作；献祭会完成该奖励，重掷会重新打开候选并消耗当次重掷机会 |

数量不足时，确认按钮可能直接隐藏，而不是留在 `options` 中标为禁用。允许选零张的页面应点击原生确认，不传空卡牌列表伪造完成。

## 场景实测与 full 示例

[全部 81 份返回](2026-11-05-selection-option-examples/README.md)中，51 份为 `selection_option`，其余 30 份为按钮与预览上下文；参数、来源与完整性均逐份可追溯。以下各链接都是本轮实测，没有用整理的伪返回代替。

| 场景 | 完整返回及要点 |
| --- | --- |
| 可跳过的三选一 | [跳过](2026-11-05-selection-option-examples/choose_skip-05-skip.full.json)后恢复玩家行动 |
| 卡牌奖励候选 | [跳过](2026-11-05-selection-option-examples/reward_skip-03-skip.full.json)回到奖励列表，该入口仍可再次打开；放弃奖励列表需另行 `proceed` |
| 普通网格手动确认 | [确认两张](2026-11-05-selection-option-examples/grid_manual-07-confirm.full.json)；这个夹具仅发起选牌，不接续卡牌效果，因此没有实际消耗事件 |
| 战斗牌堆候选 | 该夹具不提供确认按钮，[任意未提供 ID 被拒绝](2026-11-05-selection-option-examples/invalid_option-03-invalid_option.full.json)；实际单张候选用 `select_card` 自动提交 |
| 手牌保留 | [确认零张](2026-11-05-selection-option-examples/hand_zero-05-confirm_zero_cards.full.json)或[确认一张](2026-11-05-selection-option-examples/hand_one-07-confirm.full.json)后继续结束回合，并记录弃牌、敌人行动及后续抽牌 |
| 手牌升级 | [确认](2026-11-05-selection-option-examples/hand_upgrade-07-confirm.full.json)后继续原生卡牌效果 |
| 普通牌组选择 | [放弃整个选择](2026-11-05-selection-option-examples/deck_cancel-03-cancel_selection.full.json)、[返回预览](2026-11-05-selection-option-examples/deck_preview-06-cancel_preview.full.json)；该夹具只发起选择，确认本身不会移除卡牌 |
| 商店真实删牌 | [返回预览](2026-11-05-selection-option-examples/shop_remove-11-cancel_preview.full.json)不收费；重新选择并[确认](2026-11-05-selection-option-examples/shop_remove-16-confirm.full.json)后实际扣金币、移除卡牌 |
| 火堆单张升级 | [返回预览](2026-11-05-selection-option-examples/smith-08-cancel_preview.full.json)取消选择；重新选择并[确认](2026-11-05-selection-option-examples/smith-13-confirm.full.json)才升级 |
| 多张升级 | [返回预览](2026-11-05-selection-option-examples/multi_upgrade-08-cancel_preview.full.json)与[确认](2026-11-05-selection-option-examples/multi_upgrade-15-confirm.full.json) |
| 单张／多张附魔 | [单张返回](2026-11-05-selection-option-examples/enchant_single-08-cancel_preview.full.json)、[确认](2026-11-05-selection-option-examples/enchant_single-13-confirm.full.json)；[多张返回](2026-11-05-selection-option-examples/enchant_multi-15-cancel_preview.full.json)、[确认](2026-11-05-selection-option-examples/enchant_multi-24-confirm.full.json) |
| 变牌 | [返回预览](2026-11-05-selection-option-examples/transform-11-cancel_preview.full.json)不提供未来结果；[确认](2026-11-05-selection-option-examples/transform-16-confirm.full.json)后才记录原生实际变化 |
| 整包选择 | [展开第一包](2026-11-05-selection-option-examples/bundle-07-select_bundle.full.json)、[返回](2026-11-05-selection-option-examples/bundle-10-cancel_bundle.full.json)、[改选另一包](2026-11-05-selection-option-examples/bundle-13-reselect_bundle_without_read.full.json)、[确认入牌组](2026-11-05-selection-option-examples/bundle-15-confirm_bundle.full.json) |
| 结果卡展示 | [确认关闭](2026-11-05-selection-option-examples/view_cards-08-confirm_results.full.json)，不重复记录已经发生的效果 |
| 佩尔之翼献祭 | [第一次](2026-11-05-selection-option-examples/paels_wing-07-alternative_1.full.json)完成奖励但不加卡；[第二次](2026-11-05-selection-option-examples/paels_wing-17-alternative_1.full.json)达到条件并记录获得遗物 |
| 浮木重掷 | [重掷](2026-11-05-selection-option-examples/driftwood-07-alternative_1.full.json)后等待新候选；旧重掷按钮[不能再次使用](2026-11-05-selection-option-examples/driftwood-16-alternative_1.full.json)；第二份奖励中还验证了重掷后跳过、再打开不恢复次数 |
| 确认后死亡／胜利 | 分别返回 [combat_lost](2026-11-05-selection-option-examples/death-07-confirm.full.json)、[combat_won](2026-11-05-selection-option-examples/victory-07-confirm.full.json)，不误报仍待选牌 |
| 无选择、条件不足、战场视图与覆盖页 | 对应完整拒绝及下一次 `observation_required` 均见[样例目录](2026-11-05-selection-option-examples/README.md)，保留待修复现状 |

例如火堆升级确认 `selection_option({"option_id":"confirm","preset":"full"})` 的完整返回是：

```json
{
  "scene": "rest_site",
  "screen": {"status": "visible"},
  "available_actions": [
    "proceed", "inspect_ui", "inspect_potions", "inspect_relics",
    "inspect_deck", "inspect_map", "inspect_rest_site"
  ],
  "transition": {
    "stop_reason": "action_completed",
    "complete": true,
    "events": [
      {"card": {"id": 29, "name": "Bash"}, "pile": "deck", "type": "card_upgraded", "sequence": 1}
    ]
  }
}
```

可变数量的牌组移除／附魔，以及要求手动确认的变牌流程，还可能先用候选页的 `confirm` 打开预览，再在预览内用同名按钮提交。这些分支已核对原生源码，但未新增对应的可变数量游戏样例；不能将所有 `confirm` 都解释为一次完成效果。

## 返回与事件

成功使用紧凑动作回执：场景、页面、可用工具、仍待处理的选择类型／状态，以及 `transition`。`full` 保留公共空值，不会把回执扩展成完整候选页面；要查看按钮、已选项或预览，按需使用 `get_observation` 或 `inspect_selection`。

`complete:true` 表示到达下一处可交互边界，不承诺整个选择流程已结束。`choice_required` 可以表示需要确认、返回候选或新一轮选择；确认后也可能恢复玩家行动、进入奖励、胜利或死亡。

取消普通牌组、升级、附魔和变牌预览时，实际清除的选择已有 `card_deselected`。确认提交和页面清理不应冒充取消。确认后发生的入牌组、移除、升级等实际变化仍进入各自事件。

有些成功操作合理地返回 `events:[]`：跳过没有造成已记录的资源变化、关闭结果页、重掷后等待新的候选，以及展开／返回整包预览。整包操作不冒充逐张点击；其结果可从实际展开的选择页读取。

## 设计建议

建议先修复上述两项错误处理问题，保留现有参数、按钮 ID 与紧凑回执，不新增 `summary`。回执已经用于确认动作到达何种边界，完整内容由查看工具按需提供。

小范围整理按钮前置检查和公开诊断即可，并与已有的候选点击检查共享通用的场景判断；不扩展为全工具重构。按钮仍通过原生点击执行，取消预览继续复用已有的选中变化记录。

这份建议尚待确认；不把候选设计写成已实现能力。
