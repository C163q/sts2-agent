# inspect_selection 审阅与建议

> 当前状态：三项修复及一次独立审查完成，28 组 GUI 场景／验证组合、676 项 Python 和 124 项 C# 检查通过，工具核销，无遗留或阻塞。下文保留审阅基线的 20 类组合场景和 100 份返回，修复后行为与验证见[实施记录](2026-11-05-selection-inspection-implementation.md)。

## 优先处理的问题

下表描述修复前审阅基线的表现，处理状态指向已实现修复。

| 问题 | 实际表现与影响 | 建议与状态 |
| --- | --- | --- |
| 未操作的拒绝也要求重新观察 | 没有选牌界面时，普通读取失败后可以直接结束回合；同样状态下传入 `view_upgrades:false`，尚未点击任何控件就被拒绝，却使后续合法动作要求重新观察 | 中优先级；已修复并针对验证。仅对明确未交互的拒绝保留已有许可；真正切换过 UI、状态过期或结果未知时仍须重新读取 |
| 拒绝原因没有传给 LLM | 底层知道“没有选牌界面”或“需要返回选牌界面”，公开结果却只有 `The requested action is unavailable.`，无法判断该返回选择、关闭覆盖页，还是改用其他工具 | 中优先级；已修复并针对验证。公开明确且安全的拒绝原因，区分没有选择、选择未支持、查看战场及其他页面覆盖；异常诊断继续留在内部 |
| 卡包与结果页文字漏读 | 卡包页横幅写着“选择一组”，潘多拉魔盒结果页底部说明这些是已变化的卡牌；两者 `selection.prompt` 却是 `null`。普通 `default/summary` 会直接省略它 | 中优先级；已修复并针对验证。沿用 `prompt` 返回实际显示的文字，同时修复共用读取影响的 `get_observation`；不从隐藏页面补内容 |

这些问题先于新增参数处理。没有发现需要改变卡牌 ID、选择按钮或随机变牌隐私规则的依据。

## 已确认的参数与摘要

现有参数已足够，建议保持名称和行为：

| 参数 | 当前行为 |
| --- | --- |
| `preset` | `default` 为默认，使用公共空值规则；`full` 保留空值及完整正文；`summary` 对候选、包内卡牌及比较两侧统一使用手牌摘要 |
| `card_ids` | 省略或 `null` 返回全部，`[]` 不返回卡牌详情；保留原生顺序，重复去重，无效 ID 合并报告 |
| `view_upgrades` | 省略保持当前 UI；布尔值点击可用的原生升级复选框。该页不支持时保留原数据，附 `upgrade_view_unavailable`，不代选或确认 |

`summary` 保留提示、选择数量范围、全部已选 ID、按钮和当前升级模式。卡牌保留身份、费用、附魔、Affliction 和实际标记，不保留卡牌正文、稀有度、卡池和悬停帮助；空描边和空不可出牌标记省略。选择级附魔说明描述正在执行的操作，继续保留。

筛选只限制卡牌详情：不改变已选项、不删按钮、不改变整包选择方式。比较按原牌 ID 筛选，命中就保留整组；随机变牌仍为 `random:true, after:null`。`[]` 仍可保留非空 `selected_ids`、包 ID 和按钮，这表示“没有请求卡牌详情”，并非原生列表为空。

本项只修正确性和相应小范围共用逻辑，沿用现有参数与摘要，不拆分工具或增加筛选维度。非空 `prompt` 在所有预设保留；null 时只有 full 保留，default/summary 继续省略。

## 场景目录与完整返回

共有十二种已支持的选择类型，另有未支持、隐藏和覆盖等拒绝分支。同一类型可能来自卡牌、药水、事件、商店或遗物，但其结构取决于实际打开的页面。

