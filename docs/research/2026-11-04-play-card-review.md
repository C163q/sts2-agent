# play_card 核验与连续出牌调研

> 当前状态：场景核验完成，处于设计讨论。已核验 29 项不同场景／门控并保存 33 份完整 full 返回及 12 种原生队列轨迹。连续出牌已确定遵循原生队列；工具名称、参数和逐张回执仍待定稿，尚未修改公开工具行为。play_card 未核销，无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 依据与建议 | 状态 |
| --- | --- | --- | --- | --- |
| PLAY-01 | 中 | 商店、地图／牌组覆盖、选择、非出牌阶段等拒绝统一为 `Normal card play is unavailable.`，无法据此判断应关闭页面、继续选牌还是等待。 | `GameAdapter.CardPlay.cs:35`；将阶段合法性与具体拒绝原因收敛到同一入口，供单张出牌、目标查询及连续出牌复用。保留已核实的未提交／未交互保证。 | 待定稿后修复；属于现有错误准确性 TODO 的提前覆盖。 |
| PLAY-02 | 中 | `TargetInspection.Reason` 丢弃 preventer，将外部限制统一为 `This card cannot be played now.`，丢失原生拒绝气泡能显示的阻止来源名称。 | `NMouseCardPlay.StartAsync` 调用 `UnplayableReasonExtensions.GetPlayerDialogueLine(preventer)`；阻止来源使用牌／遗物／状态／附魔／Affliction 的公开标题。优先复用该 UI 文本，不公开内部 hook 标识或隐藏机制。 | 待定稿后修复；不可打出关键词与自身条件在原生 UI 中本就共用 UNPLAYABLE，不将其笼统描述列为缺陷。 |
| PLAY-03 | 低 | 缺少目标的错误及参数说明只提 `inspect_targets.targets`，容易被理解为必须先调用该工具；实际可直接使用已知的当前敌人 `id`。 | `GameAdapter.CardPlay.cs:51`、`PLAY_SCHEMA` 与现行出牌指南。说明目标 ID 的统一含义，保留“未知目标要求时查询”的简短提示。 | 待修订文案；没有实际的 inspect_targets 前置门控。 |

另有一个**已明确的许可设计边界**：`action_canceled` 即使 `complete:true`、原生画面已恢复可行动，MCP 仍过滤掉玩法动作，不续接许可，须先读取状态。这与当前文档及测试一致，不能当作实现偏差悄悄更改；是否允许有充分完成证据的取消直接续接，留待单张与批量回执一起定稿。

执行后取消目前也没有原因，但不能直接套用手动拖牌前的拒绝气泡规则：队列执行路径不一定显示相同气泡，也不能用事后状态反推当时唯一原因。可公开原因及逐张结果须单独设计取证，无法核实就保持未知。

两处持续维护文档仍只列 play_card 的显式未提交保证，而登记表已经覆盖 end_turn：已同步 [architecture.md](../development/architecture.md) 与 [roundtrip.md](../development/roundtrip.md)，不改变许可实现。

## 核对基线与证据

