# advance_dialogue 开发核验

## 基线与范围

核验日期2026-11-07，代码基线e325609，Mod0.78.1、MCP0.80.1、schema46；Linux游戏v0.107.1、release构建59260271，RitsuLib0.6.10。结论对应此基线，参数建议见[审阅报告](2026-11-07-advance-dialogue-review.md)。

本地证据根目录：`.tmp/2026-11-07-advance-dialogue-review/`。游戏程序集为安装目录下`data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256为`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；隔离测试DLL为`6cb15bec6745bc9ef8c81bbbd683527732a774e6013089fbe0422263d04f4e7a`，与当前构建产物相同。原生三种类型已从目标程序集重新反编译至证据目录的`source/`，未提交源码或程序集。

## 实现入口和原生流程

| 职责 | 入口与核对结果 |
| --- | --- |
| 公开注册 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)的advance_dialogue：NO_ARGUMENTS、default/full、需要许可、返回transition、记录事件。未启用unsubmitted_rejection_unchanged。 |
| 参数解析 | [ancient_details.py](../../src/sts2_mcp/output/ancient_details.py)的ancient_arguments：除choose_ancient_option外均只接受省略或空对象；额外参数在Python拒绝，许可保留。 |
| 分发 | [RequestDispatcher.cs](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)：存在EpilogueInspection.Current时进入EpilogueRequest，其余进入AncientRequest。底层非空参数在分发前拒绝。 |
| 先古之民 | [GameAdapter.Ancient.cs](../../src/Sts2Agent/Adapter/GameAdapter.Ancient.cs)：核对expected_state、Exposed／Singleplayer／Ready和Continue.IsEnabled，UiChanged后ForceClick原生DialogueHitbox；等待同一run／先古model的NonCombatBoundary。 |
| 建筑师 | [GameAdapter.RunEnding.cs](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs)：核对expected_state、Ready、当前button且非IsProceed；UiChanged后ForceClick原生事件按钮，等待同一run的NonCombatBoundary。 |
| 按钮和可用动作 | [AncientInspection.cs](../../src/Sts2Agent/Observation/AncientInspection.cs)、[EpilogueInspection.cs](../../src/Sts2Agent/Observation/EpilogueInspection.cs)、[GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：已经使用对应Ready和Continue／Button判断；具体拒绝仍独立散落在两个动作分支。 |
| 停止边界 | [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs)的NonCombatBoundary，及共用ActionObservation：等待原生就绪和稳定状态，不要求整段对话结束。 |

目标程序集的`MegaCrit.Sts2.Core.Nodes.Events.NAncientEventLayout`将DialogueHitbox.Released连接到OnDialogueHitboxClicked，再调用SetDialogueLineAndAnimate(current+1)。最后一句隐藏并禁用hitbox、启用馈赠选项；此前的假继续按钮是展示控件。NAncientDialogueHitbox.OnRelease只负责点击外观，推进通过Released信号完成。

`MegaCrit.Sts2.Core.Models.Events.TheArchitect.CreateOptionForCurrentLine`在最后一句创建PROCEED选项，其回调为WinRun；其余选项回调为AdvanceDialogue，递增当前行并等待PlayCurrentLine，再更新选项。工具通过IsProceed区分最终按钮；没有把最终胜利混入普通推进。

这些操作沿原生Released／事件选择流程执行，不通过直接改写对话索引完成。ForceClick本身会绕过hover／focus／pause检查，因此合法性应在调用前集中判断；此次未调整点击方式。

## 两项问题的原因

### 拒绝后丢失许可

两个动作入口的拒绝均使用FileMailbox.Error，没有明确action_submitted:false保证；注册表也未启用该动作的未提交恢复规则。[game_session.py](../../src/sts2_mcp/game_session.py)因此将其作为不具备恢复依据的失败处理。raw execution记录证明本次拒绝没有开始UI交互或提交，但公开会话不能只凭这些事实推断所有同类错误都可恢复。

与已完成的choose_ancient_option对照，整改应同时补齐点击前的明确保证与注册策略；继续保留过期、提交后、不确定、缺失或矛盾证据的重新读取要求。不能通过放宽所有illegal_action来解决。

### 原因未公开

先古路径把无房间、覆盖、非单人和未就绪合并为一条私有消息，无Continue时另返一条私有消息；建筑师路径把无上下文、未就绪、无按钮和最终Proceed合并。均未提供public_message，[error_output.py](../../src/sts2_mcp/output/error_output.py)转换后只剩通用illegal_action文本。

整改应集中当前页面、原生忙碌状态和按钮用途的判断，并让执行、按钮enabled和available_actions引用同一判断。两个场景各保留自己的原生按钮及生命周期；无须新增全项目对话框架。

## 验证与边界

相关Python检查32项通过，耗时1.789秒，见证据根目录python.log。GUI共核验五类不同场景：

| 场景 | 结果与证据 |
| --- | --- |
| 战斗中误调用 | 明确未点击、前后snapshot一致；end_turn随后被要求重新观察；刷新后成功。gui-fixed/evidence.json。 |
| 已展开馈赠／已领取馈赠 | 分别拒绝继续，纠正为choose_ancient_option或proceed仍被观察许可阻挡；刷新后成功。gui-fixed/evidence.json。 |
| 卡牌包选择覆盖 | 拒绝继续；selection_option被观察许可阻挡，inspect_selection后可继续。gui-fixed/evidence.json。 |
| 先古对话 | 地图／牌组覆盖拒绝，两个关闭工具直接成功；额外参数本地拒绝；原生外部推进造成stale_state，下一动作要求观察；刷新后正常推进至馈赠，随后误继续导致改选馈赠被许可阻挡。gui-remaining/evidence.json。 |
| 建筑师 | 地图／牌组覆盖拒绝，两个关闭工具直接成功；正常推进到最终按钮为action_completed／events:[]；误继续后proceed要求观察，刷新后原生前进返回run_won。gui-architect/evidence.json。 |

前后相等的snapshot和execution.ui_interaction_started:false／action_submission_observed:false用于核验已发生的拒绝，不替代未来接口需要明确给出的未提交保证。成功动作后直接继续调用的许可正常续接。

保留三个脚本准备失败记录：首轮把公开recovery的get_observation误写为refresh_observation（37.444秒）；gui-fixed在前三类通过后错误地认为close_map也需要玩法许可（118.630秒）；gui-remaining完成先古核验后，终章启动没有等待主菜单就断言场景（77.406秒）。分别修正测试预期和加载等待，最后只补跑剩余场景，未改产品代码。gui-architect最终通过，67.224秒。原始失败报告不改为成功；通过范围按具体case和evidence记录统计，不声称前三个整体报告通过。

五个自有游戏进程69212、69529、70003、70304、70572均已退出。两种成功调用都实测default；17份[典型返回](2026-11-07-advance-dialogue-examples/README.md)中14份为实际MCP返回，3份full通过本轮实际原生响应及当前解析／投影生成并单独标记。中段先古示例来自外部原生推进，两个最终边界full来自实际default调用的原生响应；没有冒充额外full游戏调用。full与default在这些无空值回执中相同。未修改产品代码、版本或正式安装，未重建DLL。多人、第三方对话、全部角色／台词随机分支，以及超时、进程退出等异常路径没有新增GUI样本。已知致死斗篷按用户TODO留待游戏升级后复测，与普通翻句分开。
