# proceed 开发核验依据

> 当前状态：修复已实现、验收并合入main。本文保留a8b85aa提交前的核验依据与失败证据；后续实现见[实施记录](2026-11-06-proceed-recovery-implementation.md)。用户可读结论见[审阅记录](2026-11-06-proceed-review.md)。

## 基线与证据

- 项目8d7da3b；Mod0.71.1、MCP0.73.1、schema41。
- 核对日期2026-11-06；Linux游戏v0.107.1／release59260271，RitsuLib0.6.10。游戏安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时DLL均da9c1c694042b244cf5672eb4231db8048eac3b5337f84f27c33a572d3249331；未重建、更新版本或正式安装。
- 原始证据根`.tmp/2026-11-06-proceed-review/`。一般场景复用隔离进程，终章另用EndingFixture.victory与全新进度的独立进程，未放宽suite的ending禁用约定。

## 问题清单

| 编号 | 优先级 | 证据与影响 | 状态 |
| --- | --- | --- | --- |
| PROCEED-01 | 中 | 八条分支的明确点击前拒绝没有未交互证明，spec没有unsubmitted_rejection_unchanged；GUI拒绝后合法动作被MCP观察前置拦截 | 待讨论修复 |
| PROCEED-02 | 中 | 原因被合并且未设置public_message，分发/可用列表/执行各自维护判断；GUI均公开笼统错误 | 待讨论修复 |
| PROCEED-03 | 低 | verify_run_ending.py:82断言终局available_actions为空，与实际保留只读工具矛盾 | 源码及实际响应确认，旧脚本尚未修复 |

## 分发、可用性与等待

[RequestDispatcher.cs](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)先处理当前建筑师；随后各分支在没有RewardInspection.Current时按Ancient、Divination、Event、Shop、Treasure、RestSite选择，余下proceed落入RewardRequest。对应实现位于GameAdapter.RunEnding/Ancient/Divination/Event/Shop/Treasure/RestSite/Rewards.cs。

[GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)分别用各类Ready、按钮及Clickable判定提供proceed；地图覆盖和结算等场景再裁剪玩法动作。当前未发现已测正常入口的可用列表与合法点击相矛盾，但检查分散在分发、列表与执行多处。

各分支在UiChanged之后ForceClick，通常以NonCombatBoundary等待。EventRequest同时使用当前CombatJournalScope；建筑师使用EpilogueInspection.Button并核对IsProceed，禁止把对话中段按钮当proceed。奖励页以claim/skip信号等条件区分完成，proceed行目标为空时直接等待下一边界。ToolSpec为action/requires_permission，接收零原生参数，返回经过完整校验的actions_only加transition。

## 目标版本原生资料

- `.tmp/2026-10-31-rewards/source/Nodes.Screens.NRewardsScreen.cs`的OnProceedButtonPressed：终结普通奖励打开地图，Boss分支设置本地换幕就绪；非终结奖励SkipLocalRewardsSet并移除当前overlay。
- `.tmp/2026-10-31-treasure/source/NTreasureRoom.cs`的OnProceedButtonPressed：Skip时先SkipRelicLocally，单人再开启地图；不是以领取代替跳过。
- `.tmp/2026-10-31-rest-site/source/NRestSiteRoom.cs`的ShowProceedButton/OnProceedButtonReleased：按原生状态启用并打开地图。
- `.tmp/2026-10-31-events/source/NEventLayout.cs`、NEventOptionButton.cs及`.tmp/2026-10-31-ancients/source/NAncientEventLayout.cs`：事件完成按钮与对白/选项流程。项目EventInspection额外核对IsFinished、TextKey:PROCEED及非CurrentOptions身份，普通选项不归入proceed。
- `.tmp/2026-10-31-divination/source/NCrystalSphereScreen.cs`：初始化禁用前进，OnMinigameFinished才显示并启用；OnProceedButtonPressed进入原生前进。
- `.tmp/2026-10-31-run-ending/source/TheArchitect.cs`：最后一行生成PROCEED选项，执行WinRun；对应RunManager.ProceedFromTerminalRewardsScreen区分打开地图和ResumePreviousRoom，后者等待父房间Resume。

