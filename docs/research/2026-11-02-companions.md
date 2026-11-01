# 奥斯提与君王之剑的接口覆盖核查

核查结论：奥斯提的原生出牌与攻击来源已有通用接入，但基础观察和战斗对象详情将其误归入敌人；代受伤存在格挡遗漏，最大生命变化没有事件覆盖。君王之剑的原生攻击来源正确，手牌完整详情可以查看其正文，但悬浮剑的可见身份和悬停预览没有接入。本次仅核查与记录，未修改工具行为，也未完成这两种机制的游戏内验证。

## 核对基线与证据

- 核对日期：2026-11-02；代码基线 `ef0a25d`，Mod `0.42.1`、MCP `0.40.0`、schema `24`。
- 游戏：Linux `v0.107.1`，release `59260271`；RitsuLib `0.6.10`，兼容分支 `0.107.1`。
- 原生程序集：游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 本地反编译证据：`.tmp/2026-11-02-companions/source/`，文件名对应下文的完整类型后缀；类型目录为同级 `types.txt`。反编译产物不纳入 Git。

下文的原生类型均位于 `MegaCrit.Sts2.Core` 命名空间。源代码调用链可以确认接口覆盖及遗漏，但不代替节点可见性、动画稳定与真实 MCP 回执验证。

## 奥斯提

### 身份与静态观察

`Models.Monsters.Osty` 继承 `MonsterModel`。`Commands.PlayerCmd.AddPet<T>` 用玩家的阵营创建它，再设置宠物所有者并调用 `CreatureCmd.Add`。因此奥斯提同时满足 `Creature.IsMonster == true` 和 `Creature.IsEnemy == false`；内部模型类别不等于敌我关系。

[CombatObservation.EnemyNodes](../../src/Sts2Agent/Observation/CombatObservation.cs) 当前以 `node.Entity.IsMonster` 过滤节点，未检查阵营。只要奥斯提身体可见，就会被列入 `enemies`，并沿用现有生命条、格挡、状态图标和意图采样。[CombatantInspection](../../src/Sts2Agent/Observation/CombatantInspection.cs) 复用同一筛选，因此其状态说明也会错误关联到 `enemies.<index>.powers`。目前没有独立的友方召唤物列表。

原生 `Osty.IsHealthBarVisible` 仅在存活时为真。死亡身体仍可能留在战场，生命条隐藏不能转写为模型中的 `0/max_hp`。`OstyCmd.Summon` 还通过 `TrackBlockStatus(summoner.Creature)` 让奥斯提显示主人的格挡，不能把这份显示当成一份可独立消耗的格挡。

### 出牌与攻击来源

- `Models.Cards.Unleash`、`Fetch` 和 `SicEm` 使用 `DamageCmd.Attack(...).FromOsty(Owner.Osty, this)`。
- `Commands.Builders.AttackCommand.FromOsty` 设置 `Attacker = osty`、`ModelSource = card`；执行时将两者分别传给 `CreatureCmd.Damage` 的 `dealer` 与 `cardSource`。
- [TargetInspection](../../src/Sts2Agent/Observation/TargetInspection.cs) 与[出牌入口](../../src/Sts2Agent/Adapter/GameAdapter.CardPlay.cs) 已通过原生目标规则和 `TryManualPlay` 执行卡牌，不需要另一种“奥斯提攻击”动作。`TargetType.Osty` 也已有映射。
- [TurnCapture](../../src/Sts2Agent/Events/TurnCapture.cs) 采集上述 `dealer/cardSource`；[TurnJournal](../../src/Sts2Agent/Events/TurnJournal.cs) 用 `IsEnemy` 区分事件身份。因此已公开奥斯提的攻击应记录 `actor.kind: "ally"`、`actor.name: "Osty"`，来源仍为对应卡牌。静态观察误分类与事件身份使用了不同判断，应一并统一。

这一结论针对原生调用链；本次没有实际导出奥斯提攻击的 JSON。

### 代受伤与生命周期缺口

`Models.Powers.DieForYouPower.ModifyUnblockedDamageTarget` 将符合条件的、打向主人的攻击转交给存活的奥斯提。`CreatureCmd.Damage` 先消耗主人的格挡，再让奥斯提承担未格挡部分，超出奥斯提生命的伤害回到原目标。

当前日志仅在实际调用 `Creature.LoseHpInternal` 时采集 `DamageResult`。原生转交分支在主人不损失生命时，会直接创建一个包含主人格挡结果的 `DamageResult`，不调用主人的 `LoseHpInternal`。这份结果不会进入日志，而伤害期间的格挡减少又被 `BlockChanged` 订阅排除，造成遗漏。例如，按源码推导，10 点攻击先消耗主人 3 点格挡、余下 7 点全由奥斯提承担时，可能只记录奥斯提的 7 点生命损失，缺少主人格挡的 3 点；这不是本次实测样本。

