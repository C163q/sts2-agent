# select_card 审阅与建议

> 当前状态：场景核验完成，24 类组合场景和 58 项相关 Python 检查通过，已整理 91 份完整公共返回。两项错误恢复与说明问题及选中反馈缺口共三项待处理，选中／取消事件方案待确认；尚未修改工具行为或核销。开发证据见[核验记录](2026-11-05-select-card-development-notes.md)。

## 优先处理的问题

| 问题 | 实际表现与影响 | 建议与状态 |
| --- | --- | --- |
| 没有点击也要求重新观察 | 传入不存在的卡牌 ID，候选和 UI 完全没变，随后选择有效卡牌仍返回 `observation_required`。没有选牌界面、把确认预览当候选点击等拒绝也有同样问题 | 中优先级；已复现，待确认修复。只对明确未点击、未滚动的前置拒绝保留已有观察许可；状态过期、滚动期间变化或结果未知不能据此保留 |
| 拒绝原因过于笼统 | 没有选牌界面、卡牌 ID 不属于候选、正在查看战场、页面被覆盖、需要确认预览、卡包不能单取一张等情况，对 LLM 都只说 `The requested action is unavailable.` | 中优先级；已复现，待确认修复。区分具体原因，并指出返回选牌、关闭覆盖页或使用当前按钮；任意异常诊断继续留在内部 |
| 选中／取消没有直接反馈 | 多选页面中，玩家能看到选中标记或牌的位置变化，但选牌回执只有选择类型和状态，`events:[]` 无法表达到底选中了还是取消了哪张牌 | 中优先级；现有多选及手牌样例已证实。建议在 `transition.events` 增加选中／取消事件，待确认；不要求为获取这项 UI 反馈再调用观察 |

这些问题在新增参数之前处理。非法参数已在本地校验，不进入游戏，也不丢弃已有许可；无需把它与上述原生拒绝混为一谈。

## 工具做什么

`select_card` 点击当前选择中的一张牌，`card_id` 使用候选的 `id`，不是列表序号，也不是牌种 ID。工具会滚动定位可浏览列表中的目标，再按原生规则点击。

- 三选一和卡牌奖励通常立即提交，之后可能恢复战斗、回到奖励或进入下一次选择。
- 普通网格、牌堆和手牌选择按页面规则选择、取消或完成；不能假设每次点击都会关闭页面。
- 牌组移除、升级、附魔、变牌可能进入确认预览。此时使用 `selection_option` 的确认或返回按钮，不再点击预览中的牌。
- 卡牌包通过 `selection_option` 的 `bundle:N` 选择整包；结果展示页通过确认按钮关闭。它们显示了牌，但不允许 `select_card` 单独选择。

## 当前参数与返回

| 参数 | 当前行为 |
| --- | --- |
| `card_id` | 必填，0 至 2147483647 的整数；使用当前 `selection.cards[].id` |
| `preset` | `default` 为默认；`full` 保留公共空值。没有 `summary` |

成功返回与其他动作一致：场景、页面、当前可用操作、简短的选择类型／状态，以及 `transition`。完整候选、已选 ID 和比较通过 `get_observation` 或 `inspect_selection` 按需读取；`full` 不会把动作回执扩展成完整画面。

现有实现仅选择、取消或进入预览时经常返回 `transition.events:[]`：尚未发生牌的移动、升级等实际变化。这解释了当前输出，但仍缺少玩家可见的选中反馈。确认后才发生的效果属于确认调用，不能提前写入选牌调用；点击直接完成选择并引发实际效果时，现有事件随该次调用返回。

`complete:true` 表示已经到达可输入的边界，不表示整个选择流程结束；`choice_required` 可以表示仍需选择、确认或继续下一次选择。成功结果满足公共续接条件时可直接继续调用，不要求每次插入观察。

## 场景与完整示例

完整样例、调用参数及原始记录索引见[示例目录](2026-11-05-select-card-examples/README.md)。这些是实测公共返回，保留当前拒绝缺陷，不能当作修复后的契约。