第三幕最后Boss和建筑师末尾已经实际验证；普通事件战斗奖励触发父事件Resume分支只核对源码。Battleworn Dummy样本中play_card已返回scene:event/combat_won，不能将后续proceed描述为触发了恢复。

## PROCEED-01／02：拒绝与共用入口

所有分支的stale_state保持原状态校验；无页面、被覆盖、未就绪、无按钮、商品页打开或对白尚未完成等明确拒绝均用FileMailbox.Error，没有action_submitted:false/public_message。GameSession按action先清除许可，不能仅凭execution.ui_interaction_started:false推断未执行；公开层因此显示The requested action is unavailable并要求观察。

GUI覆盖奖励地图、未开宝箱、未用火堆、打开的商品页、未结束事件/先古之民/占卜、未到最后一行的建筑师；拒绝后对loot_treasure、choose_rest_option、close_shop、choose_event_option、choose_ancient_option、set_divination_tool或advance_dialogue的下一请求在发送前被observation_required拦截。

建议集中当前上下文的目标和原因，并使available_actions及执行共用。只为第一次UiChanged/ForceClick前的明确拒绝提供证明；已交互、过期、超时或未知结果仍保守。保留每类原生流程、事件和等待，不以统一打开地图替代原生行为。错误原因应提示关闭覆盖、完成选择/对白，或在结算页用run_result_option。

## PROCEED-03与测试修正

当前[transition_details.py](../../src/sts2_mcp/output/transition_details.py)允许终局保留不需要玩法许可的查看工具；[game_session.py](../../src/sts2_mcp/game_session.py)不会对run_won续接玩法许可。旧[verify_run_ending.py](../../tests/game/verifiers/verify_run_ending.py#L82)却要求available_actions==[]。这是旧脚本的过时断言，不是终态仍能执行玩法。

新审阅脚本第一次沿用该断言：architect/evidence.json已捕获正确run_won、HP80→0及四个只读工具，但验证在空列表断言失败。新脚本改为与GAME_ACTIONS无交集，并继续验证没有终局许可、详情读取后的错误proceed与再次要求观察。architect-corrected用另一个新进度进程全部通过。

旧脚本并未被此专项完整执行或修复；上述低优先级结论来自其源码与真实响应对照。后续修复须保留其其余检查并实际回归对应终章分支。主菜单空available_actions的另一个断言不属于同类过时断言。

## 验证记录

- python.log：奖励、宝箱、火堆、商店、先古、事件、占卜、终章、许可及GUI套件相关110项通过，6.720秒。
- [主验证器](../../tests/game/verifiers/verify_proceed_review.py)与[14场景清单](../../tests/game/data/gui_suite_proceed_review.json)：首轮gui前十类通过，ancient因测试在入场尚未可操作时选择馈赠失败；初始available_actions仅有查看工具、所有候选enabled:false。修改为按可用动作等待，gui-remaining四例通过。不重跑前十例，不将这个测试前提问题列为proceed故障。
- gui首轮270.752秒/103次MCP，PID197706退出；gui-remaining127.811秒/47次MCP，PID198634退出。14类成功场景包括14清单条目，首轮失败古代场景的六次调用另保留在总数中。
- architect首轮57.614秒/13次MCP，PID199121退出；architect-corrected57.659秒/17次MCP，PID199710退出。两轮均独立启动全新进度；finally终止拥有的游戏/验证器进程组，必要时强制关闭。总计180次真实MCP包含两轮失败现场，不能称为单次全绿套件。
- [23份完整返回](2026-11-06-proceed-examples/README.md)：22份full、一份default，无图片。divination查看调用可能附图，proceed动作样本均没有图像内容。
- 无生产源码修改，不构建或重跑完整Python/C#。双Boss、教程、真实超时、对局中途退出、多人及全部事件/遗物组合未新增实测；奖励页前进触发父事件恢复仅源码核对。

23项样本来源/哈希、319个相对链接、运行时一致性及四个自有游戏进程退出均已校验，结果保存于证据根verification.json。旧终章入口与当前断言差异另记documentation-conflict-report.md；持续维护文档已注明限制，脚本修复仍待讨论。清单保持26/44。