- 代码基线：`d46406c`；Mod `0.62.0`、MCP `0.64.0`、观察 schema 40。
- 游戏：Linux `v0.107.1`，release build `59260271`；程序集为安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 依赖：RitsuLib `0.6.10` 的游戏 `0.107.1` 兼容运行时；[作者发布页](https://github.com/BAKAOLC/STS2-RitsuLib/releases/tag/v0.6.10)用于核对发行基线。游戏行为以该程序集与实际运行结果为证，不以其他版本或网页摘要替代。
- RitsuLib 源码直接核对 `.tmp/ritsulib-end-turn-review/`，提交 `772f280964f2efc7c7e2f29fc59844e68616dd57`，工作树无修改。重点查看 `CardModelIsValidTargetAnyPlayerPatch`、`CustomTargetTypeGeneralPatches`、`ModExtraHandCardPlayPatch` 和 `SecondaryResourceCardPatches`；原版手牌仍走原生队列，不把额外手牌或自定义资源支持推定为本项目已经接入。
- 新反编译证据保存在不纳入 Git 的 `.tmp/2026-11-04-play-card-review/source/`；类型、成员及重点位置见下表，完整文件摘要见同目录外的 `source-manifest.json`。不提交游戏资源或反编译产物。
- 本轮仅增加双重门控的文件测试入口 `check_test_play_queue`、GUI 核验器及测试清单，不增加公开 MCP 工具，不安装正式 Mod。

| 原生类型／成员 | 作用与关键依据 |
| --- | --- |
| `CardModel.TryManualPlay`／`EnqueueManualPlay` | 检查当前资源及目标，通过 `ActionQueueSynchronizer.RequestEnqueue(new PlayCardAction(...))` 提交；没有“上一张必须结算完”或“队列必须为空”的限制。 |
| `NMouseCardPlay.StartAsync`／`UnplayableReasonExtensions.GetPlayerDialogueLine` | 原生拖牌拒绝使用统一气泡：费用／队友不足有专用提示；外部限制格式化来源的公开标题；不可打出关键词和卡牌条件均为 UNPLAYABLE。 |
| `NPlayerHand.CanPlayCards`／`AreCardActionsAllowed` | UI 检查拖牌状态、额外回合归属、玩家动作禁用和眼睛查看状态；没有用全局队列为空限制快速出牌。 |
| `ActionQueueSynchronizer.RequestEnqueue` | 单人模式直接同步入队；敌人／抽牌阶段的原生延迟请求是另一种机制，不属于建议开放的批量入口。 |
| `ActionQueueSet.GetReadyAction` | 单人队列按顺序执行；队首等待选择时不执行后续项。 |
| `PlayCardAction.ExecuteAction` | 执行前再次解析卡牌、目标，检查牌仍在手牌、当前 `CanPlay` 和 `IsValidTarget`，再消耗资源并执行效果。 |
| `GameAction.Execute`／`Cancel` | 执行中调用 `Cancel()` 后，外层 finally 仍可能把 State 写成 `Finished`；必须独立记录取消通知及真实出牌事件。 |
| `CardSelectCmd.FromHand`／`FromHandForUpgrade` | 实际需要手工选择时使用 `CancelPlayCardActions`；候选足够少而自动选择时不走该分支。 |
| `CardSelectCmd.FromChooseACardScreen`／`FromSimpleGrid`／`FromCombatPile` | 选择上下文使用 `PlayerChoiceOptions.None`；暂停当前牌，保留已排队后续项。`CancelAllCardPlay` 只取消正在拖动／等待入队的 UI 持有者，不等于清空已入队动作。 |
| `ActionQueueSet.PauseActionForPlayerChoice` | 只有带 `CancelPlayCardActions` 时取消该玩家尚未执行的出牌，并在该选择期间继续拒绝新入队的出牌。 |
| `TrueGrit.OnPlay` | 未升级随机从真实手牌模型选一张消耗；排队只移走 UI 持有者，尚未执行的牌仍属于模型手牌，因此可以被选中。 |
| `ActionQueueSet.CombatEnded`／`ActionQueueSynchronizer.SetCombatState` | 收到 NotInCombat 后清理未执行战斗动作与跨回合延迟请求；胜负结束的具体通知时序不能混为一谈，不会把未出牌迁移到下一场战斗继续。 |
| `CombatManager.HandlePlayerDeath`／`CheckWinCondition` | 死亡移除战斗牌并处理待结算失败；不同同步／异步时序须分别检查实际出牌与队列状态。 |

## 当前公开契约

```json
{"card_id": 7, "target_id": 3, "preset": "full"}
```

- 一次提交一张当前可见、已识别的手牌；`card_id` 是本场战斗稳定 ID，不是手牌下标或 `deck:N`／`pile:N`。
- 卡牌 ID 为 `0..2147483647`；目标 ID 为 `0..4294967295`。不接受 bool、浮点、字符串或 null。
- `any_enemy`／`any_ally` 必须提供目标，即使只有一个；其他受支持类型必须省略目标。UI 指示范围与目标合法性的既定规则不变，不因为暂时费用不足而清空目标范围。
- 当前拒绝 TargetedNoCreature 和未知自定义目标类型；不能把它们当作无目标卡提交。额外手牌仍不在当前读取／提交范围内。
- 默认 preset 为 `default`，另有 `full`；没有 summary。动作回执本身已经精简，未发现需要增加 summary 的独立信息层。
- 同一 MCP 连接串行处理请求，现行 `CanPlayCards` 还要求队列为空；并发发送多个现有 play_card 不能用来实现原生快速排队，也不能借用稍后才返回的许可。
- 本地参数错误与显式未提交／未交互的拒绝保留既有许可；成功只在当前共同许可条件下续接，未提交失败不生成新许可。
- 成功返回 `scene/screen/available_actions/transition`；期间事件沿用 [end_turn](../development/end-turn.md)，全量观察仍只保留在文件 IPC 内。普通手动牌 full 的 `autoplay:false` 在 default 中省略；true、事件空值、before/after 等沿用统一例外。

### 返回分支目录

实际参数和 33 份完整 full 返回见[样本目录](2026-11-04-play-card-examples/README.md)，不是手写示意；原生连续探针的提交、选择时状态及实际出牌／取消事实见[队列轨迹](2026-11-04-play-card-examples/native-queue-traces.json)。后者是测试诊断，不是未来公开工具格式。

内容变体不单独改变结构：单体攻击、自身技能、群攻、随机攻击、X 费用、生成牌、回牌、自动出牌、召唤和充能球等都复用事件列表；已覆盖的移动与召唤例子也可参见[结束回合及移动核验](2026-11-04-turn-transitions-implementation.md)。

| 分支 | 返回与后续操作 |
| --- | --- |
| 普通结算 | `player_ready`，complete 通常为 true；可按返回继续行动。 |
| 手牌选择／升级、发现、牌堆选择等 | `choice_required`，带精简 selection；候选详情由 inspect_selection 获取。实际选择工具在该步骤继续父牌结算。 |
| 原生自动选择 | 不伪造选择边界，继续到普通结算或其他真实边界。 |
| 当前战斗胜利／失败 | `combat_won`／`combat_lost`，保留当前可用查看工具，不续接玩法许可。 |
| 跨战斗交接 | 共用观察器及 journal 识别新战斗，事件可含 `combat_started`；不是“旧牌队列跨战斗续跑”。 |
| 确认取消并恢复可行动 | `action_canceled`；当前无取消原因，也不续接玩法许可。 |
| 未支持交互 | `manual_input_required`；不自动选择、不把未知选择当作牌已结算。 |
| 未完成 | `timeout`／`interrupted` 或事件截断使 complete 为 false；不自动重试。 |
| 参数错误 | error invalid_request，修正请求；发生在提交前。 |
| 状态已过期 | error stale_state，必须重新读取，不复用旧保证。 |
| 阶段、资源、手牌、目标不合法 | error illegal_action；目前已有足够明确的资源／目标说明与仍通用的阶段／条件说明，见问题表。 |
| 未知结果或传输／协议故障 | 走共用错误与许可清理；不因“客户端没收到”判断游戏没有执行。 |

## 原生连续出牌的结论

**单人支持上一张未结算时继续按顺序入队。** 入队的牌仍在模型手牌中，只是 UI 从手牌持有者移到出牌队列；真正开始执行时才移动到 play 堆并结算。既不预扣所有排队牌的费用，也不保证提交时合法的牌将来一定能打出。

| 中途变化 | 原生行为 | 批量工具必须遵守的含义 |
| --- | --- | --- |
| 正常顺序 | 前一张结算后继续下一张；不并行结算卡牌效果。 | “连续入队”不能宣传成同时结算多张牌。 |
| 后续牌能量／星能不够 | 对应执行尝试取消，不消耗该牌费用；队列继续后面的合法牌。 | 不做全批回滚，不因一张失败清空后续队列。 |
| 单体目标死亡但还有敌人 | 对应牌无法再命中该目标而取消；后续合法牌继续。 | 不自动换目标。若已战斗胜利，则进入结束清理分支。 |
| 手动选择手牌消耗／弃置／升级等 | 当前牌等待选择，取消该玩家后续排队出牌；选择结束后不会自动重排这些牌。 | 返回选择边界，并标明排队项已取消；不能自行补发。 |
| 发现牌、独立候选或弃牌堆选择 | 当前牌等待选择，已排队后续项保持等待；完成选择后原生继续。 | 工具必须及时返回 choice_required，不能等待整批结束；后续选择回执可能同时包含已排队牌的效果。 |
| 候选少而自动选择手牌 | 不进入手动选择取消分支；选中排队牌消耗后，该牌执行时已不在手牌而跳过。 | 不能按卡牌名称预判“必定取消所有后续项”。 |
| 随机消耗命中排队牌 | 该牌执行时跳过，后面的合法牌仍继续。 | 跳过未必产生 BeforeCancelled，必须靠实际出牌事实和公开去向判断。 |
| 胜利 | 未执行战斗动作取消并清理。 | 不自动领取奖励，也不重发到下一场战斗。 |
| 死亡 | 实测已排队的后续牌在手牌移除后跳过，State 为 Finished，未触发取消，也未实际出牌；与胜利的直接取消不同。同步死亡还可能在下一次提交之前已经发生。 | 每次提交前重查终态；不能仅凭 TryManualPlay 返回 true、Finished 或有无取消通知判断已打出。 |

费用或目标分支还有一个容易误判的细节：执行中取消的动作最终 State 也可能是 Finished。缺少手牌的跳过则连取消通知都没有。因此统计结果至少需要“提交是否发生、取消是否发生、真实 card_played 是否发生”三类独立事实，不能用一个枚举状态代替。

RitsuLib 还可能把自定义次级资源不足标为 `BlockedByCardLogic`，因此不能把该 flag 直接解释成某个原版牌的条件失败。当前项目没有接入这些额外资源，细化诊断时仍须保留安全兜底，不能凭 flags 拼出未核实的机制说明。

### 时序与信息边界

- 入口只接受当前已知手牌及明确目标，不预知即将抽出的牌、随机结果或发现候选，不预填后续选牌。
- 只在当前玩家可操作的出牌阶段尝试连续入队；不利用同步器的敌人回合缓冲绕过现行工具阶段要求。
- 先提交的牌可能同步完成或已经弹出选择，再轮到下一项。每次尝试都须重新检查当前 UI、同一局／战斗／回合及原生合法性；不承诺整份请求一定能全部入队。
- 入队后的执行仍由原生检查决定。PlayCardAction 执行时的 CanPlay／IsValidTarget 不等于全部 UI 目标准入规则，工具不能再加一层自写执行器，擅自取消原生仍会执行的牌。
- 选择、胜负或页面变化后，尚未提交的项直接留在回执里，不私自保存为未来自动执行的列表。只有已经进入游戏原生队列的项遵循原生暂停／恢复。
- 取消原因仅公开能够取证的事实；不把事后费用变化、随机消耗或目标死亡猜成唯一取消原因。未知结果保留未知，不自动重试。
- 不输出牌堆内部位置、隐藏顺序、随机数或未来效果。逐张回执描述本次请求的执行事实，不扩大基础观察内容。

## 方案与接口候选

**已确认：采用原生连续入队。** 逐张等待完整结算的批处理只节省调用次数，不能还原正在排队的牌被选择、消耗或取消的行为，因此不作为当前方案。

两个公开入口候选仍待定稿：

1. **新增 `play_cards`，保留 `play_card` 单张契约（建议）**。单张参数简单、旧调用不变；复用内部提交与记录器。代价是多一个公开工具，核销清单和目录需要同步增加。
2. **在 `play_card` 中加入 `cards`，与 card_id/target_id 互斥**。工具数量不变，但 schema 需表达两种请求形状，错误提示、required 规则及示例都更复杂。

建议输入形状，仅为候选，**当前不能调用**：

```json
{
  "cards": [
    {"card_id": 7, "target_id": 3},
    {"card_id": 8},
    {"card_id": 9, "target_id": 3}
  ],
  "preset": "default"
}
```

建议返回公共动作回执，再增加按输入顺序的逐张结果，标识原请求位置、card_id 和已核实的执行状态。必须区分“已打出”“未打出／取消”“仍在原生队列中等待”“未提交”，不能只有成功数量。选择后原生队列会继续时，第一次回执不能把仍排队项写成最终成功或失败。

建议把已经入队项目的只读追踪延续到后续选牌回执，提供最终发生的出牌／取消结果；这不负责新增提交，也不是后台执行计划。若只在第一份回执给 queued 而不再更新，原生后续取消又没有期间事件时，调用方无法直接知道最终逐张结果。这一跨回执契约也需要在实现前确定。

整批尚未进行 UI 交互或提交时，可以使用现有显式未提交保证；已有部分提交后，不能把某一项的未提交错误当作整批未执行，也不能自动回滚或重试。超时／断连不能撤销原生队列；未知结果仍须重新读取，不默默取消已经提交的牌。

仍需定稿：入口名称；空数组／重复 ID／最大长度；结构及初始牌／目标引用是否整批前置校验；逐张结果的字段及有证据的取消原因；跨选牌回执的状态更新；中途单项提交被拒后是否继续尝试后项；action_canceled 的许可续接。费用与动态条件必须按实际提交时检查，不能预扣总费用或预测将来结果。已确认原生取消后的既有队列继续，不等于所有这些接口问题都已确定。

## 建议的小范围重构

当前 `CardPlayRequest` 同时承担目标查询、参数验证、阶段门控、单张提交订阅及等待。直接往里加多张循环会把“允许尝试入队”和“整批结算结束”混在一起，且现有 CanPlayCards 要求队列为空，不能用于后续每张的快速提交。

建议仅拆出三项职责：

- 当前出牌阶段与可公开拒绝原因，共用单张和队列入口；初始稳定要求与允许排队的后续提交要求显式区分。
- 单次原生提交及逐张生命周期追踪，不把 Finished 当作已出牌。
- 批量入口的边界与汇总，复用既有 ActionObservation、CombatJournalScope、期间事件和 MCP 许可机制。

不另建卡牌结算器，不直接 EnqueueWithoutSynchronizing，不修改资源／牌堆替代正常出牌，也不扩展为任意工具批处理。跨选择等待已有原生队列，不新增 Mod 后台待执行计划。

## 验证与剩余范围

验证结果：

- 构建通过，0 警告／0 错误；最后一次构建耗时 4.33 秒。最终测试 DLL 与隔离运行时 SHA-256 均为 `909767d134a3cdddebe62d07f740c988b8f6ca960bb87ec2f1fe0f8c78bd96a6`。版本号未变，只有测试设施及文档变更。
- 相关 Python 55 项通过（`python-delivery.log`）；既有 C# 检查 91 项通过（`csharp-final.log`）。
- 29 项不同场景均有通过记录：12 种原生队列探针、16 个公开工具场景、1 个入口门控；对应所选证据共 127 次真实 MCP 调用。门控另验证 testMode 关闭和 suite 关闭时各 68 个测试入口被拒绝。
- 证据来自三份运行记录、两份测试构建：`gui-final` 中的 11 个公开工具成功场景、`gui-supplement` 中的 9 个原生探针、`gui-delivery` 的 9 个剩余场景。后两份使用上述最终 DLL；前一份 SHA-256 为 `c12f9d81207e352e283a70b0523ba65fdcf0746d50edcda9be7bdbd17aba502f`，随后仅调整原生探针条件及测试等待。每份公开样本独立记录实际 DLL 摘要。
- 33 份公开 full JSON 已与实际 structuredContent 逐项相等、参数及摘要核验；12 种原生轨迹来自最终测试 DLL。最后 9 局套件完整通过，184.32 秒；不把早期失败目录改写为通过。
- 本次四个自有游戏进程 `201054`、`202516`、`213337`、`214437` 均已确认结束。未安装 Mod，未操作正式存档。

全部原始报告、日志与状态保存在 `.tmp/2026-11-04-play-card-review/`。初始测试及证据复核暴露了三类控制条件问题，原记录均保留：

- Offering 同步死亡发生在后项提交之前，不能代替“已经排队后死亡”的样例；分别保留负面 API 探针和先 Strike、再 Offering 的排队探针。
- Discovery 可能同步进入选择。后加牌被底层 API 接受，不能证明它们原先已经排队；改成 Strike 在前阻塞，并断言普通连续探针的后项提交时首项仍为 Executing。
- 初始地图可能没有 close_map；覆盖核验只在真实 available_actions 提供时关闭。胜利后的原生探针验证通过，但测试清理曾因页面仍变化触发 stale_state；补充只读稳定等待，不重试玩法动作。

这些修正只涉及测试条件与清理；没有把模拟请求形状或底层 API 的负面探针称为公开合法玩法。

多人与第三方目标、全部特殊卡牌／遗物组合、真实鼠标输入的速度上限、超时／断连时游戏既有队列继续的全部时序，不在这些探针的验证保证内。跨战斗交接沿用共用链路的既有范围，本轮不重复证明所有重入事件。

原生探针使用隔离初始状态，通过正常 CardPileCmd、PlayerCmd 等布置牌与资源，再连续调用真正的 TryManualPlay 并跟踪游戏队列；没有手写卡牌效果或替换选择器。星能探针给原版牌设置战斗星能费用，终态探针调整初始 HP；这是控制条件验证，不表示这些组合都来自自然游玩。顺序探针在同一调用内无等待提交，记录后项入队时前项仍为 Executing；没有模拟真实鼠标逐帧输入速度。
