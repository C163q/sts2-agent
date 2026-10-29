# 选牌与查看战场

适用于 Mod `0.14.0`、MCP server `0.11.0`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。这些接口操作已经打开的原生选牌界面，不负责使用药水、打出牌或点击事件选项来触发选择。源码核对与范围见 [设计依据](../research/2026-10-30-card-selection-design.md)。

## 观察与信息范围

`get_observation` 的 `selection` 在没有选择时为 `null`；有选择时包含：

| 字段 | 含义 |
| --- | --- |
| `type` | `choose_one`、`reward`、`grid`、`combat_pile`、`deck`、`hand` 或 `unsupported` |
| `status` | `visible` 为选牌页面；`battlefield` 为点击眼睛后查看战场；`covered` 为被其他页面覆盖；`unsupported` 为尚未接通的选择类型 |
| `prompt`、`min_select`、`max_select` | 当前选择提示与数量范围；隐藏时为 `null` |
| `cards` | 当前画面可见候选，包含稳定整数 `id`；已经展开显示的牌面可附正文，手牌摘要不自动展开正文 |
| `selected_ids` | 当前已选项目；隐藏时为 `null` |
| `options` | 当前显示的按钮及 `id`、英语 `text`、`enabled`；未启用不能点击 |
| `can_view_battlefield` | 原生眼睛当前可用，可显式切换视图 |

`cards` 在查看战场、被覆盖或未支持时为 `null`，与没有候选的空列表不同。网格可能滚动，基础观察不补齐屏幕外候选；`inspect_selection()` 显式读取整个可浏览候选列表、正文及共享 `hover_tips`，不会展开尚未生成的结果，也不会切换视图。共享解释通过整数 `card_ids` 引用候选。手牌选择沿用战斗手牌 ID。

基础观察和查看结果按情境附简短 `notes.selection`：选择遮挡时提示用眼睛查看战场；查看战场时提醒仍有选择待完成，须返回选择界面；牌组、牌堆或地图覆盖选择时提醒先关闭当前查看页。这些说明不重复候选正文或按钮列表。

## 操作

`select_card({"card_id": 7})` 等价于点击一张候选。多选界面会选择或取消该项，单选界面可能立即提交；原生需要确认时必须再调用 `selection_option`。它不直接更改牌组，不绕过选择结果的网络同步，不替代正常结算。

`selection_option({"option_id": "confirm"})` 点击观察中列出的启用按钮。可能出现 `skip`、`confirm`、`cancel_preview`、`cancel` 或奖励 `alternative:N`；含义以当前 `text` 为准。预览取消与放弃整个选择分别处理。奖励替代选项还可能是治疗、献祭或重新生成，不能一律视为跳过。允许选零张的手牌选择通过原生确认按钮提交空选择。

两类动作都必须先调用 `get_observation`，只消耗一次观察许可，失败后也须重新观察。`inspect_selection` 不产生新的动作许可；若读取前后的状态没有改变，保留原许可。原生滚动候选由工具先定位再点击，定位期间若选择已经改变则拒绝输入。选择实例代际参与底层令牌，防止外观相同的连续选择复用旧许可。

## 眼睛与现有查看工具

调用 `set_selection_view({"view":"battlefield"})` 点击原生眼睛。此后基础观察及 `inspect_hand`、`inspect_combatants`、`inspect_ui`、药水、遗物详情按当前可见性工作；牌组、地图和牌堆还要求各自原生入口可用。小型候选和简单网格使用其自己的牌堆入口，不能强行点击被禁用的战斗按钮。

查看战场不允许出牌、结束回合或直接选隐藏的候选，`available_actions` 为空。`close_card_view` 只关闭牌组或牌堆，保留底层选择与原有查看状态；地图由 `close_map` 关闭。关闭覆盖页后，调用 `set_selection_view({"view":"selection"})` 返回候选。视图工具清除动作许可，提交选择前重新观察；普通观察和只读详情都不会自动切换眼睛。

## 动作后的结算

选牌动作与 `end_turn` 使用同一可感知事件记录，返回基本观察和 `transition`。点击多选但尚未确认时停在 `choice_required`；真正提交后等待后续选择、玩家可行动、胜负或超时。非战斗选择完成使用 `selection_resolved`。事件字段、`complete` 和超时恢复规则见 [结束回合](end-turn.md)。连续选择每次单独操作，不自动代选，也不会因等待期间出现下一次选择而一直挂起。

选择状态直接来自界面，不要求已经完成过一次回合。选择悖论在第一回合开始时也可识别并操作。暴政消耗和本版本计划妥当保留手牌使用同一手牌接口。

当前接通小型候选、卡牌奖励、简单网格、战斗牌堆选择、普通牌组选择以及普通手牌选择。专门的升级、变化、附魔、手牌升级和卡牌包选择返回 `unsupported`，不提供动作，但会作为已识别的交互边界立即返回 `choice_required`；任意第三方页面仍需额外适配。静态遮挡按已核实的原生页面判断，不能保证覆盖任意像素级遮挡。声音、其他游戏版本与完整自动游玩不属于已验证范围。

标准库文件客户端支持相同操作：`select_card --card-id 7 --expected-state <令牌>`、`selection_option --option-id confirm --expected-state <令牌>`，以及 `set_selection_view --view battlefield`；这些参数与既有 `--ipc-dir` 一起使用。原始令牌通过 `get_state --raw` 获取，MCP 客户端由会话内部管理。