此外：

- `OstyCmd.Summon` 对存活奥斯提使用 `GainMaxHp`，同时提高最大生命并治疗；当前 `TurnJournal` 没有订阅生物的 `MaxHpChanged`，`RunResourceJournal` 仅订阅玩家，而 Python 的 `max_hp_changed` 契约也仅接受玩家。不能仅在 C# 增发一个友方事件而不改客户端契约。
- 死亡与复活已有通用订阅。`Creature.HealInternal` 从死亡变为存活时会发出 `Revived`，与当前日志的去重重置兼容；仍需覆盖奥斯提死亡后再次召唤、同一动作内再次死亡的实际表现。
- `CreatureAddedToCombatEvent` 已有 `creature_added` 接入，但仅在回调当时尝试识别可见身份，没有为尚未展示的身体延后发布。不能据此声称首次召唤已完整覆盖；应检查原生节点创建、淡入及生命条刷新时序。

## 君王之剑

### 战场对象与悬停内容

`Commands.ForgeCmd.PlayCombatRoomForgeVfx` 将 `Nodes.Vfx.NSovereignBladeVfx` 挂到玩家的 `NCreature` 下。每把剑绑定一个具体的 `SovereignBlade` 卡牌实例；多把剑可以共存，因此不能只读一个全局铸造数值。

`NSovereignBladeVfx.UpdateHoverTip` 的原生入口为：

```csharp
NHoverTipSet.CreateAndShow(_hitbox, HoverTipFactory.FromCard(Card));
```

`HoverTipFactory.FromCard` 返回绑定当前卡牌的 `CardHoverTip`。这是一张当前卡牌的预览，包含其正文；并非独立的“铸造层数”计数控件。`ForgeCmd` 增加卡牌伤害，剑的外观也会随伤害变化，但不能从剑的大小或私有字段额外反推并返回精确铸造数值。

原生悬停要求未攻击、未进入目标选择且 hitbox 接受鼠标；发起出牌时会禁止悬停，主人死亡时也会将 hitbox 改为忽略鼠标。接入详情时须复用这些边界，不能只检查节点存在。

### 现有工具覆盖

| 场景 | 当前覆盖 |
| --- | --- |
| 剑在当前可见手牌中 | 基础观察有卡牌摘要；`inspect_hand` 默认完整预设可读取当前正文 |
| 剑在可浏览牌堆中 | 可通过现有原生牌堆查看读取，不代表已支持战场悬停入口 |
| 战场上可见悬浮剑 | 基础观察不列出此对象；`inspect_combatants` 与 `inspect_ui` 均未枚举 `NSovereignBladeVfx` |
| 剑被消耗或发生变牌 | 原生移除对应悬浮节点，不能依据过去存在的剑继续返回悬停正文 |

### 攻击来源

`Models.Cards.SovereignBlade.OnPlay` 使用 `DamageCmd.Attack(...).FromCard(this)`。`AttackCommand.FromCard` 设置 `Attacker = card.Owner.Creature`；剑的移动和斩击由 `BeforeDamage` 中的特效调用单独完成。

因此伤害事件的攻击者是储君，来源是君王之剑卡牌。剑不是另一个 `Creature`，不应登记成友方生物或赋予独立的攻击者身份。现有通用来源采集与此一致。

## 建议的后续实现

优先扩展现有观察与 `inspect_combatants`，保持原生出牌入口：

1. 统一可见战斗生物的筛选，再按真实阵营分出敌人与友方召唤物；为奥斯提保留身份、当前实际可读的生命／格挡／状态，并在详情中提供可悬停说明。不要仅从敌人列表排除奥斯提而丢掉它。
2. 为可见悬浮剑提供对象摘要，并在 `inspect_combatants` 中读取其原生卡牌预览；未悬停基础观察不附送正文或精确伤害。按实际可见实例处理多把剑、禁用悬停及消耗移除。
3. 补齐转交伤害的格挡结果和友方最大生命事件，覆盖首次召唤、成长、代受伤、死亡与再次召唤。只发布实际已展示的信息，不回放隐藏期间变化。

另建 `inspect_osty`、`inspect_forge` 等专用工具会增加相似入口，当前没有必要；只修正敌我分类则仍会遗留悬停和事件缺口。上面是候选方案，尚未确定最终 JSON 字段，也未实施。

后续应在独立中文游戏实例中，经真实 MCP 完成奥斯提攻击、部分／完全格挡、伤害溢出、死亡后再召唤，以及君王之剑铸造、移出手牌、多剑、消耗的验证；悬停内容须与原生 UI 对照。当前结果不能作为这些场景已经通过的证明。
