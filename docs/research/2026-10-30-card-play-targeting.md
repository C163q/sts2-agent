# 出牌与目标选择源码调研

当前状态：源码调研完成，以下接口是建议方案，尚未实施。当前仍为 Mod `0.14.0`、MCP server `0.11.0`，不提供出牌工具。运行时行为须在实施时验证，不能用本次静态核对代替实机验证。

## 核对基线与证据

- 仓库基线：`47d3bee`。
- Linux 游戏 `v0.107.1`，分支 `v0.107.1`，提交 `59260271`；安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- RitsuLib `0.6.10`、游戏 `0.107.1` 兼容运行时；随附文档 `compat/0.107.1/STS2-RitsuLib.Runtime.xml`；作者源码提交 [`772f280964f2efc7c7e2f29fc59844e68616dd57`](https://github.com/BAKAOLC/STS2-RitsuLib/tree/772f280964f2efc7c7e2f29fc59844e68616dd57)。
- 本次反编译证据在不入库的 `.tmp/2026-10-30-play-card/`，既有 `CardModel`、`NPlayerHand`、`Creature` 等证据在 `.tmp/decompiled/`。后文按完整类型及成员定位，不将反编译源码纳入仓库。
- 对照用户提供的 `~/Pictures/STS2_battle-12.png` 和 `STS2_battle-13.png`：前者为坚毅+的自身指示框，后者为打击的敌人指示箭头。

## 原生出牌与后续选择

`MegaCrit.Sts2.Core.Nodes.Combat.NPlayerHand.StartCardPlay` 创建 `NMouseCardPlay` 或 `NControllerCardPlay`。鼠标流程先拖动到出牌区域，再处理目标；数字键走 `startedViaShortcut: true`，省略起始拖动，仍需完成确认或目标输入。此时尚未提交 `PlayCardAction`，右键等操作可取消。

`NTargetManager._Input` 还有一个容易忽略的细节：拖动时在没有悬停目标的地方松开鼠标，可能切换为点击选目标模式，并非所有情况都立即取消。工具若暴露这种半完成状态，就需要额外观察、选目标与取消协议。

真正的提交入口为 `CardModel.TryManualPlay(target)`：检查 `CanPlayTargeting`，运行 `OnEnqueuePlayVfx`，通过 `ActionQueueSynchronizer.RequestEnqueue` 提交原生 `PlayCardAction`。原生 `NCardPlayQueue.OnActionEnqueued` 会处理本地手牌移出与排队显示。`PlayCardAction.ExecuteAction` 在执行前再次检查卡牌仍在手牌、可打出且目标有效，再消耗资源并运行 `OnPlayWrapper`。因此可以复用一次完整提交，无须把鼠标坐标或数字键中间态变成 LLM 协议。

出牌后的选择必须由实际流程决定：

| 卡牌或机制 | 本版本源码行为 |
| --- | --- |
| 发现 `Models.Cards.Discovery.OnPlay` | 出牌后随机生成三个候选，进入 `FromChooseACardScreen`，允许跳过；选中后设为本回合免费并加入手牌 |
| 冲锋！！ `Models.Cards.Charge.OnPlay` | 通过 `FromCombatPile` 选择抽牌堆两张牌，随后变化为 `MinionDiveBomb` |
| 微光 `Models.Cards.Glimmer.OnPlay` | 先抽三张，再通过 `FromHand` 选择一张放回抽牌堆顶 |
| 自动处理少量候选 | `Commands.CardSelectCmd.FromCombatPile`、`FromHand` 等在候选为零时直接返回；候选数不超过 `MinSelect` 且不要求手动确认时自动返回候选，不打开选择界面 |

不能按卡名预设“出牌后必有选择”，也不能预读发现的随机候选、微光的未来抽牌或未打开抽牌堆的内容。实际出现选择才返回 `choice_required`；自动处理完成则继续等到正常可行动、胜负或其他交互边界。

## 目标规则与可打出条件

这两者需要分别表达。`CardModel.CanPlay` 检查不可打出关键词、实际资源费用、存活队友数量、`Hook.ShouldPlay` 和卡牌自身 `IsPlayable`。例如 `Models.Cards.GrandFinale.IsPlayable` 检查抽牌堆为空；`Normality.ShouldPlay` 会限制本回合出牌次数。不能只比较画面费用与能量，也不能把 `requires_target: false` 当成可打出的保证。

卡牌目标语义如下。下表为卡牌流程，不能套用药水的同名枚举。

| 目标类型 | 是否由调用者指定目标 | 提示信息与限制 |
| --- | --- | --- |
| `Self` | 否 | 原生显示自身指示框；提交卡牌时传 `null` |
| `AnyEnemy` | 是，即使只有一个候选 | 当前可选敌人；不能静默代选唯一敌人 |
| `AllEnemies` | 否 | 原生群体指示范围；不指定某一名敌人 |
| `RandomEnemy` | 否 | 当前可能范围；不提前抽取随机对象，也不预测每一击 |
| `AnyAlly` | 是 | 其他存活玩家，排除自己；拟态 `Mimic` 使用此类型 |
| `AnyPlayer` | 多人时是，单人时否 | RitsuLib 修补此类型的原生卡牌流程，不能只看未打补丁的原生分支 |
| `AllAllies` | 否 | 以原生指示和具体卡牌效果为准，不能仅凭名称推断是否排除自己 |
| `Osty` | 否 | 原生显示自身奥斯提的指示框，卡牌提交不传显式目标 |
| `None` | 否 | 没有目标指示，不意味着可以打出 |

`Entities.Cards.ActionTargetExtensions.IsSingleTarget` 对 `Self` 也返回 `true`，所以不能用它直接生成工具的 `requires_target`。

单体目标还需要核对界面层：`NTargetManager.AllowedToTargetCreature` 区分敌人、玩家和队友，队友排除本地玩家；`OnCreatureHovered` 检查 `Hook.ShouldAllowTargeting`，`_Process` 在目标变为不可命中时取消。单独调用 `CardModel.IsValidTarget` 不足以复现这些限制：原生的 `AnyAlly` 分支只比较阵营，甚至没有自行排除自己。查询和执行均须复用一致的目标检查，包含当前可见性、存活、可命中、单体可指定规则和卡牌目标规则。

`Entities.Creatures.Creature.IsHittable` 与可被单体指定不同。不可指定的对象仍可能受到群体效果；不能把 `ShouldAllowTargeting` 的单体限制套到随机或群体范围。`NCardPlay.ShowMultiCreatureTargetingVisuals` 对敌方群体和随机类型使用 `HittableEnemies`，对自身显示自身框。

### 实验体转阶段

`Models.Powers.AdaptablePower.AfterDeath` 保留死亡的实验体、进入其死亡状态，并在复活期间禁止命中；它阻止战斗立即结束。`Models.Monsters.TestSubject.RespawnMove` 随后复活。

静态源码支持“此时不能把它作为正常攻击目标”，但不足以支持“此时所有无目标牌都不能打出”：`CardModel.CanPlay` 没有统一的空敌方列表检查；`Commands.Builders.AttackCommand.Execute` 对活战斗的空攻击对象会跳出攻击循环。不能自行增加全牌禁用规则，也不能仅因群体提示范围为空就断言卡牌非法。是否能提交、是否只有攻击部分无效果、是否受当时其他流程限制，须对具体牌在隔离实例验证。工具应遵循核实后的原生行为。

## RitsuLib 的帮助与边界

RitsuLib 提供目标类型扩展、`AnyPlayer` 卡牌修复，以及本项目已使用的 `CardPlayingEvent` 等生命周期通知。可以继续复用其实际生效的检查和通知，但它没有代替本项目的交互停止边界与 MCP 权限管理。

尤其不能直接把 [`CardModelTargetingExtensions.GetTargets`](https://github.com/BAKAOLC/STS2-RitsuLib/blob/772f280964f2efc7c7e2f29fc59844e68616dd57/src/Combat/CardTargeting/CardModelTargetingExtensions.cs) 当作只读提示接口：`RandomEnemy` 分支调用 `Rng.CombatTargets.NextItem`，会推进游戏随机数。兼容运行时随附 XML 同样明确记录这个副作用。药水的同类扩展也有此行为。

`CardModel.IsValidTarget` 和 `PotionModel.IsValidTarget` 的源码还互相提醒：`Self` 卡牌不传对象，自身药水传所有者对象。因此未来可以共用对外的目标提示结构，执行和内部目标规范化必须分别适配。

RitsuLib 可注册自定义单体与群体目标类型。未适配类型应明确返回不支持，不能默认按无目标牌提交。任意第三方谓词的纯度和信息边界不能通过类型名称保证。

## 推荐接口

推荐增加两个工具，保留现有选牌工具。下列格式均为设计示例，ID 和数值不是本次实机调用结果。

```text
inspect_targets({"card_id": 7})
play_card({"card_id": 7, "target_id": 3})
play_card({"card_id": 8})
```

`inspect_targets` 是只读查询，针对当前可见、已识别的手牌，不抽随机数，不开始拖牌，不打开瞄准状态，不运行效果。它不产生动作许可；状态未变化时保留之前观察的许可。首版只接收 `card_id`；未来药水接入时再明确扩展参数，不预留无实现的参数。

建议返回卡牌身份、当前综合可提交性、是否要求指定目标、目标类型、当前对象列表及必要的简短不可用原因。例如：

```json
{
  "card": {"id": 8, "name": "Defend"},
  "playable": true,
  "target_type": "self",
  "requires_target": false,
  "targets": [{"id": 0, "kind": "player", "name": "Ironclad"}],
  "reason": null
}
```

```json
{
  "card": {"id": 7, "name": "Strike"},
  "playable": false,
  "target_type": "any_enemy",
  "requires_target": true,
  "targets": [],
  "reason": "No valid target."
}
```

`targets` 表示当前目标类型对应的可指定对象或指示范围：单体模式是可传入 `target_id` 的对象；自身、群体、随机模式仅解释范围，不能因此传入 `target_id`。随机列表不表示命中顺序，也不保证期间状态变化后范围不变；它更不是全部后续效果的对象预测。合法目标存在而能量不足时，列表仍可非空而 `playable` 为 `false`。

对象 ID 使用原生战斗实例 `CombatId`，与敌人观察、期间事件一致；自身身份可在显式查询中提供，不需要为了自身牌增加特殊字符串目标。不得输出隐藏对象或目标内部规则。不可用原因使用玩家可以通过原生尝试获知的简短说明，不附送隐藏的 hook 对象、内部状态机、规则位掩码或未来结果。

`play_card` 一次只提交一张当前本地手牌。要求指定目标时必须提供 `target_id`，即使当前只有一个候选；不要求时省略，传入多余目标应在提交前拒绝，避免悄悄忽略调用者意图。目标是战斗对象 ID，不是屏幕序号。不能在调用中附送选牌 ID、候选预测或后续动作序列。

### 三种方案的取舍

| 方案 | 取舍与结论 |
| --- | --- |
| 完整出牌提交 + 只读目标查询 | 一次表达明确动作，查询按需进行，无悬空瞄准状态；推荐 |
| 开始出牌、选择目标、取消分别提供工具 | 更贴近数字键操作，但增加会话中间态、失效与恢复协议；当前 LLM 任务没有必须保留该中间态的需求 |
| 在出牌参数中同时填写目标和后续选牌 | 发现和微光的候选在效果执行后才确定，不满足信息边界；不采用 |

## 执行、信息边界与现有模块

1. MCP 仍须先 `get_observation`，每次出牌消耗一次许可，失败也须重新观察。目标查询不能替代观察，也不保证查询后状态一直有效。
2. 游戏线程再次检查快照、正常本地出牌阶段、无遮挡、无选牌、未瞄准、动作队列就绪、卡牌归属与实际手牌位置、原生可打出条件和目标合法性。查看选牌遮住的战场仍不允许出牌；建议目标查询也只在正常出牌画面提供。
3. 记录器在提交前订阅。执行优先调用原生 `TryManualPlay`，由同步器和队列消费；不能调用 `CardCmd.AutoPlay` 替代手动打出，不能直接扣资源或调用卡牌效果。目标和牌的检查与提交之间不跨帧等待；若需要等待，提交前重查。
4. 同时记录实际入队的本张 `PlayCardAction`。不能因同步器尚未完成入队时队列短暂为空，就误报已经完成。原生同步器及队列行为须在实机验证。
5. 按现有 `TurnJournal` 返回实际可感知事件和最终观察。等待胜负、本地选择、真正恢复可行动、明确取消或超时；复用 `requireTurnStarted: false`，因为普通出牌后仍是同一回合。不能直接等待整张牌的 `CompletionTask`，否则会在需要 LLM 选牌时挂起。
6. 出牌未产生选择就不伪造选择；产生选择时立即返回 `choice_required`，后续继续使用 `select_card`、`selection_option`、眼睛和已有查看工具。多个选择逐个处理，专门升级等未支持选择仍明确停止，不代选。
7. 入队不等于实际打出，原生执行前还可能取消。建议增加明确的 `action_canceled` 停止原因；不能把“提交成功”写成“效果已生效”，也不能将 `player_ready` 本身当成打出证据。是否真正开始效果由实际事件确认。
8. 超时或异常仍按未知结果处理，不自动重试。`complete` 只表示本次调用到达已知边界且事件未截断，不意味着整张牌及所有后续选择均完成。

基础观察不自动附送所有手牌的目标规则或完整正文；目标规则由显式查询读取，事件只记录已经发生的内容。实际实现需要同步现有 `player_ready` 文档：`end_turn` 要求后续玩家回合，选牌与出牌允许同一回合继续，不能共用“必已进入下一回合”的解释。

首版建议沿用现有单人或测试多人入口限制，覆盖原版单人手牌、能量与星星费用、普通指定与非指定目标、后续已支持选择及期间胜负。真实多人动作当前被适配器统一拒绝；拟态的源码规则应记录并保持目标 ID 设计兼容，但不能把已有接口写成已支持多人。接通真实多人还涉及队友观察、并发动作和远端选择，不隐含纳入本次基础出牌实现。药水使用与任意第三方自定义目标也分别适配。

## 实施验证要求

- 普通指定目标：打击指定敌人；缺省、错误、死亡、不可命中或被单体规则阻止的目标均在提交前拒绝；只剩一个候选仍要求显式 ID。
- 无须指定目标：防御、飞剑回旋镖、闪电霹雳；自身范围可见，随机范围不提前抽取；不得把群体范围误当可指定对象。
- 实验体：正常、死亡待复活、复活后三个阶段，分别验证单体、群体、随机和自身牌，记录实际允许或拒绝行为。
- 其他限制：费用不足、星星不足、X 费、不可打出关键词、卡牌自身条件、外部禁止出牌；查询与执行一致，不能只看费用文字。
- 后续选牌：发现生成后才返回候选；冲锋！！抽牌堆大于二、等于二、小于二和零张；微光抽牌后才列手牌候选。另验证连续选择、手动确认、跳过及未支持的升级选择边界。
- 期间结算：普通伤害、击杀、反伤致死、自动出牌和多次触发；最终状态和事件与真实 UI 一致，不提前返回。
- 只读查询：连续查询随机目标前后比较隔离实例的相关 RNG 计数和实际游戏状态，证明无副作用；查询期间不进入瞄准，不更改 UI。
- 并发与恢复：新鲜及过期许可、查询后状态变化、人工输入、未完成入队、原生取消、超时与请求去重；不自动补发未知结果动作。
- 验证层次：参数与输出边界测试、C# 规则检查、隔离原生游戏场景、图形界面截图与实际 stdio MCP 往返。不得在正式对局构造测试，不以编译通过代替游戏行为验证。
