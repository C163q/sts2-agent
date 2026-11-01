# 奥斯提与君王之剑的接口覆盖核查

当前状态：已完成，共 3 项，已完成 3 项。观察、详情与事件修复已通过 Python、纯 C#、独立中文游戏及专项原生检查；接口文档已同步，无阻塞。未安装到正式游戏；第三方召唤的已知限制见下文。

基线核查结论：奥斯提的原生出牌与攻击来源已有通用接入，但基础观察和战斗对象详情将其误归入敌人；代受伤存在格挡遗漏，最大生命变化没有事件覆盖。君王之剑的原生攻击来源正确，手牌完整详情可以查看其正文，但悬浮剑的可见身份和悬停预览没有接入。下文核查针对基线，最终行为与验证结果在实施部分记录。

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

## 实施范围

优先扩展现有观察与 `inspect_combatants`，保持原生出牌入口：

1. 统一可见战斗生物的筛选，再按真实阵营分出敌人与友方召唤物；为奥斯提保留身份、当前实际可读的生命／格挡／状态，并在详情中提供可悬停说明。不要仅从敌人列表排除奥斯提而丢掉它。
2. 为可见悬浮剑提供对象摘要，并在 `inspect_combatants` 中读取其原生卡牌预览；未悬停基础观察不附送正文或精确伤害。按实际可见实例处理多把剑、禁用悬停及消耗移除。
3. 补齐转交伤害的格挡结果和友方最大生命事件，覆盖首次召唤、成长、代受伤、死亡与再次召唤。只发布实际已展示的信息，不回放隐藏期间变化。

沿用现有工具，不增加专用工具。新增基础观察 `allies[]`，包含可见友方召唤物的 `id/name/hp/max_hp/hp_display/block/powers`，按横坐标排列；实际状态显示控件跟踪玩家格挡时，附带 `block_shared_with: "player"`，避免重复计算。隐藏战场为 `null`，可见但没有召唤物为 `[]`。`inspect_combatants` 同样提供 `allies` 的身份与状态，以及 `allies.<index>.powers.<index>` 悬停来源。

基础观察与详情新增 `player.sovereign_blades[]`，每项只含绑定卡牌的稳定 `id/name`；名称为外观可识别的基础名，不从模型附送升级后缀。显式预览的标题保留实际升级后缀，基础观察不自动展开正文。详情的共享提示以 `player.sovereign_blades.<index>` 为来源，在保留原牌拥有者、牌堆和目标上下文的副本上重算当前预览，再按原生卡牌预览的 `PileType.Deck` 格式化，不修改原牌的预览缓存；不附送卡牌原本未展示的所在牌堆。多剑按绑定卡牌的稳定 ID 排列，不把持续公转的坐标纳入状态令牌；原生公转会调整子节点前后顺序，因此不能沿用子节点枚举顺序。隐藏、零缩放或视口外的剑不作为可见对象，可见但不可悬停的剑保留摘要而不提供说明。

友方最大生命沿用 `max_hp_changed`，扩展客户端允许 `target.kind: "ally"`；等待 UI 显示端点，隐藏取消且恢复不补发。代受伤的格挡结果从本次动作中新产生的原生 `DamageReceivedEntry` 补录，按结果对象去重；只补录在该次伤害入口与补录时均可读的格挡，不读取过去战斗历史补写事件，不改变死亡来源采集。

后续应在独立中文游戏实例中，经真实 MCP 完成奥斯提攻击、部分／完全格挡、伤害溢出、死亡后再召唤，以及君王之剑铸造、移出手牌、多剑、消耗的验证；悬停内容须与原生 UI 对照。当前结果不能作为这些场景已经通过的证明。

## 实施计划与验证

使用 `writing-plans` 制定本计划，并以 `executing-plans` 在当前工作区连续执行；所有游戏 API 以上述程序集及补充反编译证据为准。Mod/MCP/schema 同步更新，正式安装与正式存档不在本次范围。

- [x] 契约与复现：新增 `tests/python/test_companions.py`，验证基础观察投影、友方／剑的详情来源、非法 ID／路径拒绝及友方最大生命事件；增加 `Testing/Fixtures/CompanionFixture.cs` 和 `tests/game/verifiers/verify_companions.py`，先在基线复现敌我误分类及缺失的剑摘要。
- [x] 观察、详情与事件：新增 `Observation/SovereignBladeInspection.cs`；修改 `CombatObservation`、`CombatantInspection`、`GameAdapter` 和 Python 投影／详情验证；在 `TurnJournal` 补录格挡、按显示端点记录友方最大生命并处理首次加入的延迟公开。新增 `Testing/Checks/CompanionChecks.cs`，验证隐藏取消、成长与伤害拆分，按失败证据逐项修复。
- [x] 交付：执行全部 Python 测试、纯 C# 检查、构建与独立中文 GUI 套件；覆盖奥斯提攻击与再召唤、剑的铸造与多实例、相关隐藏边界，以及死亡归因／动作续接／战斗交接回归。更新接口文档、保存示例 JSON，独立审阅完成。

重点边界：隐藏生命条不补模型数字；共享格挡不重复计算；多剑不读取其他隐藏卡牌；持续公转不使令牌持续变化；原生未调用 `LoseHpInternal` 的格挡不能遗漏或与已有伤害重复。

