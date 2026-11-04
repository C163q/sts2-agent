# use_potion 开发核验记录

> 当前状态：五项修复及地图 covered 已交付，use_potion 已核销。已核验 30 类场景／边界并整理 120 份完整返回；USE-01–05 与地图覆盖状态由[实施记录](2026-11-05-potion-actions-implementation.md)跟进；下述表格及样本保留修复前基线，暂无阻塞。

本文供开发实现与复测使用，保留问题编号、内部类型、源码位置和测试记录。实际表现、建议及待决定事项见[用户审阅说明](2026-11-04-use-potion-review.md)。

## 优先关注的问题

以下为审阅基线的问题及已确认处理范围，实施验证另记。必须先处理正确性及共用契约，再决定是否调整输出。

| 编号 | 优先级 | 问题与影响 | 证据及建议范围 |
| --- | --- | --- | --- |
| USE-01 | 中；错误准确性 | 空槽、越界、缺少目标、多余目标、目标不合法、自动药水、不能移除及页面不允许用药，大多统一返回 `The requested action is unavailable.`。LLM 无法区分改参数、关闭页面、完成选择或改用其他动作 | `PotionRequest` 将阶段门控和用药条件分别合并，动作拒绝未设置 public_message；basic、blocked、覆盖页、商店及选择实测。集中阶段原因、单槽定位及目标原因，由查询、available_actions 和提交前复核复用；不公开异常堆栈或内部类型 |
| USE-02 | 中；错误恢复 | 已有许可时，明确未输入、未提交的用药拒绝仍清除许可；随后直接 end_turn 或选牌会得到 observation_required | 原生拒绝未给明确未提交保证，use_potion 也没有登记该保证。basic 的五种语义拒绝前后原生快照相同，但下一次 end_turn 均被 MCP 拦截；选择和覆盖页亦采样。关闭浏览页自身不要求玩法许可，仍可直接执行，不能据此断言许可保留。可复用 play_card/end_turn 的明确拒绝契约；已交互、已提交、stale_state、取消和未知结果不能因此保留许可 |
| USE-03 | 中；槽位定位 | potion_slot 的说明要求从 inspect_potions.potion_slots 数位置，却未说明筛选结果须读 slot_indices 映射。筛选后的第 0 项可能实际属于第 1 槽，容易喝错药 | `POTION_SLOT.description` 与 inspect_potions 筛选契约不一致。参数应明确引用从左到右、含空槽的原始下标；读取筛选结果时使用同位置的 slot_indices，而非压缩数组下标。use/discard/inspect_targets 共用此参数定义，宜一并修正 |
| USE-04 | 低；不必要的前置暗示 | 顶层说明仅在目标要求未知时建议 inspect_targets，但 target_id 字段写成该查询结果中的 ID，容易被理解为每次必须先查目标 | 源码只校验当前目标，不校验是否查询过。提示词方向为“提示卡牌或药水可指定的目标”，而非强制查询；target_id 说明只需明确何时填写及省略。当前观察中已知且适用的生物 ID 可直接使用；merchant 保持现有支持，不把 self 当成输入参数 |
| USE-05 | 中；跨槽耦合及读取职责 | InteractiveHolders 要求整栏所有槽位在屏内、启用且可悬停，任一槽不满足即让其他槽位也不能用药或查询目标。PotionJournal 及药水获得事件还复用含交互检查的 OnScreenHolders，导致已公开自动用药事件也可能漏记 | slot_boundary 分别把第 2 槽移出屏幕、禁用、禁止悬停，确认未动的第 1 槽也被拒绝。journal_boundary 禁用第 1 槽后结束回合，第 2 槽瓶中精灵实际消耗并救回玩家，却没有 potion_used；这是双重测试门控注入条件，不是自然游玩布局。建议分开展示读取和单槽交互：取消药水槽位视口截断，单独核对目标槽的真实交互条件；全栏仅因无法辨认槽位位置等真实歧义拒绝。事件使用展示规则，不使用“是否可以点击药水”的规则；potion_obtained 同类边界仍仅由源码核对 |

涉及共用链路的修改不等于 discard_potion 已完成内容审阅；该工具仍单独核验。USE-05 中事件链的验证范围也应单列，不以普通用药成功代替边界验证。

