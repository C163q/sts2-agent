# 选牌与查看战场

适用于 Mod `0.29.0`、MCP server `0.25.0`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。[搜刮工具](rewards.md) 负责打开奖励入口，这些接口操作已经打开的原生选牌界面，不负责点击事件选项；[出牌工具](card-play.md) 和 [药水工具](potion-actions.md) 可触发后续选择。通用接口依据见 [选牌设计](../research/2026-10-30-card-selection-design.md)，手牌升级依据见 [补充调研与验证](../research/2026-10-30-hand-upgrade-selection.md)。

## 观察与信息范围

`get_observation` 的 `selection` 在没有选择时为 `null`；有选择时包含：

| 字段 | 含义 |
| --- | --- |
| `type` | `choose_one`、`reward`、`grid`、`combat_pile`、`deck`、`hand`、`hand_upgrade`、`deck_upgrade`、`deck_enchant`、`deck_transform`、`bundle`、`view_cards` 或 `unsupported` |
| `status` | `visible` 为选牌页面；`battlefield` 为点击眼睛后查看战场；`covered` 为被其他页面覆盖；`unsupported` 为尚未接通的选择类型 |
| `prompt`、`min_select`、`max_select` | 当前选择提示与数量范围；隐藏时为 `null` |
| `cards` | 当前画面可见候选，包含稳定整数 `id`；已经展开显示的牌面可附正文，手牌摘要不自动展开正文 |
| `selected_ids` | 当前已选项目；隐藏时为 `null` |
| `options` | 当前显示的按钮及 `id`、英语 `text`、`enabled`；未启用不能点击 |
| `can_view_battlefield` | 原生眼睛当前可用，可显式切换视图 |
| `upgrade_previews` | 仅 `deck_upgrade` 提供；已经显示的单牌或多牌升级比较，未进入预览或隐藏时为空列表 |
| `upgrade_preview` | 仅 `hand_upgrade` 提供；已显示的升级前后牌面 `before`、`after`，未选择或隐藏时为 `null` |

`cards` 在查看战场、被覆盖或未支持时为 `null`，与没有候选的空列表不同。网格可能滚动，基础观察不补齐屏幕外候选；`inspect_selection()` 显式读取整个可浏览候选列表、正文及共享 `hover_tips`，不会展开尚未生成的结果，也不会切换视图。共享解释通过整数 `card_ids` 引用候选。手牌选择沿用战斗手牌 ID。

基础观察和查看结果按情境附简短 `notes.selection`：选择遮挡时提示用眼睛查看战场；查看战场时提醒仍有选择待完成，须返回选择界面；牌组、牌堆或地图覆盖选择时提醒先关闭当前查看页。这些说明不重复候选正文或按钮列表。

## 操作

`select_card({"card_id": 7})` 等价于点击一张候选。多选界面会选择或取消该项，单选界面可能立即提交；原生需要确认时必须再调用 `selection_option`。它不直接更改牌组，不绕过选择结果的网络同步，不替代正常结算。

`selection_option({"option_id": "confirm"})` 点击观察中列出的启用按钮。可能出现 `skip`、`confirm`、`cancel_preview`、`cancel` 或奖励 `alternative:N`；含义以当前 `text` 为准。预览取消与放弃整个选择分别处理。奖励替代选项还可能是治疗、献祭或重新生成，不能一律视为跳过。允许选零张的手牌选择通过原生确认按钮提交空选择。

