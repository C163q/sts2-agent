# 选牌与查看战场

适用于 Mod／MCP `0.46.0`、schema `27`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。[搜刮工具](rewards.md) 负责打开奖励入口，这些接口操作已经打开的原生选牌界面，不负责点击事件选项；[出牌工具](card-play.md) 和 [药水工具](potion-actions.md) 可触发后续选择。通用接口依据见 [选牌设计](../research/2026-10-30-card-selection-design.md)，手牌升级依据见 [补充调研与验证](../research/2026-10-30-hand-upgrade-selection.md)。

## 观察与信息范围

`get_observation`、动作回执和 `inspect_selection` 中的 `scene` 均表示同一个底层房间或战斗，不随选牌类型改变。例如涅奥牌包选择仍为 `scene:"ancient"`，火堆锻造仍为 `scene:"rest_site"`；当前选择由 `selection.type/status` 表达。`inspect_selection` 默认只扩展当前选择的详情；显式 `view_upgrades` 可切换当前页的升级复选框，不打开其他页面。[一致性验证记录](../research/2026-11-01-selection-scene.md)包含底层场景的验证范围。

底层文件及 MCP full 的 `selection` 在没有选择时为 `null`；有选择时包含：

| 字段 | 含义 |
| --- | --- |
| `type` | `choose_one`、`reward`、`grid`、`combat_pile`、`deck`、`hand`、`hand_upgrade`、`deck_upgrade`、`deck_enchant`、`deck_transform`、`bundle`、`view_cards` 或 `unsupported` |
| `status` | `visible` 为选牌页面；`battlefield` 为点击眼睛后查看战场；`covered` 为被其他页面覆盖；`unsupported` 为尚未接通的选择类型 |
| `prompt`、`min_select`、`max_select` | 当前选择提示与数量范围；隐藏时为 `null` |
| `cards` | 当前画面可见候选，包含稳定整数 `id`；已经展开显示的牌面可附正文，手牌摘要不自动展开正文 |
| `selected_ids` | 当前已选项目；隐藏时为 `null` |
| `options` | 当前显示的按钮及 `id`、英语 `text`、`enabled`；未启用不能点击 |
| `can_view_battlefield` | 原生眼睛当前可用，可显式切换视图 |
| `can_view_upgrades` | 当前页的原生升级复选框可见、启用且未被确认预览覆盖 |
| `view_upgrades` | 候选列表当前实际的升级预览状态；选择隐藏时为 `null`，没有该模式时为 `false` |
| `upgrade_previews` | 仅 `deck_upgrade` 提供；已经显示的单牌或多牌升级比较，未进入预览或隐藏时为空列表 |
| `upgrade_preview` | 仅 `hand_upgrade` 提供；已显示的升级前后牌面 `before`、`after`，未选择或隐藏时为 `null` |

`cards` 在查看战场、被覆盖或未支持时为 `null`，与没有候选的空列表不同。网格可能滚动，基础观察不补齐屏幕外候选；`inspect_selection()` 默认显式读取整个可浏览候选列表、正文及共享 `hover_tips`，不会展开尚未生成的结果。省略 `view_upgrades` 时不改变 UI。共享解释通过整数 `card_ids` 引用候选。手牌选择沿用战斗手牌 ID，升级预览的克隆仍使用原牌 ID。

基础观察和查看结果按情境附简短 `notes.selection`：选择遮挡时提示用眼睛查看战场；查看战场时提醒仍有选择待完成，须返回选择界面；牌组、牌堆或地图覆盖选择时提醒先关闭当前查看页。这些说明不重复候选正文或按钮列表。

## MCP 输出预设