| 场景 | 选中后的实际行为与完整返回 |
| --- | --- |
| 三选一 `choose_one` | [选中](2026-11-05-select-card-examples/choose_one-04-choose_candidate.full.json)即提交；该例恢复玩家行动 |
| 卡牌奖励 `reward` | [选中](2026-11-05-select-card-examples/reward-03-choose_candidate.full.json)立即把牌加入牌组，事件为 `card_added, pile:deck`；该例奖励来自事件，因此回到 `scene:event` |
| 普通网格 `grid` | [选中第一张](2026-11-05-select-card-examples/grid-03-select_first.full.json)、[再次点击取消](2026-11-05-select-card-examples/grid-05-deselect_without_read.full.json)；[选够两张](2026-11-05-select-card-examples/grid-09-choose_candidate.full.json)自动完成并获得卡牌 |
| 战斗牌堆 `combat_pile` | [选中](2026-11-05-select-card-examples/combat_pile-03-choose_candidate.full.json)完成选择；这个测试场景只发起原生选择，没有接续执行卡牌效果，因此没有移动事件 |
| 普通牌组 `deck` | [选中](2026-11-05-select-card-examples/deck-03-choose_candidate.full.json)进入移除确认；真正移除在[确认](2026-11-05-select-card-examples/deck-08-confirm.full.json)后记录 |
| 手牌 `hand` | [选中](2026-11-05-select-card-examples/hand-04-select_first.full.json)、[取消](2026-11-05-select-card-examples/hand-06-deselect_without_read.full.json)后仍等待输入；这个保留手牌页面需要另行确认 |
| 手牌升级 `hand_upgrade` | [选中](2026-11-05-select-card-examples/hand_upgrade-04-select_first.full.json)显示比较，[再次点击](2026-11-05-select-card-examples/hand_upgrade-06-deselect_without_read.full.json)可取消；未确认时不记录实际升级 |
| 牌组升级 `deck_upgrade` | [火堆单张](2026-11-05-select-card-examples/smith-04-choose_candidate.full.json)直接展开比较；[多张选择](2026-11-05-select-card-examples/multi_upgrade-09-choose_candidate.full.json)达到数量后进入比较；都要另行确认 |
| 牌组附魔 `deck_enchant` | [单张](2026-11-05-select-card-examples/enchant_single-04-choose_candidate.full.json)和[多张](2026-11-05-select-card-examples/enchant_multi-13-choose_candidate.full.json)达到数量后进入预览；附魔事件在确认时返回 |
| 牌组变牌 `deck_transform` | [选中](2026-11-05-select-card-examples/transform-04-choose_candidate.full.json)进入随机变牌确认；选中回执不提前提供变牌结果 |
| 卡牌包 `bundle` | [单取包内卡牌被拒绝](2026-11-05-select-card-examples/bundle-05-not_individually_selectable.full.json)；应使用整包按钮 |
| 结果确认 `view_cards` | 卡牌仅供查看，[`select_card` 被拒绝](2026-11-05-select-card-examples/view_cards-06-not_individually_selectable.full.json)；使用确认按钮关闭 |

其他边界包括：四十张候选中[直接选择末尾](2026-11-05-select-card-examples/scroll-03-choose_candidate.full.json)、两次外观相同的连续选择、滚动时发生并发选择、查看战场、牌组覆盖、选择后[胜利](2026-11-05-select-card-examples/victory-04-choose_candidate.full.json)或[死亡](2026-11-05-select-card-examples/death-04-choose_candidate.full.json)，以及选择后[进入战斗](2026-11-05-select-card-examples/combat_entry-03-choose_candidate.full.json)。[头槌选择](2026-11-05-select-card-examples/headbutt-11-select_card.full.json)正确返回 `card_moved, from_pile:discard, to_pile:draw`，不透露堆内位置。并发滚动的内部检查不伪装成 MCP 公开返回。

例如火堆选择 Bash 后，`preset:"full"` 返回：

```json
{
  "scene": "rest_site",
  "screen": {"status": "covered"},
  "available_actions": [
    "selection_option", "inspect_ui", "inspect_potions",
    "inspect_relics", "inspect_selection"
  ],
  "selection": {"type": "deck_upgrade", "status": "visible"},
  "transition": {"stop_reason": "choice_required", "complete": true, "events": []}
}
```

升级尚未发生。使用 `inspect_selection` 可以读取已显示的比较，或按先前已读到的按钮直接确认；无须为了获取许可而重复读取。

核验未覆盖控制器交互、任意第三方选择页、真实跨局竞争和所有卡牌效果组合；未支持页面与异常竞争按源码边界说明，不据普通页面样本宣称全面验证。

## 建议的设计范围

建议保留现有参数与紧凑动作回执，不增加 `summary`，也不把多选合成一次提交：点击之间可能出现确认、自动提交或下一次选择，逐次点击符合当前操作用途。

选中反馈有两个可行位置：

- **推荐：新增 `card_selected`／`card_deselected` 事件。** 每条只含 `sequence`、`type` 和 `card:{id,name}`，名称以已公开牌面为准。直接表达此次 UI 操作造成的变化，沿用现有卡牌事件身份格式。
- 在回执的 `selection` 补回完整 `selected_ids`。便于直接读取当前集合，但每次重复完整列表，而且选择自动提交或切换页面后没有同一个集合可返回；这也不能单独表达先取消旧牌再选中新牌的变化。保留为替代方案，不建议与事件同时增加。

以下为推荐方案的示意，尚未实现：

```json
{
  "stop_reason": "choice_required",
  "complete": true,
  "events": [
    {"sequence": 1, "type": "card_selected", "card": {"id": 7, "name": "Defend"}}
  ]
}
```

再次点击同一已选牌时记录 `card_deselected`；原生自动替换已选牌时，按实际操作先记录旧牌取消、再记录新牌选中。被拒绝或原生没有改变选择时不生成虚假反馈。进入预览或提交后页面清空不代表取消，不能把关闭页面误报成全部取消。

记录须跟随原生实际接受的选择，覆盖最后一张导致自动提交的情况；不能只比较调用前后的最终页面，也不能因为收到了点击请求就假定选中。选中和随后实际移牌、升级等事件按发生顺序共用 `sequence`；不会提前给出随机结果，default/full 都保留这些事件。原生取消预览造成的已选变化也应复用同一记录入口，`selection_option` 的其他行为仍留待该工具审阅。

需要的小范围重构包括候选前置诊断和独立的选中状态记录入口；不把记录逻辑堆进分派函数。滚动定位和原生点击继续由现有选择动作负责；不借此扩大为 `selection_option` 或视图操作的完整重写。
