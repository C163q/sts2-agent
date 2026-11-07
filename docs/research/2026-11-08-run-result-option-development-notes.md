# run_result_option 开发核验

## 基线与证据

核验日期2026-11-08，代码基线f033e359e873a0a62a07afde1b90f376617ac00b，Mod0.79.0、MCP0.81.0、schema47；Linux游戏v0.107.1、release59260271，RitsuLib0.6.10。参数和行为建议见[审阅报告](2026-11-08-run-result-option-review.md)。

本地证据根目录为`.tmp/2026-11-08-run-result-option-review/`。目标程序集`data_sts2_linuxbsd_x86_64/sts2.dll`的SHA-256为`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；隔离运行DLL与当前构建产物一致，SHA-256为`42e7a81c122c9ac3feb07366934f08c072527c4e14d4856c0b999c018fcf5672`。未重新构建、安装Mod或升级游戏。

## 实现与原生路径

| 职责 | 当前入口与结论 |
| --- | --- |
| 注册与参数 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)的run_result_option使用OPTION_SCHEMA，default/full、要求许可、记录事件并返回transition；未启用unsubmitted_rejection_unchanged。 |
| 参数校验 | [run_ending_details.py](../../src/sts2_mcp/output/run_ending_details.py)的option_arguments仅接受option_id，字符串须完整匹配标识规则；Python先剥离通用preset。底层[RunResultRequest](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs)另核对参数及expected_state。 |
| 结算上下文 | [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)跟踪本局NGameOverScreen和离开结算后关联的时间线菜单栈；回到主菜单、关联栈退出后清理，普通菜单时间线不属于该上下文。 |
| 操作条件 | Ready核对单人、Exposed、DisplayComplete、时间线InputBlocker及至少一个可点击按钮；Options与Clickable再核对单项。[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)使用相同Ready。 |
| 执行 | NEpochSlot在画外时先调用NSlotsContainer.LerpToSlot并重查上下文／按钮；随后UiChanged。上一章／下一章发MouseReleased，其余ForceClick，沿原生信号处理。 |
| 停止边界 | ActionObservation等待[NonCombatBoundary](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs)，includeRunOutcome:false；返回主菜单单独判断。TransitionSuccess及共用[action_result](../../src/sts2_mcp/output/action_output.py)生成精简回执。 |

原生NGameOverScreen.OpenSummaryScreen分阶段显示计分、徽章、进度和发现，最终启用按钮。OnMainMenuButtonPressed根据DiscoveredAnyEpochs进入时间线或返回主菜单；View Run在此目标版本未被启用。NTimelineScreen按原生队列提供教程、章节故事和多种解锁屏幕，关闭章节时先处理排队解锁，再恢复时间线。不能只根据按钮ID为main_menu就判断已退出。

目标版本源码保留在证据目录source/：NEpochSlot、NSlotsContainer、NRunHistory和NSubmenu已重新反编译；NGameOverScreen、NTimelineScreen、NEpochInspectScreen从同一程序集基线的既有证据复制。上游源码和程序集均不提交。

## 三项问题的根因

### 拒绝后丢失已有许可

RunResultRequest的参数、页面和按钮拒绝均使用FileMailbox.Error；除过期状态外，明确点击前拒绝也没有action_submitted:false或ui_unchanged保证。注册项未启用未提交恢复，[game_session.py](../../src/sts2_mcp/game_session.py)因而无法保留此前许可。实测错误房间的execution.ui_interaction_started和action_submission_observed均false，前后snapshot一致，后续end_turn仍被observation_required阻挡。

不能仅凭错误名一律恢复。NEpochSlot路径在UiChanged前已经可能执行2.5秒滚动；若增加明确拒绝保证，必须把首次交互标记移到滚动之前，区分滚动前和滚动后拒绝。过期、已交互、不确定、坏响应继续清除许可。

### 公开错误丢失具体原因

当前将无上下文、覆盖和未就绪合并为“The run result is unavailable.”，缺失／禁用按钮另返“The requested result button is unavailable.”；这些消息没有public_message，[error_output.py](../../src/sts2_mcp/output/error_output.py)统一替换为“The requested action is unavailable.”。因此等待、选择其他按钮和读取另一场景无法区分。

整改应在现有RunResultInspection内整理操作级和单项拒绝原因，继续复用既有原生按钮。详情工具已有独立InspectionUnavailableReason，不能把允许部分读取的条件拿来放宽操作。

### 已揭晓章节被排除

RunResultInspection.Options只遍历State==Obtained的NEpochSlot。目标程序集NEpochSlot.OnRelease实际分两条：Obtained调用RevealEpoch并转Complete；Complete调用OpenInspectScreen(playAnimation:false)，支持重新阅读。后者进入NEpochInspectScreen.Open时会RefreshChapterPaginators，而首次揭晓的UnlockAnimation会HidePaginators。因此当前仅支持揭晓的选项范围也阻断了正常重新阅读及章节翻页路径。

建议Options同时考虑已显示且原生允许操作的Obtained／Complete条目，保留epochIds作为同一时间线对象的稳定ID。按钮文字区分揭晓和查看；enabled仍使用真实原生条件，不把NotObtained变成可点击项。关联范围维持本局结算。

## 本局详情夹具与崩溃证据

[BrowsableContentChecks.PrepareHistory](../../src/Sts2Agent/Testing/Checks/BrowsableContentChecks.cs)使用NRunHistory.AssetPaths[0]创建普通run_history页面，直接over.AddChild，调用DisplayRun并启用BackButton；没有SetStack。目标程序集NSubmenu.ConnectSignals将BackButton.Released连至_stack.Pop，普通页面依赖菜单栈。原生NGameOverScreen.OpenRunHistoryScreen指定的资源则是run_history_screen_via_game_over_screen.tscn，不能把两者的读取相同视为返回流程相同。

gui-suite-fixed的history_back公开结果为timeout/outcome:unknown，未收到原生响应文件；游戏stdout记录`Invalid Program: attempted to call a UnmanagedCallersOnly method from managed code.`，堆栈经过GodotObject.EmitSignal、NClickableControl.ForceClick和RunResultRequest。源码确认夹具的原生返回依赖未初始化；这份致命堆栈不足以证明正常原生结算入口也会崩溃，更不能等同此前致死斗篷的根因。保留失败证据，建议实施时先修正夹具再核验。此次未强制启用View Run、未添加原生状态绕过。

## 验证记录

26项相关Python检查通过，0.796秒，见python.log。运行模块为test_run_ending、test_result_inspection_presets及test_run_result_summary；日志中的坏响应警告来自预期拒绝用例。

GUI按实际完成的检查点统计，不把中途失败的整份报告计为通过：

| 检查范围 | 结果与证据 |
| --- | --- |
| 战斗误用、冷调用与本地参数错误 | gui-suite-fixed/basic完整通过。无许可动作被拒绝；误用后丢失许可已复现；省略ID、null、数字、负数ID、尾换行、额外字段和不支持的summary被本地拒绝，之后直接end_turn成功。 |
| 胜利结算及终局许可 | gui-victory中实际continue成功进入summary；该脚本此前已经读取，却错误预期observation_required，因此整体失败。gui-victory-fixed调整顺序后，真实run_won后未读取的动作正确被拒绝；建筑师及胜利首屏真实路径正常。 |
| 未知选项、展示中、按钮全部禁用 | gui-victory-fixed及gui-death分别核验。partial通过既有PresentationFixture制造有限展示状态，disabled禁用按钮；公开错误均笼统、未交互、前后snapshot一致，下一次操作仍要求观察。恢复夹具后读取和原生动作正常。 |
| 过期状态 | 上述两次运行用原生continue模拟外部操作，旧许可收到stale_state，随后需要观察；没有错误恢复旧许可。 |
| 未提供的View Run | gui-death确认summary的options不含view_run，点选拒绝；随后main_menu受观察前置要求阻挡。gui-victory-fixed此前错误假定会出现禁用条目，在该断言处停止，保留失败报告。 |
| 教程、时间线、章节、解锁确认、返回主菜单 | gui-death完整走到scene:main_menu。所有这些动作均action_completed、complete:true、events:[]；两次epoch继续后均未读取便直接default confirm成功。 |
| 已揭晓章节 | gui-death的completed_epoch_unavailable：此前成功揭晓的同一epoch ID仍在hover_tips来源中，但options已不包含；原ID点击被拒绝，随后合法操作也要求观察。尚未补鼠标重新点选实测，原生支持由本次重新反编译的OnRelease分支证明。 |
| 主菜单与无关联时间线 | gui-menu完整通过。主菜单读取后调用continue拒绝；打开普通菜单时间线仍为scene:main_menu、run_result:null，调用back拒绝，没有误认成本局结算。 |
| 本局详情返回 | gui-suite-fixed/history准备和读取成功，back导致进程致命退出、公开timeout；仅证明不匹配的普通历史页夹具失败，见前节。 |

另保留两处准备／预期失败：gui-suite忘记向已有测试局传复用标志，在准备阶段失败，没有执行玩法核验；gui-death到达主菜单后又读取了状态，却仍预期下一动作observation_required，实际为正确的illegal_action。后者没有重跑已通过的整段解锁链，只以新gui-menu补测剩余菜单边界。未修改产品以迎合脚本断言。

六个自有游戏进程109757、110149、110716、111272、111642、111980及各自验证子进程均已退出。运行耗时分别为35.664、130.951、63.277、65.489、72.860、21.669秒。原始失败日志及响应保留，没有改写成成功。

[典型JSON](2026-11-08-run-result-option-examples/README.md)共15份，14份full、1份default，全部为实际MCP返回，保留完整字段。manifest记录调用参数、原始行号、原生响应文件及内容SHA-256；包含失败脚本中已完成的单次调用时明确标记，不冒充整体通过。展示卡牌及物品的结算内容仍使用此前已验收的读取规则。

evidence-verification.json再次核对15份样例与实际返回逐项相等、7份成功原生响应重放一致、185个相对文件链接存在，以及6个游戏／7个验证进程全部退出；同时校验上述拒绝、连续确认和实际菜单回执的证据。这个检查证明已记录的审阅事实，不把失败GUI报告改为通过。

未新增GUI验证：重新阅读已揭晓章节和章节翻页、正确结算内详情资源的返回、每日挑战榜单、多人、第三方页面、所有角色与全部随机解锁组合，以及滚动途中上下文变化。既有成功胜利完整解锁证据为同一DLL的`.tmp/2026-11-08-result-inspection-status/review-fix-victory/`，此次未重复全量结算回归。没有增加TODO项，未更改版本、产品代码或正式安装。