默认空值过滤见[公共规则](mcp.md#输出预设)：已展开比较的 before / after 两侧完整保留；未展开或被筛选掉的整个 `upgrade_preview:null` 可以省略。下文原有空值说明适用于 full 与 summary。

`inspect_selection` 接受以下可选参数。省略或传 `{}` 保持完整详情及当前 UI 模式，使用 default 省略普通空值。`preset` 和 `card_ids` 在 Python 投影，底层文件协议只接受可选的 `view_upgrades`；本次升级预览及观察修复需同时更新 DLL／清单和 Python，完整重启游戏并重连 MCP。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `default` | `default` 保留完整内容并省略普通空值；`full` 保留原有空值；`summary` 使用手牌摘要字段 |
| `card_ids` | 省略 | MCP `0.42.0` 起支持当前选择中的非负整数卡牌 ID 数组；省略返回全部，`[]` 不返回卡牌详情，重复 ID 去重，结果保持原生顺序 |
| `view_upgrades` | 省略 | 可选布尔值，真实点击原生复选框；`true` 查看升级、`false` 恢复原牌，省略保留当前模式 |

```json
{"preset": "summary", "card_ids": [1, 2, 3], "view_upgrades": true}
```

`summary` 的每张卡牌沿用[手牌摘要字段](hand-inspection.md#参数与返回范围)：保留身份、费用、可见附魔及卡面标记，移除正文、稀有度、卡池和悬停帮助；没有星耗时不输出该项。规则统一作用于 `cards`、`bundles[].cards`，以及 `upgrade_preview`、`upgrade_previews`、`enchant_previews`、`transform_previews` 的 `before/after`；预览也不保留正文，需要时另读 `full`。

当前已知缺口：普通网格候选的完整读取分支尚未输出卡牌已有的 enchantment，因而该分支的 summary 也无法保留它；手牌、包内容及节点比较不受此分支影响。已列入[候选范围与摘要调整](../research/2026-11-02-get-observation-selections.md#完整候选读取的附魔缺口)的后续修复与实测，当前尚未修复。

摘要保留场景、选择类型和状态、提示、数量限制、已选 ID、按钮、包 ID、升级模式、随机变牌标记及原有空值。选择级 `selection.enchantment` 仍保留附魔操作名称与说明，它描述当前要执行的操作。不会补全未知卡牌或随机变牌结果；预设及筛选本身不改变候选范围和 UI。读取成功后可直接选择；仍先验证完整原生详情，再投影为摘要，错误不会被转为空结果。非法参数不发往游戏，也不丢弃已有动作许可。

`card_ids` 同时筛选 `cards`、`bundles[].cards` 和已经展开的预览。预览按原牌 `before.id` 命中，保留整组 `before/after`，不生成尚未展开的比较或随机结果；未命中的 `upgrade_preview` 为 `null`，列表预览移除对应项。包 ID 保留，包内 `cards` 可为空；查看包内某张牌不改变整包选择方式。full 的共享提示同步裁剪卡牌关联，summary 继续不提供悬停效果。

筛选仅限制返回的卡牌详情，提示、数量限制、**全部** `selected_ids`、按钮和选择级附魔说明保持完整；因此过滤结果中的空列表或 `null` 不表示原生页面没有候选或预览。结果确认页的牌也可筛选，但不会因此变成可点击候选。ID 仅在本次可浏览详情及已展开预览中匹配，不查询其他牌堆或隐藏页面。

无效 ID 按请求首次出现的顺序合并报告，有效卡牌照常返回：

```json
{"errors": [{"code": "cards_not_in_selection", "card_ids": [80, 70]}]}
```

此时 MCP `isError` 为 `false`，客户端须检查 `errors`；没有无效 ID 时省略它。参数校验与 `inspect_hand` 相同：ID 为 0 至 2147483647 的整数，不接受布尔值、浮点数、字符串或 `null`。空筛选和混合错误仍验证完整底层详情并刷新动作许可；原生读取失败保持顶层 `error`，不转换为卡牌缺失。测试范围见[筛选实现记录](../research/2026-11-02-selection-filters.md)。

## 候选升级预览

火堆及事件等牌组升级选择 `deck_upgrade`、牌组变形选择 `deck_transform`，以及潘多拉魔盒等结果页 `view_cards` 提供原生升级复选框。以当前 `can_view_upgrades` 为准；控制器模式隐藏的控件、确认预览背后的控件都不能强行点击。其他选择页没有该开关，例如卡牌奖励、普通移除和附魔；手牌升级已有的选中前后比较保持原有行为。

显式传入 `view_upgrades` 后，等待 UI 稳定再返回新状态和令牌，页面保留本次模式。`cards` 的名称、费用、正文与当前普通／升级牌面一致；仅预览可升级卡牌，原本不能升级的牌保持原样。ID 仍指向原牌，不能将预览克隆当成额外候选。不会实际升级、选择或确认卡牌，也不会改变当前选中项。既有 `upgrade_previews` 和随机变牌比较独立保留，不因候选升级模式而生成未来结果。

当前没有可操作的升级复选框时，保留当前数据并附 `errors:[{"code":"upgrade_view_unavailable"}]`，MCP `isError:false`。若同时有筛选错误，两项依次合并；仍按本次 `preset`、`card_ids` 返回有效数据。不传该参数不会产生此错误。选择已被隐藏或切换时仍返回顶层 `illegal_action`，不返回隐藏候选。

标准库客户端可使用 `inspect_selection --view-upgrades` 或 `--no-view-upgrades`。实现依据和验证范围见[选牌升级预览记录](../research/2026-11-02-selection-upgrades.md)。

## 操作

`select_card({"card_id": 7})` 等价于点击一张候选。多选界面会选择或取消该项，单选界面可能立即提交；原生需要确认时必须再调用 `selection_option`。它不直接更改牌组，不绕过选择结果的网络同步，不替代正常结算。

`selection_option({"option_id": "confirm"})` 点击观察中列出的启用按钮。可能出现 `skip`、`confirm`、`cancel_preview`、`cancel` 或奖励 `alternative:N`；含义以当前 `text` 为准。预览取消与放弃整个选择分别处理。奖励替代选项还可能是治疗、献祭或重新生成，不能一律视为跳过。允许选零张的手牌选择通过原生确认按钮提交空选择。

两类动作使用当前观察许可，可以来自基础观察、专项详情、视图操作或满足续接条件的成功动作结果，具体条件见[MCP 动作许可](mcp.md#调用和错误语义)；失败后须重新观察。`inspect_selection` 成功时刷新状态令牌，可直接选择已读取的候选。原生滚动候选由工具先定位再点击，定位期间若选择已经改变则拒绝输入。选择实例代际参与底层令牌，防止外观相同的连续选择复用旧许可。

## 卡牌奖励替代按钮

`selection.type: "reward"` 的替代按钮由原生奖励实际生成，在基础观察及 `inspect_selection` 的 `selection.options` 中提供相同的 `id/text/enabled`。除 `skip` 外使用 `alternative:N`，通过 `selection_option` 点击；编号是当前页面的位置，不代表固定效果，须结合本次 `text` 判断。

| 遗物 | 当前按钮文字 | 行为 |
| --- | --- | --- |
| 佩尔之翼 `PaelsWing` | `Sacrifice` | 消耗这一份卡牌奖励，不加入卡牌；每两次献祭由原生流程获得遗物 |
| 浮木 `Driftwood` | `Reroll` | 当前奖励重新生成候选，不加入卡牌；每份奖励可重掷一次，使用后按钮消失，跳过后重新打开同一奖励也不恢复次数 |

重掷后的卡牌使用新的当前候选 ID；从观察或详情读取后操作，不复用旧候选或已经消失的替代按钮。献祭获得遗物时，普通完成还等待遗物入栏和佩尔之翼的计数动画结束；遇到原生后续选择仍先返回输入边界，不等待依赖选择的父任务。分别持有两个遗物时的实测、截图及组合边界见[验证记录](../research/2026-11-01-reward-alternatives.md)。

## 手牌升级

武装等触发的 `hand_upgrade` 复用以上工具。`cards` 只列原生筛选后可见的手牌和已经选中的原牌，不混入升级结果克隆；选择前不生成升级结果。`select_card` 选中后停在 `choice_required`，通过 `inspect_selection` 按需读取 `selected_ids` 和已经显示的 `upgrade_preview`。`before`、`after` 两侧包含牌名、费用与展开的正文，`id` 都是原手牌 ID。它们是同一张牌的比较，不能当成额外的可选牌。

再次点击已选 ID 等价于点击预览左侧原牌，取消选择；点击其他候选等价于改选，预览随之替换。只有点击启用的 `selection_option({"option_id":"confirm"})` 才提交选择并继续实际升级。未选择时原生确认按钮可能完全隐藏，以 `options` 为准，不自动确认。眼睛和覆盖页隐藏候选与预览，返回后保留待确认选择。

可升级手牌不足两张时，本版本 `CardSelectCmd.FromHandForUpgrade` 可能直接选择唯一候选或不做选择，工具应直接等待后续结算，不人为创建界面。已经升级的武装也沿用游戏自身的全手牌升级流程。

## 眼睛与现有查看工具

调用 `set_selection_view({"view":"battlefield"})` 点击原生眼睛。此后基础观察及 `inspect_hand`、`inspect_combatants`、`inspect_ui`、药水、遗物详情按当前可见性工作；牌组、地图和牌堆还要求各自原生入口可用。小型候选和简单网格使用其自己的牌堆入口，不能强行点击被禁用的战斗按钮。

查看战场不允许出牌、结束回合或直接选隐藏的候选；`available_actions` 列出当前可用的战场详情、页面查看及 `set_selection_view` 返回入口。`close_card_view` 只关闭牌组或牌堆，保留底层选择与原有查看状态；地图由 `close_map` 关闭。关闭覆盖页后，调用 `set_selection_view({"view":"selection"})` 返回候选。返回候选的成功视图结果可以直接续接选择；普通观察和只读详情都不会自动切换眼睛。

## 动作后的结算

选牌动作与 `end_turn` 使用同一可感知事件记录，返回[精简动作回执](mcp.md#动作返回格式)。点击多选但尚未确认时停在 `choice_required`；真正提交后等待后续选择、玩家可行动、胜负或超时。非战斗选择回到[通用事件](events.md)、[先古之民](ancients.md)、商店、宝箱房、搜刮或[休息处](rest-site.md)时使用 `action_completed`；父事件的异步效果、卡牌预览和资源动画仍须完成。其余非战斗选择完成使用 `selection_resolved`。事件字段、`complete` 和超时恢复规则见 [结束回合](end-turn.md)。连续选择每次单独操作，不自动代选，也不会因等待期间出现下一次选择而一直挂起。

选择状态直接来自界面，不要求已经完成过一次回合。选择悖论在第一回合开始时也可识别并操作。暴政消耗和本版本计划妥当保留手牌使用同一手牌接口。

当前接通小型候选、卡牌奖励、简单网格、战斗牌堆选择、普通牌组选择、普通手牌选择以及手牌升级选择。[休息处锻造](rest-site.md#锻造与烹饪选牌)的牌组升级使用 `deck_upgrade`，`upgrade_previews` 提供已经显示的单牌或多牌比较。牌组变牌、附魔、卡牌包和结果确认已接通，见下节。其他尚未接通的页面返回 `unsupported`，不提供动作；战斗与通用选择把它作为已识别边界返回 `choice_required`，[搜刮动作](rewards.md) 则返回 `manual_input_required`；任意第三方页面仍需额外适配。静态遮挡按已核实的原生页面判断，不能保证覆盖任意像素级遮挡。声音、其他游戏版本与完整自动游玩不属于已验证范围。

手牌升级的真实图形 MCP 回归须使用新建的隔离实例：先按[构建与运行](roundtrip.md)准备目录，运行 `python3 scripts/run_roundtrip.py --windowed --play-scenario armaments`，再在另一终端运行 `.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_hand_upgrade --report .tmp/upgrade-check/run.json`。报告目录不能复用已有截图文件。检查会出牌、选牌、取消、切换视图并确认，不能指向正式对局。

标准库文件客户端支持相同操作：`select_card --card-id 7 --expected-state <令牌>`、`selection_option --option-id confirm --expected-state <令牌>`，以及 `set_selection_view --view battlefield`；这些参数与既有 `--ipc-dir` 一起使用。原始令牌通过 `get_state --raw` 获取，MCP 客户端由会话内部管理。

## 附魔、变牌、卡牌包与结果确认

- `deck_enchant` 复用 `select_card`；`enchantment` 是已显示的附魔名称和正文，`enchant_previews` 是当前实际比较，未展开时为空列表。两侧 ID 都引用已选原牌。原生多张附魔确认页可能只显示原牌，不虚构附魔后的比较；附魔说明仍单独返回。`cancel_preview` 返回候选，`confirm` 才实际提交。
- `deck_transform` 提供 `transform_previews`，每项含 `before`、`after`、`random`。原生随机轮换卡面属于结果示意，归一化为 `random:true, after:null`；它不表示提前抽到的结果。确定变化（如变成指定牌）可提供当前可见 `after`。两侧 ID 只关联原牌，不能当作新候选。确认后按游戏自身随机流程处理。
- `bundle` 的 `bundles` 保留卡牌包及其 `id` 和可见卡牌；未展开时仅摘要，显式详情可读当前卡牌包的完整牌面。使用 `selection_option` 点击列出的 `bundle:N`，再用 `confirm` 或 `cancel_preview`。不通过 `select_card` 单取包中一张牌；`min_select/max_select` 为包的数量范围。展开后 `cards` 提供选中包的真实牌面。
- `view_cards` 是潘多拉魔盒等已经完成变化后的结果页，不是再次选牌。使用列出的 `confirm` 关闭；不能点击其中卡牌当作选择。

覆盖页会隐藏以上附加信息。没有进入原生选牌时不强行创建界面，例如合法附魔候选不足原生数量时，游戏可能直接处理。先古之民领取效果复用这些工具，不为每件遗物复制工具。