两类动作使用当前观察许可，可以来自 `get_observation` 或上一步完整成功的动作结果，具体条件见[MCP 动作许可](mcp.md#调用和错误语义)；失败后须重新观察。`inspect_selection` 不产生新的动作许可；若读取前后的状态没有改变，保留原许可。原生滚动候选由工具先定位再点击，定位期间若选择已经改变则拒绝输入。选择实例代际参与底层令牌，防止外观相同的连续选择复用旧许可。

## 手牌升级

武装等触发的 `hand_upgrade` 复用以上工具。`cards` 只列原生筛选后可见的手牌和已经选中的原牌，不混入升级结果克隆；选择前不生成升级结果。`select_card` 选中后停在 `choice_required`，返回 `selected_ids` 和已经显示的 `upgrade_preview`。`before`、`after` 两侧包含牌名、费用与展开的正文，`id` 都是原手牌 ID。它们是同一张牌的比较，不能当成额外的可选牌。

再次点击已选 ID 等价于点击预览左侧原牌，取消选择；点击其他候选等价于改选，预览随之替换。只有点击启用的 `selection_option({"option_id":"confirm"})` 才提交选择并继续实际升级。未选择时原生确认按钮可能完全隐藏，以 `options` 为准，不自动确认。眼睛和覆盖页隐藏候选与预览，返回后保留待确认选择。

可升级手牌不足两张时，本版本 `CardSelectCmd.FromHandForUpgrade` 可能直接选择唯一候选或不做选择，工具应直接等待后续结算，不人为创建界面。已经升级的武装也沿用游戏自身的全手牌升级流程。

## 眼睛与现有查看工具

调用 `set_selection_view({"view":"battlefield"})` 点击原生眼睛。此后基础观察及 `inspect_hand`、`inspect_combatants`、`inspect_ui`、药水、遗物详情按当前可见性工作；牌组、地图和牌堆还要求各自原生入口可用。小型候选和简单网格使用其自己的牌堆入口，不能强行点击被禁用的战斗按钮。

查看战场不允许出牌、结束回合或直接选隐藏的候选，`available_actions` 为空。`close_card_view` 只关闭牌组或牌堆，保留底层选择与原有查看状态；地图由 `close_map` 关闭。关闭覆盖页后，调用 `set_selection_view({"view":"selection"})` 返回候选。视图工具清除动作许可，提交选择前重新观察；普通观察和只读详情都不会自动切换眼睛。

## 动作后的结算

选牌动作与 `end_turn` 使用同一可感知事件记录，返回基本观察和 `transition`。点击多选但尚未确认时停在 `choice_required`；真正提交后等待后续选择、玩家可行动、胜负或超时。非战斗选择回到[通用事件](events.md)、[先古之民](ancients.md)、商店、宝箱房、搜刮或[休息处](rest-site.md)时使用 `action_completed`；父事件的异步效果、卡牌预览和资源动画仍须完成。其余非战斗选择完成使用 `selection_resolved`。事件字段、`complete` 和超时恢复规则见 [结束回合](end-turn.md)。连续选择每次单独操作，不自动代选，也不会因等待期间出现下一次选择而一直挂起。

选择状态直接来自界面，不要求已经完成过一次回合。选择悖论在第一回合开始时也可识别并操作。暴政消耗和本版本计划妥当保留手牌使用同一手牌接口。

当前接通小型候选、卡牌奖励、简单网格、战斗牌堆选择、普通牌组选择、普通手牌选择以及手牌升级选择。[休息处锻造](rest-site.md#锻造与烹饪选牌)的牌组升级使用 `deck_upgrade`，`upgrade_previews` 提供已经显示的单牌或多牌比较。牌组变牌、附魔、卡牌包和结果确认已接通，见下节。其他尚未接通的页面返回 `unsupported`，不提供动作；战斗与通用选择把它作为已识别边界返回 `choice_required`，[搜刮动作](rewards.md) 则返回 `manual_input_required`；任意第三方页面仍需额外适配。静态遮挡按已核实的原生页面判断，不能保证覆盖任意像素级遮挡。声音、其他游戏版本与完整自动游玩不属于已验证范围。

手牌升级的真实图形 MCP 回归须使用新建的隔离实例：先按[构建与运行](roundtrip.md)准备目录，运行 `python3 scripts/run_roundtrip.py --windowed --play-scenario armaments`，再在另一终端运行 `.tmp/mcp-venv/bin/python scripts/verify_hand_upgrade.py --report .tmp/upgrade-check/run.json`。报告目录不能复用已有截图文件。检查会出牌、选牌、取消、切换视图并确认，不能指向正式对局。

标准库文件客户端支持相同操作：`select_card --card-id 7 --expected-state <令牌>`、`selection_option --option-id confirm --expected-state <令牌>`，以及 `set_selection_view --view battlefield`；这些参数与既有 `--ipc-dir` 一起使用。原始令牌通过 `get_state --raw` 获取，MCP 客户端由会话内部管理。

## 附魔、变牌、卡牌包与结果确认

- `deck_enchant` 复用 `select_card`；`enchantment` 是已显示的附魔名称和正文，`enchant_previews` 是当前实际比较，未展开时为空列表。两侧 ID 都引用已选原牌。原生多张附魔确认页可能只显示原牌，不虚构附魔后的比较；附魔说明仍单独返回。`cancel_preview` 返回候选，`confirm` 才实际提交。
- `deck_transform` 提供 `transform_previews`，每项含 `before`、`after`、`random`。原生随机轮换卡面属于结果示意，归一化为 `random:true, after:null`；它不表示提前抽到的结果。确定变化（如变成指定牌）可提供当前可见 `after`。两侧 ID 只关联原牌，不能当作新候选。确认后按游戏自身随机流程处理。
- `bundle` 的 `bundles` 保留卡牌包及其 `id` 和可见卡牌；未展开时仅摘要，显式详情可读当前卡牌包的完整牌面。使用 `selection_option` 点击列出的 `bundle:N`，再用 `confirm` 或 `cancel_preview`。不通过 `select_card` 单取包中一张牌；`min_select/max_select` 为包的数量范围。展开后 `cards` 提供选中包的真实牌面。
- `view_cards` 是潘多拉魔盒等已经完成变化后的结果页，不是再次选牌。使用列出的 `confirm` 关闭；不能点击其中卡牌当作选择。

覆盖页会隐藏以上附加信息。没有进入原生选牌时不强行创建界面，例如合法附魔候选不足原生数量时，游戏可能直接处理。先古之民领取效果复用这些工具，不为每件遗物复制工具。
