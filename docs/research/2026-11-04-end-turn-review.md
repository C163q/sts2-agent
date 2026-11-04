# end_turn 场景与参数核验

> 当前状态：现状核验完成，提供 36 份完整真实返回；TURN-01–03 的修复范围及维持 default/full、不增加 summary 已确认，尚未实施。另完成[头槌移动事件补充核验](2026-11-04-headbutt-transition-review.md)，MOVE-01 新事件设计待定稿。工具尚未核销。暂无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 证据及建议范围 |
| --- | --- | --- | --- |
| TURN-01 | 中；错误准确性 | 主菜单、事件、牌组／牌堆／地图覆盖及待处理选牌均只返回 `The requested action is unavailable.`，无法知道是应关闭页面、完成选择还是等待回合；底层 RitsuLib 拒绝文字也不能有效解决问题，因为通用 available_actions 拒绝先执行 | [请求入口](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[可用性](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[错误公开](../../src/sts2_mcp/output/error_output.py)。建议结束回合可用性和安全原因共用入口，在提交前给具体公开原因；异常诊断仍私有 |
| TURN-02 | 中；错误恢复 | 上述前置拒绝没有提交动作，也没有 UI 交互，却清除已有许可；原来合法的选牌、事件选项等随后被 observation_required 阻挡。覆盖拒绝前后完整观察相同 | [会话](../../src/sts2_mcp/game_session.py)、[工具注册](../../src/sts2_mcp/tool_registry.py)、专项真实调用。建议只为已审查的提交前拒绝提供“未提交且未交互”保证，沿用 play_card 的机制保留旧许可；不扩展到 stale_state、超时、异常或未知结果 |
| TURN-03 | 中；可用工具准确性 | 胜负停止时把 available_actions 全部清空，连无需动作许可的详情／页面工具也一起删除；未重新观察就能直接 inspect_relics，同一画面的基础观察也仍列出它。胜负不续接动作许可与查看工具是否可用是两件事 | [共用动作解码](../../src/sts2_mcp/output/transition_details.py)、[许可判断](../../src/sts2_mcp/game_session.py)、[战胜后直接查看](2026-11-04-end-turn-examples/terminal-won-direct-relics.full.json)和[战败后直接查看](2026-11-04-end-turn-examples/terminal-lost-direct-relics.full.json)。建议在清除动作许可的同时保留当前快照中仍合法且无需许可的查看工具；这是所有使用 end_turn_details 的动作共用问题，应在共用出口修正，不能只改 end_turn 的 JSON |

TURN-01–02 属于用户既有“错误原因与恢复提示”“工具报错后的观察前置要求”范围；TURN-03 是本项核对发现的共用返回问题。三项均未修复，不因完成审阅而核销工具或扩大用户 TODO。

## 核对基线与证据

- 日期：2026-11-04；代码 `ff60dc3`，Mod `0.61.0`、MCP `0.63.0`、schema `40`。现行兼容基线统一见 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`，release build `59260271`，RitsuLib `0.6.10` 兼容运行时。核对安装目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 构建与隔离运行时的 Sts2Agent.dll 相同，SHA-256：`4504a65c32e0d03fe3068cf13307a5642da3945cc3c6bab01cb8572d46565d14`。不重建、不安装正式 Mod。
- 原生：[动作分派](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[战斗就绪判断](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[动作等待](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)、[战斗日志作用域](../../src/Sts2Agent/Events/CombatJournalScope.cs)、[回合日志](../../src/Sts2Agent/Events/TurnJournal.cs)、[有界缓冲](../../src/Sts2Agent/Events/TurnEventBuffer.cs)。
- Python：[工具注册](../../src/sts2_mcp/tool_registry.py)、[参数归一化](../../src/sts2_mcp/request_arguments.py)、[会话许可](../../src/sts2_mcp/game_session.py)、[动作解码](../../src/sts2_mcp/output/transition_details.py)、[动作投影](../../src/sts2_mcp/output/action_output.py)、[空值规则](../../src/sts2_mcp/output/null_fields.py)。
- 从目标程序集重新反编译 NEndTurnButton、EndPlayerTurnAction、CombatManager、ActionQueueSynchronizer、PaelsEye、TyrannyPower；证据保存在 `.tmp/2026-11-04-end-turn-review/source/`，不纳入 Git。

## 当前参数与提示词

```json
{"preset":"full"}
```

只有通用 preset：default（默认）／full；不接受 summary、actions_only、批量回合数或额外参数。省略业务参数，MCP 内部取得并发送最近的状态令牌，preset 不进入游戏。没有已有许可时先返回 observation_required；成功详情、观察或可继续的动作均可提供许可，不要求固定调用 get_observation。

default 不裁剪事件，事件中的 source、name、before、after 等已有 null 全部保留；不增加原来没有的字段。当前正常回执仅有上下文、动作列表、transition 和按需附加的选择／notes，default 与 full 没有值得另建 summary 的主体差异。同一观察不能用来预排多次结束回合，但成功且可继续的上一动作回执可以授权下一次调用。

工具提示词：

```text
End the player's turn once and wait for the next input boundary, turn or run end. May stop for a choice before the next turn; inspect and resolve that selection separately.
```

职责与长度合适，已说明只结束一次且可能先停在选择。建议保持主体；如果调整，最多明确返回期间事件和当前交互上下文，无须复制所有停止原因或要求额外观察。

## 返回与场景目录

MCP 成功返回 `scene/screen/available_actions/transition`，有待处理选择时附 `selection.type/status`，需要时附 `notes.selection/interaction`。full 也不附送下一回合手牌、敌人、顶栏或候选详情；完整原生观察先校验，再做动作精简。场景使用返回时的统一上下文，不能把 scene 固定写成 combat。

[36 份完整示例与来源](2026-11-04-end-turn-examples/README.md)包括 17 类结束回合机制、下一次 default 调用、复活后续回合、参数／页面拒绝，以及胜负后直接查看。以下区分返回分支与相同分支下的机制变体。

| 场景 | 当前停止／返回 | 核验重点 |
| --- | --- | --- |
| 普通回合及敌方塞牌 | player_ready／complete:true | 手牌弃置、伤害、card_added 去向和新抽牌；不输出下一回合意图或牌面正文 |
| 回合结束时受到卡牌伤害 | player_ready，或战败 combat_lost | Wither 来源、伤害和真正的战败，不把零血瞬间当终局 |
| 敌方攻击导致战败 | combat_lost | 返回时可能已进入 run_result；不要求把战斗失败原因改成 run_lost |
| 回合结束时保留选择 | choice_required | 父结束回合流程仍在等待，不能再次 end_turn 代替选择 |
| 回合开始时暴政选择 | choice_required | 记录此前事件，不包含尚未发生的选牌结果；完整候选由详情／观察读取 |
| 结束回合伤害、灾厄或自动出牌击杀 | combat_won | 只代表战斗获胜；当前可能为奖励或短暂 unrecognized，不能据 complete 推断奖励已就绪 |
| 怪物死亡并复活 | player_ready | 同一生物 ID；未确认战斗结束时不提前宣告胜利 |
| 格挡抵消伤害 | player_ready | blocked 与实际 hp_loss；不把被格挡部分再次计为生命损失 |
| 抽牌触发自动出牌／消耗触发格挡 | player_ready | 保留采集顺序、autoplay 与已核实来源，事件不折叠成净差值 |
| 无限生命显示 | player_ready | 不输出内部有限 HP；未知 hp_loss 保留 null |
| 偷窃草蜢首回合 | player_ready | 公开 Swipe、伤害及 Escape Artist 图标计数；不虚构偷牌专用事件或未公开牌名 |
| 佩尔之眼额外回合 | player_ready | 可直接恢复另一玩家回合，没有敌方伤害也正常；不人为补一轮敌人行动 |
| 同一动作切换战斗 | player_ready，或真实选择边界 | combat_started 分隔前后 ID 命名空间，不携带新遭遇或隐藏敌人数据 |
| 主菜单／事件等非战斗 | illegal_action | 已有许可时才会进入原生前置判断；目前说明不足并丢失旧许可 |
| 地图／牌组／牌堆覆盖、当前选牌 | illegal_action | 不穿透覆盖层、不代选；目前同样存在 TURN-01–02 |
| 参数错误 | invalid_request | 本地拒绝，不发送 IPC，保留已有许可，不制造新许可 |
| 没有已有许可 | observation_required | 不向游戏提交；错误中的 get_observation 是通用恢复入口，也可成功读取相关详情 |
| 提交后未到达边界／原上下文失效 | timeout 或 interrupted，complete:false | 事件可以非空，不能按错误前状态重发；不续接许可 |
| 事件缓冲超出 512 个位置 | 原停止原因，但 complete:false | 不宣称记录完整、不续接许可；不是另外结束一次回合 |

完整事件种类、可见信息边界、缓冲及普通动作共用规则以[结束回合与期间事件](../development/end-turn.md)为唯一现行定义，不在本报告复制字段表。

## 执行、等待与错误核对

结束回合复用原生 EndPlayerTurnAction，经 ActionQueueSynchronizer 提交一次；该动作只标记结束意愿，后续阶段由 CombatManager 处理。工具继续记录并等待输入边界，不以 EndPlayerTurnAction 本身完成作为整个敌方回合完成。

普通下一回合要求玩家 TurnNumber 增加、重新满足就绪判断、队列为空，并收到后续玩家 TurnStarted 通知。选择优先返回；胜负依据原生通知；战斗交接等待新上下文。普通就绪与胜利还等待已接入的有限 UI 过渡及 250ms 稳定，帧持续推进时最大等待约 25 秒。timeout/interrupted 和事件截断的 complete 为 false；不是进程挂起时也保证 25 秒返回。

当前先检查 expected_state，再按 available_actions 统一拒绝，之后才进入 end_turn 专用提交分支。TURN-01 不能只靠把专用分支的 RitsuLib 提示改成 public_message 解决；多数拒绝根本到不了那里。TURN-02 也不能仅从执行事实中的两个 false 推断未执行，须由已核验的拒绝路径提供明确保证。

原生 NEndTurnButton 的释放逻辑也提交同一 EndPlayerTurnAction，因此使用原生队列本身合理。现有可用性组合检查战斗、玩家阶段、覆盖、选择、出牌过程、队列和目标选择，但没有直接检查按钮 IsEnabled／可见性。源码核对确认这是判断入口差异；尚无自然游戏样本证明这些已有门控全部满足时按钮仍不可用，不把它计作已复现故障。修复可用性入口时应补按钮隐藏／禁用边界验证，不应把未经证实的旁路写成现有事实。

## 已确认设计与重构范围

建议先处理 TURN-01–03，保留 default/full，不增加新参数或 summary。相比给事件加筛选，当前更需要保证拒绝原因、许可和可用工具列表可信；调用者需要新手牌、状态或奖励内容时仍按需查看。

结束回合的可用性和安全原因集中到专用入口，由 available_actions 与提交前复核共同使用；原有 CanEndTurn 还被出牌、浏览及等待使用，不宜直接把它替换为按钮专用判断，避免修改其他职责。提交前明确拒绝沿用已有未提交保证；请求一旦进入提交、异常或未知结果，继续清除许可、不自动重试。

TURN-03 在共用动作解码层处理：停止边界与许可由会话独立判断，查看工具从当前已校验的快照中保留；胜负／未知结果仍不能借此续接游戏动作。候选保守范围为保留仍可用且不要求许可的详情和页面工具，不把 claim_reward、proceed 等需许可动作未经讨论就开放；不把 get_observation 人为塞进 available_actions。需要同步核对其他复用此出口的动作，不另建一份 end_turn 专属裁剪。

TURN-01–03 以上范围已确认，尚未实施。错误恢复、明确拒绝、安全原因、终态查看列表、旧 Mod 缺少保证、stale_state、超时、取消、矛盾证据与无旧许可均须纳入实现验证。[头槌的 MOVE-01](2026-11-04-headbutt-transition-review.md) 是另一个共用事件缺口，核验结果已记录，新增事件字段及覆盖范围仍待定稿，不将候选格式写成已确认接口。

## 验证与限制

已有 46 项相关 Python 检查和 16 组模拟探针通过，证据位于 `.tmp/2026-11-04-end-turn-review/python.log`、`probes.json`。探针覆盖本地参数不发送、当前原生拒绝丢失许可、default/full 保留事件 null、完整观察先校验、选择可直接续接以及未知结果不重试；timeout、中断和截断使用模拟响应，不是自然游戏实测。

GUI 首批完成 17 局，补采 3 局通过，合计完成 20 局，覆盖 18 类场景配置及胜负复测，另含主菜单检查。保存 105 次真实 MCP 调用，逐次核对 structuredContent 与文字 JSON 相同；预期拒绝也计入调用数。第一批的机制样本另经 34 条离线断言核对，包含来源、阻挡伤害、触发顺序、复活身份、隐藏 HP、偷窃草蜢计数和战斗交接，不只检查 stop_reason。

第一批在额外回合补采前发生采样脚本 StopIteration：读到先古之民入场尚未就绪、所有选项 disabled 的画面，却假定必有 enabled 选项。对照现有 verify_ancients 的就绪／对话流程后，补采按当前 available_actions 等待输入就绪并推进必要对话，再取得佩尔之眼进入战斗；不修改生产工具或降低断言。原始失败报告和已完成 17 局保留在 `.tmp/2026-11-04-end-turn-review/report.json`；新三局及直接查看证据在 `terminal/report.json`。失败那次只读取先古之民的调用也计入 105，不冒充额外回合成功样本。

胜负复测中，end_turn 返回空列表，直接再次 end_turn 为 observation_required，但不经 get_observation 调用 inspect_relics 成功；之后的基础观察也列出 inspect_relics，确认 TURN-03。牌组、抽牌堆、地图和事件拒绝前后的完整公开观察相同；选牌／事件原来合法的后续动作被 observation_required 阻挡，确认 TURN-02。所有这些原生拒绝均退化为同一通用 message，确认 TURN-01。

两次采样的自有游戏 PID 为 159278、160474，均由上下文管理器关闭，最终核对进程已不存在。未操作正式游戏、存档或安装目录；不声称重新验证编译或全部 C# 检查。

天然异常／断线／渲染停止、所有角色／遗物组合、多人、第三方 Mod 和按钮强制隐藏／禁用尚未新增游戏样本。相同结构下的机制变体不等于所有卡牌、怪物及能力都已穷举。只做源码／现有测试核对的边界不冒充自然实测。