## 已核实的失败与修正

- `red-osty-gui`、`red-blade-gui`：独立中文游戏分别复现缺少友方列表、缺少悬浮剑摘要；当时手牌与游戏 UI 中已有对应对象。
- `red-events-gui`：静态观察修正后，奥斯提主人的部分／完全格挡仍遗漏，召唤成长缺少最大生命事件；溢出伤害分支正确。原生检查的 15 项中 4 项失败，按原生结果补录与显示端点记录修复。
- `green-gui`：真实文件响应已有友方状态的悬停来源，却因 Adapter 未转发 `allies` 而被客户端拒绝；已补齐响应字段。仅验证 C# 详情对象不能发现这一跨层遗漏。
- `verified-gui`：测试误以为下一回合一定重新抽到 Unleash；原生史莱姆加入的 Slimed 占用了抽牌位置。移除错误的测试前提，保留原生抽牌与动作拒绝规则。
- `verified-gui-2`、`diagnostic-gui`：多剑检查前后唯一玩法差异为 `player.discard_count: 0 -> 1`，来自测试准备的原生牌飞行动画，剑 ID 和顺序未变。测试直接调用原生命令，须等待实际弃牌计数更新后再判断公转稳定性；未扩大生产动作的等待范围。
- `hidden-block-red-gui`：10 项剑检查全部通过；新增隐藏格挡检查单独失败，补录泄露了 10 点隐藏格挡。修复在每次原生伤害入口记录可读目标，并在补录时再次校验战场、身体及格挡显示。
- `preview-red-gui`：剑进入弃牌堆后施加 5 层 `ParryPower`，原生悬停显示 `Gain 5 Block`，读取旧缓存的工具显示 `Gain 0 Block`。改为在保留原牌上下文的副本上重算预览，并新增“先读工具、再触发原生悬停”及不改写原牌缓存的检查，避免原生悬停先刷新缓存后掩盖问题。
- `identity-red-gui`：升级后的剑仍只有相同的悬浮外观，基础身份却从 `CardModel.Title` 读出了 `+`；14 项检查仅此一项失败。基础名改用 `TitleLocString`，显式预览标题继续保留原生可见的升级后缀。
- `contracts-green.log`：沙箱内带事件循环的 Python 检查在 30 秒超时；按环境约定改在沙箱外执行完整套件，`python-full.log` 为 377 项通过，不把通信受限算作功能失败。

上述目录与日志均位于 `.tmp/2026-11-02-companions/`。最终构建与 GUI 验证使用新目录保存，不覆盖失败现场。

## 当前示例与审阅

真实 MCP 输出节选保存在本次证据目录的 `examples/`：`osty-observation.json`、`osty-growth-receipt.json` 和 `sovereign-blade-details.json`，不包含控制令牌。原生悬停卡牌的英文正文为 `Retain.\nDeal 15 damage.`，工具正文与实际渲染逐字一致；中英文截图由 `SovereignBladeChecks` 保存。

独立只读审阅发现的格挡补录可见性问题已修正并复审；未发现其他已确认的新增严重或重要问题。审阅不替代最终游戏验证。第三方 Mod 若让新生物永久透明，待公开身份仍可能使动作等待至现有超时边界；原生奥斯提有限淡入按当前程序集核对并由游戏场景覆盖，不宣称所有第三方召唤动画均受支持。

现行事件文档还保留了“搜刮尚无通用物品日志”的旧表述，与既有 `RunInventoryJournal` 实现不符，本次同步修正为受支持的资源、物品与永久牌组变化；该项只是文档纠正，未改变搜刮逻辑。

## 最终验证结果

交付版本为 Mod `0.43.0`、MCP `0.41.0`、schema `25`，工具数量不变。

| 验证 | 结果与证据 |
| --- | --- |
| Python 全套 | 377 项通过，32.917 秒，`python-full.log` |
| 纯 C# 检查 | 60 项通过，`csharp-checks.log` |
| 最终构建 | 0 警告、0 错误，`verified-build.log` |
| 独立中文 GUI 回归 | `release-gui` 的 10 局在同一自有进程内全部通过：奥斯提、剑、首次召唤、原生边界检查、随从死亡归因、活雾反伤死亡、战斗交接、充能球可见性及连续动作 |
| 最后基础名修正后的验证 | `identity-green-gui` 用最终 DLL 重新执行 1 局剑检查，14 项全部通过；此前 10 局使用的构建仅在最后基础名读取和新增检查上不同，不将它们描述为同一 DLL 的单批验证 |
| 专项原生检查 | 奥斯提 16 项、剑 14 项，另回归交接 19 项、充能球可见性 18 项；均通过 |
| 文档与清理 | 473 个本地链接及差异空白检查通过；上述两个自有进程 PID `193250`、`194442` 已退出；未更新正式游戏中的 Mod 或存档 |

最终 DLL SHA-256 为 `c881ff83ed5a552b0ecd218a316c17e887a47118e8b04601f3db44c5f55390ab`，构建产物与隔离运行时一致，匹配 `identity-green-gui/report.json`。汇总为 `.tmp/2026-11-02-companions/verified-summary.json`。最终基础名及预览重算分别完成独立只读复审，无未解决的重要发现。
