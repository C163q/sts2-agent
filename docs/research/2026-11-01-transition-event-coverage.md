# 动作事件记录覆盖审查

本文件保留 `a06fe7b` 基线的覆盖审查；下列表格描述修复前的实现。后续已启动分阶段处理，第一阶段的 HP、最大生命和金币共用记录及各类动作接入见[实施与验证记录](2026-11-01-run-resource-events.md)。物品和卡牌永久变化等缺口仍待后续阶段。

## 问题与基线

问题指成功动作已有 `transition.stop_reason`、`complete`，但 `transition.events` 为 `[]`，并非整个 `transition` 缺失。空事件不能据此解释为动作没有产生效果。

核对日期为 2026-11-01，代码基线为 `a06fe7b`：Mod `0.35.0`、MCP server `0.33.0`、原始观察 schema `17`。复核的图形证据使用 Linux 游戏 `v0.107.1`、release `59260271`、RitsuLib `0.6.10`；本轮没有重新核对游戏程序集 API 或正式安装状态。

## 根因

现有主要记录器 `TurnJournal` 依赖战斗上下文。多数战斗外动作只等待交互边界，然后直接写入 `events = Array.Empty<object>()`；`EventTaskTracker` 等任务跟踪器负责判断结算是否结束，不负责记录效果。

`choose_event_option` 和 `travel_to_node` 使用 `CombatEntryCapture`，后者仅在战斗启动时创建 `TurnJournal`。未触发战斗时回退为空事件；开始战斗前已经发生的战斗外效果也不在该记录范围内。

Python 的 `action_output.action_result` 保留已验证的整个 `transition`，没有在精简回执时删除事件。`transition_details.end_turn_details` 要求完整停止字段，并校验已有事件类型；它允许空数组。因此需要补齐游戏侧采集与协议类型，而非只修改工具提示或输出预设。

## 21 个游戏动作的覆盖

工具范围来自 `scripts/available_tools.py` 的 `GAME_ACTIONS`。以下三类共 21 个：12 个固定空事件、5 个依场景使用空记录路径、4 个具有记录器的战斗／药水动作。

### 固定空事件的 12 个动作

| 工具 | 当前行为及缺口 | 实现 |
| --- | --- | --- |
| `choose_ancient_option` | 领取或替换遗物及附带效果没有事件记录 | `GameAdapter.Ancient.cs` |
| `advance_dialogue` | 先古之民与终章对话均为空事件；纯对话推进可合理为空 | `GameAdapter.Ancient.cs`、`GameAdapter.RunEnding.cs` |
| `choose_rest_option` | 休息回血、挖掘等直接效果没有事件记录；打开锻造选牌时尚未实际升级 | `GameAdapter.RestSite.cs` |
| `claim_reward` | 仅另有 `reward_result` 表达领取状态，没有具体所得及附带效果记录 | `GameAdapter.Rewards.cs` |
| `buy_item` | 仅另有 `purchase_result`，没有支付金币、所得物品及附带效果记录 | `GameAdapter.Shop.cs` |
| `open_shop`、`close_shop` | 固定为空；单纯展开或收起页面可合理为空 | `GameAdapter.Shop.cs` |
| `loot_treasure` | 取得遗物及附带效果没有事件记录；仅开箱不一定产生物品变化 | `GameAdapter.Treasure.cs` |
| `set_divination_tool`、`divine` | 切换工具、揭开棋盘和相关结算均无事件记录；单纯切换工具可合理为空 | `GameAdapter.Divination.cs` |
| `respond_to_confirmation` | 确认或取消事件弹窗没有效果事件；失败仍可由停止原因表达 | `GameAdapter.Confirmation.cs` |
| `run_result_option` | 结算与解锁页面操作为空事件；纯页面操作可合理为空 | `GameAdapter.RunEnding.cs` |

表中 C# 文件均位于 `spikes/roundtrip/`。固定空表示当前实现不采集，不表示这些动作每次都应产生非空事件。

### 依场景落入空记录路径的 5 个动作

| 工具 | 已有记录范围与缺口 |
| --- | --- |
| `choose_event_option` | 仅通过 `CombatEntryCapture` 记录触发战斗之后的受支持事件；扣血、治疗、金币、物品及卡牌永久变化等战斗外效果未记录 |
| `travel_to_node` | 仅通过同一记录器捕获进入战斗后的受支持事件；进入非战斗房间及其即时效果没有通用记录 |
| `select_card`、`selection_option` | 调用开始时已经处于战斗才创建 `TurnJournal`；战斗外加牌、删牌、升级、附魔、变牌、献祭与重掷均为空。后续父流程触发战斗时也不会自动接入 `CombatEntryCapture` |
| `proceed` | 根据当前页面分派至事件、奖励、休息处、宝箱、商店、先古之民、占卜或终章处理器；大多使用固定空事件，事件路径可记录随后进入战斗的事件。恢复父事件的后续效果也受所在处理器限制 |

