# 药水动作与目标查询依据

核对日期：2026-10-30。基线为 Linux 游戏 `v0.107.1`、分支 `v0.107.1`、提交 `59260271`，程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。依赖 RitsuLib `0.6.10`，源码提交 `772f280964f2efc7c7e2f29fc59844e68616dd57`；新增药水动作使用游戏接口，战斗事件沿用已接入的 RitsuLib 生命周期。

## 已核实的原生流程

证据均来自上述程序集；本地摘录保存在不纳入 Git 的 `.tmp/2026-10-30-potions/`。

- `NPotionPopup._Ready/RefreshButtons`：区分 `CombatOnly/AnyTime/Automatic`；手动使用受自定义可用性限制，使用和丢弃都受 `Player.CanRemovePotions`、死亡及排队状态限制。自动药水不能手动喝。`RefreshButtons` 不重复检查所有初始化条件，查询应依据新建菜单的条件，不依赖旧菜单缓存。
- `NPotionHolder.UsePotion`：`AnyEnemy/TargetedNoCreature` 或 `CanThrowAtAlly()` 才进入选目标。`Self` 明确传玩家生物，其他直接用的药水传 `null`。
- `PotionModel.CanThrowAtAlly`：仅 `AnyPlayer`、玩家数大于 1 且战斗正在进行时为真。因此多人战斗外果汁仍直接用于自己。
- `PotionModel.EnqueueManualUse`：可合法用于自己时把空目标补为自己，设置排队标记，创建 `UsePotionAction` 后交给同步队列；不能套用卡牌 `Self` 必须空目标的规则。
- `UsePotionAction.ExecuteAction`：战斗中按战斗 ID 解析目标，战斗外按玩家 ID 解析；执行前检查 `IsValidTarget`，不会重新检查全部菜单可用性，外部动作入口须先检查。
- `NPotionPopup.OnDiscardButtonPressed`：禁用槽位后提交 `DiscardPotionGameAction`。该动作调用 `PotionCmd.Discard`，维护原生记录、移除事件与 `AfterPotionDiscarded`。
- `NTargetManager`：单目标生物须存活、可命中且符合 `Hook.ShouldAllowTargeting`；群体目标范围不等于全部效果作用对象。
- `FruitJuice/BloodPotion`：`AnyTime + AnyPlayer`；`FairyInABottle`：`Automatic + Self`。
- `FoulPotion`：战斗中为 `AllEnemies`，实际伤害含非宠物玩家；战斗外为 `TargetedNoCreature`，须原生商人按钮存在且商店库存页关闭，支持普通商店和假商人事件。范围查询不能把群体指示范围当成伤害预测。

- 已遍历该版本 64 种原版药水类（含 DeprecatedPotion），目标仅涉及 `Self/AnyPlayer/AnyEnemy/AllEnemies/TargetedNoCreature`；汇总在 `potion-types.json`。
- 原生商人按钮的 `SelfModulate.A` 为 0，图像由子节点绘制；仅按点击区自身透明度判断会错误排除可见商人。目标查询检查子图像可见性，且不穿透地图或库存页。

## 本次设计

目标是让 LLM 完成当前玩家可执行的药水使用和丢弃，保留观察边界、原生动作及一次观察许可。开发者根据授权决定以下接口；不增加独立瞄准阶段，不读取未来随机选项。

在“扩展现有目标工具”和“另增药水专用目标工具”中选择前者：卡牌和药水复用请求入口与目标列表约定，内部保留各自规则，避免重复工具。逐步点击药水菜单并另行选目标会增加中间状态及取消成本，本次不采用。

- `inspect_targets` 接受 `card_id` 或从 0 开始的 `potion_slot`，恰好一个。卡牌响应保持原格式；药水响应包含 `potion: {slot_index, name}`、`usable`、`discardable`、`target_type`、`requires_target`、`targets`、`reason`。`reason` 表示不能使用的原因，丢弃合法性单独报告。查询不改 UI、不消耗随机数、不建立动作许可。
- `use_potion(potion_slot, target_id?)` 与 `discard_potion(potion_slot)` 独立。仅 `requires_target` 时必须指定目标，即使只有一个候选。战斗生物沿用整数 ID；战斗外自己为只读引用 `self`，商人为 `merchant`，只有商人需要显式字符串目标。额外目标拒绝，不静默忽略。
- 正常单人战斗支持；战斗外读取当前可见且可交互顶栏，并支持无遮挡的事件、休息点、商店、地图及奖励页。选牌、查看选牌背后的战场、其他卡牌页、模态、过渡、忙碌队列及真正多人会话不能执行药水动作。读取详情仍可在此前支持的选牌战场查看状态使用。不能用内部状态补出被挡住的内容。
- 顶栏观察补充实际显示的生命与最大生命，战斗外保持 `player/enemies/turn/buttons` 为空，避免伪造完整场景观察。主菜单不暴露上次对局的顶栏。
- 使用沿用 `EnqueueManualUse`，丢弃沿用 `DiscardPotionGameAction`；跟踪确切入队动作及取消事件。战斗中复用事件记录与选择/胜负边界，战斗外完成时返回 `action_completed`；不等待被选择挂起的完整任务。所有动作消耗观察许可，失败/超时后重新观察。
- 事件记录补充 `potion_used/potion_discarded` 与药水来源，不附送药水正文。药水自动触发发生在其他动作期间也按公开事件记录；空槽不压缩，换槽后旧观察不能误操作另一瓶。

真正多人联机、自定义目标类型及其他 Mod 新增行为未纳入本次实现。已核实的多人原生规则仅作后续依据，不描述为已支持联机。

## 验证要求

先以边界测试复现缺失工具、药水参数和响应投影，再实现。真实隔离游戏覆盖自用、单目标、群体伤害、战斗外果汁/血瓶、自动药水拒绝及丢弃、禁止移除、空槽/越界/错误目标/旧令牌、选牌中止与返回、商人特殊目标、胜利/死亡和只读不变性；图形及真实 stdio 验证关键流程。运行全部 Python 与 C# 检查、构建，交付明确未验证范围。最终实现契约和证据另链接到持续维护说明。
