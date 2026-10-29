# 意图与双方 powers 详情

当前状态：实现与安装已完成。共 4 项，已完成 4 项；独立游戏验证和独立审阅均通过，无代码阻塞。正式截图附近场景的采样待用户重启并恢复战斗，尚未验证。

## 已确认范围与格式

新增文件操作 `inspect_combatants`，一次读取本地玩家和当前可见敌人的 powers，以及当前展示的敌人意图。先提供 JSON，MCP 接入另行进行；Mod 升至 0.7.0。

结果包含 `scene: "combat"`、`player.powers`、`enemies[].id/name/powers/intents` 及共享 `hover_tips`。powers 保留名称和可见计数，intents 保留当前渲染的 category/value。所有原生悬停说明按标题和正文同时相同去重，以 `sources` 路径关联本次结果中的具体 power 或 intent，例如 `enemies.0.powers.0`。不同动态正文不合并。瞄准/出牌期间沿用原生悬停抑制规则，整次返回不可读。空数组表示没有当前可读条目，整个容器不可见时为 `null`。

共享说明包含主说明和附带的术语、卡牌预览等原生额外提示。使用已实现的英语格式化和图标文本转换；不返回未来招式、内部模型 ID、隐藏 powers、额外战斗信息。基础观察保持原范围；详情包含敌人意图时沿用 `notes.enemy_attack_intents`，没有意图时不添加，不返回卡牌数值 notes。敌人用基础观察已有的 CombatId 关联，sources 下标仅指向本次结果。

## API 证据

核对日期 2026-10-29，游戏 Linux `v0.107.1`，本机 `release_info.json` 与 `data_sts2_linuxbsd_x86_64/sts2.dll`；Godot 4.5.1.m.12，.NET 9。证据反编译保存在不纳入 Git 的 `.tmp/decompiled/`。

- `NIntent.OnHovered` 使用其 `_intent`、`_targets`、`_owner`，且检查 `HasIntentTip` 后调用 `GetHoverTip`。只从已显示控件取得这三个字段，不读取 `Monster.NextMove`；隐藏容器、意图图标或控件不产生解释。`HiddenIntent.HasIntentTip` 为 false，不揭示隐藏招式。
- `AbstractIntent.GetHoverTip` 使用 intents 本地化、实际目标及拥有者；`AttackIntent.GetIntentDescription/GetSingleDamage` 使用当前原生伤害预览，包括对玩家生效的修正。
- `NPower.OnHovered` 使用 `Model.HoverTips`。`PowerModel.HoverTips` 按 `HasSmartDescription`、实际 Amount、Owner、Applier、Target 和 DynamicVars 构造当前说明，再追加 `ExtraHoverTips`；不能以静态 Description 或 `GetDumbHoverTip` 替代实际 power 主说明。
- `NCreature.OnFocus` 会汇总 `Creature.HoverTips`，但后者直接遍历 `Monster.NextMove.Intents` 和全部模型 powers，不能作为本工具读取入口。亦不调用 OnFocus/OnHovered，以免改变 UI、事件订阅或目标预览。
- `HoverTipFactory.FromPower` 直接创建提示，无语言缓存；沿用既有关键词与药水缓存隔离。`PowerCmd.Apply<T>` 和 `ThrowingPlayerChoiceContext` 仅在独立测试入口准备可见 powers，不用于正式游戏或读取接口。

## 步骤

1. [x] 核对截图、原生悬停入口、显示筛选和英语动态说明来源。
2. [x] 以实际 IPC 检查先确认旧 Mod 不支持新只读操作；实现详情读取、共享说明和命令行入口，补充独立测试检查及只读导出脚本。
3. [x] 中文独立游戏验证双方 powers、攻击及其他意图、去重、不可见条目、重复读取和语言/缓存不变；回归原有观察和详情。
4. [x] 同步持续维护文档、独立审阅并处理发现，安装 0.7.0，交付已验证变更。正式重启后的采样另待用户恢复场景。

## 初始验证

旧 Mod 0.6.0 对 `inspect_combatants` 返回 `stale_state`，新接口成功断言失败，证明尚未实现。该请求没有动作令牌且操作不是游戏动作，未推进正式对局。

## 已完成验证

- .NET 9.0.122 构建通过，0 warnings、0 errors；Python 全套 51 项回归通过。
- 中文独立图形游戏完成 31 项战斗对象检查，包括动态 powers、共享说明、可见计数、隐藏/屏外/不可悬停条目、当前控件绑定、HiddenIntent 无说明、连击包含玩家易伤、缩小的缓存名称英语化且原值/中文提示不变、作用域异常恢复、瞄准期间拒绝，以及语言和关键词缓存不变。
- 实际输出 3 个敌人和 6 条共享提示；玩家 Strength 2、Vulnerable 2 和永久 Shrink，各敌人 Vulnerable 2，共享一条易伤说明。攻击预览为 4 和 6，与界面及原生悬停正文一致；另有给 2 张状态牌的意图。
- 初次检查中两项失败来自测试假定英语标题为 Attack/Buff；实际原生标题为 Aggressive/Strategic。改为核对原生本地化键，未改写游戏提示文本。
- 主菜单调用返回 illegal_action；详情重复读取一致，前、中、后观察令牌一致，所有 sources 均可解析。
- 同实例回归基础观察 27 项、手牌 8 项、界面 15 项、药水 15 项；对应只读导出均通过，日志无 ERROR。
- 证据（不纳入 Git）：`.tmp/roundtrip/combatant-inspection.json`、`combatant-inspection-check.json`、`combatant-checks.json`、`combatant-setup.json`、`combatant-*-regression*.json` 及 `observation.png`。
- 正式截图 STS2_battle-5.png 的恢复场景尚未采样，不能把独立样本当作该截图数据。尚未接入 MCP。

## 审阅修复

独立审阅发现 Shrink 在施加时缓存中文怪物名，`PowerModel.HoverTips` 的 DynamicVars.AddTo 会覆盖新鲜名称变量，英语模板通过 `ApplierName.StringValue` 输出中文。真实中文测试已复现，新增英语正文及施加者名称检查按预期失败，证据 `.tmp/roundtrip/combatant-shrink-red.json`。

修复采用 `EnglishCardText.ReadPower` 的可嵌套主线程作用域。只在当前 power 的 powers 表条目中，将缓存 StringVar 型 ApplierName 替换为独立英语 StringVar，复制格式化变量字典，不修改真实 DynamicVars、LocString 或游戏语言。异常与嵌套结束后恢复上下文；新增原始缓存、中文原生提示不变及异常恢复检查。正式 API 核对仍基于同一程序集的 StringVar/DynamicVarSet/LocString/PowerModel/ShrinkPower。

同时核实 `NCreature.ShowHoverTips` 在 Hand.InCardPlay 时不显示提示，因此文件接口在该阶段整体返回 illegal_action，并增加临时卡牌操作节点的拒绝检查。

最终复审确认缓存名称修复与临时测试节点修复均已解决，无 Critical、Important 或 Minor 遗留。Mod 0.7.0 已安装至本机游戏 mods/Sts2Agent，DLL 与清单 SHA-256 均与构建产物一致，旧文件以编号备份保留。独立测试窗口已关闭，未操作正式对局；MCP 与 Codex 配置均未改动。