### 有记录器的 4 个动作仍存在类型缺口

- `play_card`、`end_turn` 使用 `TurnJournal`，覆盖当前已支持的战斗事件，不是完整状态差量。
- `use_potion`、`discard_potion`：战斗中使用 `TurnJournal`，战斗外仅使用 `PotionJournal`。后者只记录已知药水的 `potion_used`、`potion_discarded`，不记录治疗等实际效果；`PotionProcured` 订阅仅用于记住槽位，不会生成取得药水事件。
- 战斗外 `FoulPotion` 触发假商人战斗的分支只补充战斗停止条件，没有切换到 `TurnJournal` 或使用 `CombatEntryCapture`，因此可能缺少该战斗开始期间的效果记录。

## 事件类型的共通缺口

`scripts/transition_details.py:FIELDS` 当前支持伤害、HP、格挡、power、生物生命周期、出牌／抽牌／弃置／消耗／公开加牌，以及药水使用／丢弃。

以下内容尚无对应的专用事件类型：金币、最大生命、能量、星星变化；遗物和药水取得／失去；卡牌永久删除、升级、附魔、变牌及牌面费用／数值变化。某项效果附带的 HP 或其他已支持变化可能被部分记录，但不能据此还原完整效果。例如战斗中确认武装升级也未必产生升级事件。

`TurnJournal` 已订阅牌组加牌并在卡牌实际公开展示后尝试记录 `card_added`，不能将其描述为完全不记录永久入牌；它没有提供通用的全部牌组修改日志。

`complete:true` 仍表示已经到达所声明的停止边界并满足现有缓冲条件，不证明记录了全部效果。基础观察和专项详情本来不回放动作事件，页面查看工具也不承诺返回 `transition`。

## 可定位证据

源码入口：

- [事件动作](../../spikes/roundtrip/GameAdapter.Event.cs)、[进入战斗的采集](../../spikes/roundtrip/CombatEntryCapture.cs)、[旅行](../../spikes/roundtrip/GameAdapter.Navigation.cs)。
- [选牌动作](../../spikes/roundtrip/GameAdapter.Selection.cs)、[药水动作](../../spikes/roundtrip/GameAdapter.Potions.cs)、[药水记录器](../../spikes/roundtrip/PotionJournal.cs)、[战斗记录器](../../spikes/roundtrip/TurnJournal.cs)。
- [Python 事件校验](../../scripts/transition_details.py)、[精简回执](../../scripts/action_output.py)、[动作分类](../../scripts/available_tools.py)。

复核的已有真实 stdio MCP 图形证据位于未纳入 Git 的 `.tmp/2026-11-01-selection-presets/`：

| 路径 | 已观察事实 |
| --- | --- |
| `gui/smith/verify/evidence.json` | 打开锻造、选中痛击、确认完成升级的动作均为空事件 |
| `gui/ancient_multi/verify/evidence.json` | 先古选项、选择三张牌、确认附魔的动作均为空事件 |
| `completed-rewards-gui/paels_wing/verify/evidence.json` | 献祭与另一份奖励选择卡牌成功后均为空事件 |
| `completed-rewards-gui/driftwood/verify/evidence.json` | 重掷及随后取得卡牌成功后均为空事件 |

这些证据沿用[选择预设验证](2026-11-01-selection-presets.md)的独立实例和已通过场景，不算本轮新增测试。其他表项由静态实现确认，尚未逐个重新运行图形场景。

## 后续切入点与约束

候选方向是先设计共用的战斗外效果记录及缺失事件类型，再接入各动作，并处理与战斗记录器的交接，减少逐个事件特判。具体命名、字段、订阅方式及版本策略尚未决定。

继续实施前须核对目标游戏程序集或源码中的真实通知和生命周期，确定公开 HP／最大生命、金币、物品与卡牌永久变化的采集点。仅凭动作前后快照可能漏掉中间变化和先后顺序；仅凭选项正文推断也不能证明效果已经发生。期间事件仍遵循可见信息边界，不读取未公开卡牌、未来随机结果或隐藏物品。

设计需覆盖连续选择、父事件暂停与恢复、事件／选牌／药水后进入战斗、返回奖励或地图、取消、超时和异常；同时避免重复订阅、重复记录或与 `TurnJournal` 重复计数。复用现有游戏线程、动作稳定等待和许可规则，不额外引入每步必须 `get_observation` 的要求，也不自动重试游戏动作。

实施及回归应区分真正产生效果的动作和纯 UI 操作；前者验证具体事件，后者允许 `events:[]`。新的类型需要同步 C# 采集、Python 字段投影与验证、协议说明及真实图形验证。第一阶段范围和当前进展以开头链接的记录为准。