## 基线与证据

- 代码基线 `30a01e9`，已由 feat/potion-inspection-presets 快进合入 main；Mod `0.63.0`、MCP `0.65.0`、schema `40`。当前兼容基线仍以 [README](../../README.md#当前版本与前提)为准。
- 游戏 Linux `v0.107.1`，release build `59260271`；重新核对安装目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 隔离实例 Mod DLL SHA-256：`2d66c65c5e84e514a19480c74b7df33f6316670c588652697d8456255ca37dba`；与上次最终受测构建及本地输出一致。本次未改 C#，无须重建或安装正式 Mod。
- RitsuLib `0.6.10`；本地源码 `.tmp/ritsulib-end-turn-review`，提交 `772f280964f2efc7c7e2f29fc59844e68616dd57`。动作走游戏 API，战斗事件沿用已接入的生命周期。
- 原生证据为上述同一游戏程序集的反编译：`.tmp/2026-10-31-events-implementation/source/PotionModel.cs` 的 EnqueueManualUse/IsValidTarget/OnUseWrapper；`.tmp/2026-10-30-selection/UsePotionAction.cs` 的 ExecuteAction/CancelAction；`.tmp/2026-11-02-top-bar-visibility/source/NPotionHolder.cs` 的 UsePotion/TargetNode/DisableUntilPotionRemoved；`.tmp/2026-10-30-potions/NPotionPopup.cs` 的 _Ready/RefreshButtons/OnUseButtonPressed；`.tmp/2026-10-31-shop/source/FoulPotion.cs`。64 种原版药水的目标类型遍历及边界依据见[原生药水动作调研](2026-10-30-potion-actions.md)，没有推断自定义目标类型。
- 项目入口：[原生请求](../../src/Sts2Agent/Adapter/GameAdapter.Potions.cs)、[药水规则](../../src/Sts2Agent/Actions/PotionActions.cs)、[药水展示与交互](../../src/Sts2Agent/Observation/PotionInspection.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[药水事件](../../src/Sts2Agent/Events/PotionJournal.cs)、[获得事件](../../src/Sts2Agent/Events/RunInventoryJournal.cs)、[参数](../../src/sts2_mcp/output/potion_action_details.py)、[登记](../../src/sts2_mcp/tool_registry.py)、[许可](../../src/sts2_mcp/game_session.py)。
- 实测原始证据位于 `.tmp/2026-11-04-use-potion-review/`；验证器使用真实 stdio MCP，每次核对 structuredContent 与文字 JSON 相同。测试场景仅配置隔离初始状态，实际使用仍走公开工具及原生流程。

## 现有参数与职责

```json
{"potion_slot": 0, "target_id": 1, "preset": "full"}
```

- potion_slot：必填，原始药水栏下标，包含空槽，从 0 开始；整数 0..2147483647。空槽或超出实际槽数为语义拒绝，不会自动换一瓶药水。
- target_id：仅在当前药水要求指定目标时填写，即使只有一个候选；不要求时必须省略。接受战斗生物整数 ID 0..4294967295，或商人字符串 merchant。null、self、布尔、浮点及数字字符串均不接受。
- preset：default/full，省略为 default；没有 summary。未知字段、不支持的预设及结构／类型错误在 MCP 本地拒绝，保留已有许可，不发送原生动作，也不凭错误创建新许可。

工具只负责使用当前槽内的一瓶药水。原生拥有药水的对象身份、槽位、当前阶段、用药条件及目标在提交前重新核对；同名药水替换仍使旧令牌失效。效果、生成候选、自动触发、资源及库存变化由游戏处理；不预测随机结果，不自动处理后续选择，不附送药水正文。

药水正文由 inspect_potions 提供；inspect_targets 查询当前 usable、discardable、target_type、requires_target、targets 和不能使用的 reason。不必为已知合法目标强制调用查询。单人 AnyPlayer 药水直接用于自己；self 只作战斗外查询引用，不作 target_id 输入。

## 场景目录

| 场景 | 基线行为及边界 |
| --- | --- |
| 单体火焰药水 | 指定当前敌人 ID，返回 potion_used、实际伤害／死亡；仍有敌人时为 player_ready |
| 自用及单人 AnyPlayer 药水，如格挡药水 | 省略目标；格挡等变化按 UI 记录，不因 target_type 含 player 就要求显式输入自己 |
| 群体伤害药水 | 无须目标，记录实际对象；指示范围不等于全部效果对象，恶臭药水也可能伤害玩家 |
| 技能／攻击／能力／无色药水 | choice_required；已生成候选通过 inspect_selection 或 get_observation 读取，工具不提前选牌 |
| 液态记忆、赌徒佳酿 | 分别打开原生弃牌堆选择、手牌选择；选择或确认后继续原生流程 |
| 果汁／血瓶在战斗或战斗外 | 战斗恢复 player_ready；战斗外完成为 action_completed。顶栏 HP／最大 HP 变化沿用可见记录 |
| 事件、休息处、商店、地图及子奖励页 | 无覆盖／父流程门控阻挡且药水允许时可使用；战斗外地图与战斗中打开地图不同，后者覆盖战斗且不能用药 |
| 恶臭药水对商人 | 普通商店关闭商品页后，以 merchant 投掷；加金币及原生反馈来自游戏。商品页或地图盖住商人时不能投掷 |
| 恶臭药水对假商人 | 实测使用 merchant 后进入战斗并等待 player_ready，记录 potion_used、初始能量及抽牌；从战斗外进入首场战斗不生成 combat_started，该标记仅分隔同次动作中的前后两场战斗 |
| 禁止移除／自动药水 | 原生 CanRemovePotions 为 false 时不能用；瓶中精灵不能手动使用。自动触发时仍可产生 potion_used，例如恶臭药水致命后被精灵救回 |
| Entropic Brew 生成新药水 | 只记录实际获得的药水及槽位；不在用药前展示随机生成物 |
| 不可命中的敌人、过期槽位身份 | 目标拒绝或 stale_state，不回退到其他对象，不自动重试 |
| 原生取消 | action_canceled；不虚构 potion_used；基线仍要求再读当前状态，不能把已入队取消当作未提交拒绝 |
| 战斗胜负 | combat_won/combat_lost；可能已转入奖励或结算，也可能尚在过渡。可用查看入口沿共用终态规则保留；不据此宣称整局已结束 |
| 选牌、牌组／牌堆／战斗地图覆盖、主菜单、过渡、忙碌或非玩家回合 | 拒绝，不穿透覆盖层、代选、等待未来时机自动使用或缓存重放 |
| 超时／中断／异常、事件截断 | 沿共用动作回执及许可规则处理；不保证未执行，不自动重发。未知结果不能用 USE-02 的安全拒绝恢复规则处理 |

## 当前输出与设计建议

成功回执已经采用最小动作格式：scene、screen、available_actions、必要的 selection 类型／状态、transition，可能有共用 interaction/selection note；不会自动附送完整手牌、顶栏或候选。需要时调用对应查看工具。期间事件保留提交到停止边界已经公开的变化。

default 使用统一空值规则，full 保留已生成的普通 null；前后值、数组位置等例外仍由统一入口处理。两个预设没有另外改变动作行为。事件没有 null 时，两份结果可能相同。

对外参数和输出的建议以[用户审阅说明](2026-11-04-use-potion-review.md#已确认的修改范围)为准。开发侧候选范围如下。优先处理 USE-01–05，并作以下小范围重构：

1. 将阶段原因、单槽定位与合法性诊断集中在药水动作规则入口，提供布尔可用性及安全公开原因，供 available_actions、inspect_targets 和实际提交复用；使用与丢弃各自保留原生限制。保留父事件／先古之民等待可操作子奖励页时允许处理药水的例外，不能仅因父任务尚未完成就一概拒绝。
2. 分开“药水栏展示及原位置可识别”“指定槽位可操作”“该瓶药水当前可使用”；不让悬停能力或另一个槽位的状态污染只读目标查询及事件读取。真实隐藏／遮挡、队列／选择门控仍需准确核对。
3. 安全拒绝仅在确定未交互且未提交的路径给出明确保证；一旦开始禁用槽位、入队或执行，不把普通异常解释为未执行。保留现有原生取消和不确定结果的处理。

这三项已确认实施；不能直接把新增执行事实中的 false 当作未执行证明，也不把所有错误都改成保留许可。

## 关联发现：地图上下文

用户说明与实测字段对照见[地图与牌组显示状态的差异](2026-11-04-use-potion-review.md#地图与牌组显示状态的差异)。以下仅记录实现依据。

`MAP-CONTEXT-01`（中；契约一致性）：基础观察文档将 screen.status 定义为 scene 所指房间的可见／覆盖状态，但 ObservationContext.Visibility 在 map 非空时覆盖为 visible。因此战斗上打开地图实际是 `scene:combat, screen:{status:visible,view:map}`，而牌组／牌堆使用 covered。此差异由覆盖页实测及源码共同确认，不是 use_potion 可以穿透地图；用药门控另行拒绝。

持续维护的[上下文说明](../development/observation.md#场景上下文)已补明实际例外，未改公开返回。地图内容与 summary 本就在 inspect_map 的待核验范围；届时应一并决定是否统一状态含义及迁移相关工具／测试。用户已确认将 screen.status 统一纳入当前实施，其余地图设计仍后续处理；不新增用户 TODO。

## 验证结果与限制

[完整返回目录](2026-11-04-use-potion-examples/README.md)按场景列出 use_potion 的 full/default、错误、目标查询及选择续接。120 份文件逐一与原始证据行及 SHA-256 核对，未截断事件；完整参数、证据位置、原始行号和构建见[清单](2026-11-04-use-potion-examples/manifest.json)。建议先看：

- [单体火焰药水](2026-11-04-use-potion-examples/basic-34-use_potion.full.json)、[格挡药水](2026-11-04-use-potion-examples/basic-35-use_potion.full.json)。
- [技能药水的选择边界](2026-11-04-use-potion-examples/skill-03-use_potion.full.json)。
- [火堆喝果汁](2026-11-04-use-potion-examples/noncombat_rest-03-use_potion.full.json)、[商人投掷](2026-11-04-use-potion-examples/merchant-03-use_potion.full.json)、[假商人进入战斗](2026-11-04-use-potion-examples/fake_merchant-04-use_potion.full.json)。
- [无关槽位禁用后，自动药水漏报](2026-11-04-use-potion-examples/journal_boundary-04-end_turn.full.json)；前后观察证明实际消耗与存活，文件见样本清单。

游戏内完成 30 类不同场景／边界，所选成功用例包含 207 次真实 MCP 调用；六次独立游戏进程、共 35 次用例尝试中，30 次完成验证及清理。其余五次保留原始报告，不算通过：奖励页用药步骤通过但局间收尾超时；两次覆盖测试分别错误要求关闭工具具备玩法许可、错误使用未打开页面的空弃牌堆；一次将地图状态误断言为 covered，查明 MAP-CONTEXT-01；一次误要求首场战斗生成 combat_started。修正测试均依据现行实现与契约，未降低用药、恢复或事件断言，也未改生产代码。

奖励页收尾改为原生 proceed；覆盖页先正常打出 Defend，再确认实际 screen.view；地图按当前 view 检查，状态差异另行报告；假商人按首场战斗的抽牌与停止边界核验。各次失败目录与后续独立复测目录均保留在任务证据下。六个自有游戏 PID 已确认退出，没有操作正式游戏或安装 Mod。

完整 Python 集合 653 项通过（42.388 秒）；专项 35 项通过。专项在沙箱内达到 45 秒超时后，按已知本地 socket 限制在沙箱外重跑，同一集合 1.463 秒通过；超时日志保留，不算测试通过。合入 main 前另有 653 项 Python、114 项 C# 通过，快进后提交及代码树相同；本任务没有修改 C#，未重建 DLL。证据见 `.tmp/2026-11-04-use-potion-review/` 的 python-final.log、python-focused-outside.log、merge-verification.json、verification.json 及 processes.json。

本次没有自然注入超时、事件缓冲截断、RitsuLib 缺失、真实多人及第三方目标类型。父事件／先古之民忙碌、模态、过渡与部分非玩家阶段仅按共用门控和原生源码核对；不能用普通战斗成功代替这些边界的实测。完整程序通过不等于每种原版药水效果都单独验证。