| 场景 | 当前返回的主要区别 |
| --- | --- |
| 小型三选一 `choose_one` | [完整返回](2026-11-05-inspect-selection-examples/choose_one-04-full-candidates.json)：候选、跳过等实际按钮；选中可能立即继续结算 |
| 卡牌奖励 `reward` | 候选及本页实际生成的按钮，例如[献祭](2026-11-05-inspect-selection-examples/paels_wing-05-full-candidates.json)、[重掷](2026-11-05-inspect-selection-examples/driftwood-05-full-candidates.json) |
| 普通网格 `grid` | [完整返回](2026-11-05-inspect-selection-examples/grid-03-full-candidates.json)：可浏览候选、多选数量与已选 ID；另有[四十张候选](2026-11-05-inspect-selection-examples/large_grid-03-full-candidates.json) |
| 战斗牌堆选择 `combat_pile` | [完整返回](2026-11-05-inspect-selection-examples/combat_pile-03-full-candidates.json)：该次选择的候选和数量范围，不是打开普通牌堆浏览 |
| 普通牌组选择 `deck` | [候选](2026-11-05-inspect-selection-examples/deck-03-full-candidates.json)及[确认预览](2026-11-05-inspect-selection-examples/deck-15-full-selected.json)；预览卡牌放在 `cards`，没有新增比较字段 |
| 手牌选择 `hand` | [完整返回](2026-11-05-inspect-selection-examples/hand-04-full-candidates.json)：使用手牌 ID，可选择零张时保留原生确认规则 |
| 手牌升级 `hand_upgrade` | [未选时](2026-11-05-inspect-selection-examples/hand_upgrade-04-full-candidates.json) `upgrade_preview:null`；[选中后](2026-11-05-inspect-selection-examples/hand_upgrade-16-full-selected.json)为已显示的 `before/after` |
| 牌组升级 `deck_upgrade` | [火堆选择并展开比较](2026-11-05-inspect-selection-examples/smith-16-full-selected.json)：`upgrade_previews`；[多张比较](2026-11-05-inspect-selection-examples/multi_upgrade-16-full-selected.json)没有显示的原牌数据仍未知 |
| 牌组附魔 `deck_enchant` | [单张比较](2026-11-05-inspect-selection-examples/enchant_single-16-full-selected.json)、[多张确认](2026-11-05-inspect-selection-examples/enchant_multi-20-full-selected.json)：操作说明 `enchantment` 与 `enchant_previews`，不虚构附魔后的效果 |
| 牌组变牌 `deck_transform` | [完整返回](2026-11-05-inspect-selection-examples/transform-18-full-selected.json)：`transform_previews`；随机示意不当作已决定的结果 |
| 卡牌包 `bundle` | [未展开](2026-11-05-inspect-selection-examples/bundle-04-full-candidates.json)时 `bundles[].cards`；[展开确认](2026-11-05-inspect-selection-examples/bundle-16-full-selected.json)时使用 `cards`，通过包按钮选择整包 |
| 结果确认 `view_cards` | [完整返回](2026-11-05-inspect-selection-examples/view_cards-04-full-candidates.json)：已完成变化后的卡牌，数量范围为 0，列出的确认按钮用于关闭结果页 |

`scene/screen` 与共用上下文一致：`scene` 是底层战斗或房间，`selection.type` 表达选牌类型。例如火堆锻造仍为 `scene:rest_site`。工具不额外返回 `available_actions`，使用基础观察查看即可。

完整 JSON 见[样例目录](2026-11-05-inspect-selection-examples/README.md)：53 份 full、47 份 summary；样例保留当前问题，不能当作修复后的契约。拒绝时不返回隐藏候选；查看战场需先返回选择，牌组覆盖需先关闭覆盖页。

错误恢复的完整实测链：[普通拒绝](2026-11-05-inspect-selection-examples/no_selection-02-full-error.json)后可直接结束回合；[带升级参数的拒绝](2026-11-05-inspect-selection-examples/no_selection-06-full-error.json)后，[同一合法操作被要求重新观察](2026-11-05-inspect-selection-examples/no_selection-07-full-error.json)。

## 实施边界

建议的小范围重构仅涉及选牌查看的可用性诊断、点击前后的明确拒绝，以及当前提示文字读取；`get_observation` 和详情继续使用同一个选牌读取入口。参数投影、通用卡牌格式和实际选择动作保持各自职责。

三项修复见[实施记录](2026-11-05-selection-inspection-implementation.md)和[修复后完整返回](2026-11-05-selection-inspection-fixed-examples/README.md)。`select_card`、`selection_option` 和 `set_selection_view` 的整体动作审阅仍属于后续各自条目。
