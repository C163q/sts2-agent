# 选牌接口设计与源码依据

核对基线：Linux 游戏 `v0.107.1`，程序集 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；RitsuLib `0.6.10`。反编译证据保存在不入库的 `.tmp/2026-10-30-selection/`。本文件描述本次实施要求，当前能力另见持续维护接口文档。

## 已核实的流程

- `CardSelectCmd.FromChooseACardScreen` 用于最多三个候选；药水允许跳过，`KnowledgeDemon.ChooseCurse` 不允许跳过。候选卡片已经显示完整正文，基础观察可以提供正文，悬停解释仍通过详情读取。
- `NCardRewardSelectionScreen` 独立于上述页面；非卡牌按钮来自 `CardRewardAlternative.Generate`，除 Skip 外还可能有重掷和献祭。不能把所有非卡牌按钮都解释为跳过。`BrainLeech.Rip` 使用这种奖励流程。源码注释还举过捕梦网治疗，但该例未获实际生成逻辑支持；更正依据见[selection_option 核验](2026-11-05-selection-option-development-notes.md#奖励按钮名称与旧注释)。
- `NSimpleCardSelectScreen` 读取 `CardSelectorPrefs` 的数量上下限、手动确认规则。`RoomFullOfCheese.Gorge` 为八选二，`BrainLeech.ShareKnowledge` 为五选一。`ChoicesParadox.AfterPlayerTurnStart` 在第一回合生成五张候选，选一张并保留；它不是回合结束后的专属流程。
- `NPlayerHand.SelectCards` 管理手牌选择。`TyrannyPower` 要求消耗；`WellLaidPlansPower.BeforeFlushLate` 允许选零到指定数量。`Cancelable` 不意味着每种页面都会显示跳过按钮；以原生按钮为准。
- `NPeekButton` 隐藏选牌内容并切换原生 backstop；`NPlayerHand.OnHolderPressed` 在 peeking 时直接拒绝操作，`AreCardActionsAllowed` 也检查此状态。小型候选页和简单网格页在 peeking 时启用自己的 `NCombatPilesContainer`。
- `NDeckCardSelectScreen` 还有选择后预览与最终确认阶段；不能把预览的取消误认为放弃整个选择。升级、变化和附魔页具有各自的专门预览，本次不将它们套用普通选择的动作规则。

## 接口决定

保留现有工具并新增四个：

1. `inspect_selection`：读取当前选择中整个可浏览候选列表及悬停解释；不切换到战场，不读取尚未生成的结果。
2. `select_card(card_id)`：等价于点击一张候选，单选会提交，多选会选择或取消该项。原生需要确认时保留确认阶段。
3. `selection_option(option_id)`：点击观察中列出的启用按钮，涵盖确认、预览取消、跳过和奖励替代选项；不能通过空牌列表伪造跳过。
4. `set_selection_view(view)`：显式点击眼睛，`view` 为 `battlefield` 或 `selection`。保留原生选择和已选项目，查看战场不会使普通战斗动作合法。

`get_observation` 新增可空 `selection`：类型、当前可见阶段、提示、数量规则、可见候选、已选项、可见按钮以及眼睛入口。战场查看阶段不返回已隐藏的候选正文。网格基础观察只包含当前画面可见卡牌，整个可浏览列表由显式详情提供。手牌选择复用战斗卡牌 ID，基础手牌不自动展开正文。

普通查看工具仍以实际 UI 可用性判断；战场查看可使用手牌、双方状态及界面说明等已有工具。牌堆必须点击当前选择界面启用的入口。关闭牌堆返回原生保留的查看状态；返回选牌须显式调用 `set_selection_view`。视图切换清除 MCP 动作许可，提交选择前必须重新观察。普通选牌页不自动打开战场。

选牌动作沿用状态令牌、请求去重与单连接控制；令牌包含不携带隐藏信息的选择实例代际，防止连续外观相同的选择复用旧令牌。每次只提交一个原生输入，不直接填写游戏的选择结果或修改牌组。提交后记录可感知事件，等待下一个选择、玩家可行动、胜负或超时；非战斗选择完成以 `selection_resolved` 停止。

初期覆盖小型候选、奖励、简单网格、战斗牌堆选择、普通牌组选择和手牌普通选择。专门的升级、变化、附魔和卡牌包选择明确返回未支持状态，不能绕过其界面。测试环境可以构造初始场景，正式接口不能触发这些测试入口。

## 验证要求

边界测试覆盖隐藏候选、嵌套额外字段、残缺响应、参数类型、过期令牌和动作不重试。独立游戏验证药水可跳过、强制二选一、奖励按钮、八选二、五选一、暴政、计划妥当零选与保留、第一回合选择悖论；验证眼睛切换、查看工具、牌堆关闭后的状态、原生选择继续执行。图形实例核对截图。只编译通过不表示已通过实际行为验证；不能操作用户正式对局来构造测试场景。
