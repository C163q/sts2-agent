# 生物退场与观察稳定修复

当前状态：修复与验证完成，Mod 0.32.0 已备份安装；正式游戏进程未重启，须完整重启后加载新 DLL。

## 基线与复现

游戏 Linux v0.107.1，分支 v0.107.1，提交 59260271（2026-06-18）；RitsuLib 0.6.10 的 0.107.1 兼容运行时。代码基线 `f96364e`，修复版本 Mod 0.32.0，MCP 0.27.0、schema 16 保持不变。

实测记录中，打击击杀一名敌人后返回 `player_ready/complete=true`，下一张防御得到 `stale_state`。原始击杀响应仍包含退场敌人，其生命、格挡、能力和意图已隐藏。保留原始 JSON 序列化，仅删除该敌人条目重新计算 SHA-256，即与异常后截图携带的令牌一致。防御请求在校验阶段拒绝，没有提交出牌。

根因是死亡任务独立于卡牌逻辑动作：队列为空、牌堆飞行结束后，死亡画面仍可暂时保持静态，然后淡出并移除节点。原先连续 250 毫秒观察不变的判断未覆盖这段未来变化。

## 当前版本原生依据

证据来自游戏安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`：

- `CreatureCmd.Kill` 启动 `NCreature.StartDeathAnim`，在需要移除时调用 `NCombatRoom.RemoveCreatureNode`，不会等待整个视觉退场。
- `NCombatRoom.RemoveCreatureWhenGone` 等待 `DeathAnimationTask`，节点暂存于 `RemovingCreatureNodes`；`CombatObservation` 会读取其中仍可见的生物。
- `NCreature.AnimDie` 等待原生动画、淡出与 `IDeathDelayer`，随后释放节点。复活型敌人的死亡任务可以完成并保留非空引用。
- `NCreature.AnimDisableUi/AnimEnableUi` 的 Tween 有延迟，且原生没有保存字段；`RevealIntents`、缩放等有限 Tween 有可检查字段。
- `NCreatureStateDisplay.AnimateIn(SpawnedAtCombatStart)` 有 1.3–1.7 秒延迟后才显示生命条；`_showHideTween` 保存其生命周期。生命数字、格挡及能力图标也有各自有限渐变。
- `NChooseACardSelectionScreen.SelectHolder` 在打开超过 350 毫秒后才接受选择，候选入场 `_cardTween` 持续至 1 秒。过早的选择边界会在稍后新增 `select_card` 能力，改变令牌。

反编译定位：`.tmp/decompiled/NCombatRoom.cs`、`.tmp/2026-10-30-potions/NCreature.cs`，以及 `.tmp/2026-11-01-action-settling/source/` 下的 `NCreatureStateDisplay.cs`、`NHealthBar.cs`、`NPowerContainer.cs`、`NPower.cs`、`NPotion.cs`、`NChooseACardSelectionScreen.cs`。程序集 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；程序集与反编译产物不纳入 Git。

## 修复与相似问题审查

`CombatMotion` 在当前活动及退场节点中检查未完成的死亡任务、意图、缩放和有限状态显示过渡；对未保存引用的两个原生 UI 渐变只记录其返回 Tween。共用 `ActionObservation` 将这些检查纳入原有等待，结束后重新开始 250 毫秒稳定窗口，不修改游戏状态或令牌算法。

新增隔离夹具在真实获得格挡时触发原生生命条出生渐变。卡牌动作的飞牌等待掩盖了该延迟；不含飞牌的格挡药水则复现了 `player_ready` 后继续出牌得到 `stale_state`。补充生命条 Tween 等待后通过。这个夹具用于隔离原生生命周期，不能据此声称普通玩家喝格挡药水必然触发出生渐变。

还发现三选一的时序缺口：实际“发现”返回中缺少 `select_card`，随后纯查看的采样令牌已变化。两次单张连续选择未复现；五张“发现”夹具在第二张的下一次选择真实得到 `stale_state`。将奖励选牌已有的候选可选及入场 Tween 检查复用于 `choose_one`，保持其余选择类型及父任务暂停规则。

相似流程审查结果：

| 流程 | 检查结果 |
| --- | --- |
| 出牌、药水、结束回合、选牌后结算、进入战斗 | 共用动作等待，本次一起覆盖生物有限过渡 |
| 死亡后复活、转阶段 | 使用任务 `IsCompleted`，不以非空引用持续阻塞；待输入选择仍优先停止 |
| 奖励、宝箱、商店、休息处、先古之民及事件 | 已有原生选项任务、遗物获取、购买、页面渐变和资源等待；未确认新的独立缺陷 |
| 地图与跨幕 | 已检查输入屏蔽、页面补间、换幕任务与战斗入场；本次保留原规则 |
| 结算 | 已跟踪原生计分/页面有限 Tween；本次保留原规则 |
| 血条缓降图形、悬停、骨骼循环、粒子 | 已核对部分效果只改变未导出的图形，或不跨可见阈值；不扩大为等待所有动画 |

保留 25 秒超时、取消、真实状态过期及人工输入边界，不刷新令牌后自动重发动作。读取观察和截图仍读取当时画面，不额外承诺稳定等待。

## 验证与限制

证据目录 `.tmp/2026-11-01-action-settling/`：`gui-card-red.json`、`gui-ui-potion-red.json`、`gui-choice-chain-red.json` 分别记录退场、延迟生命条及三选一的真实失败；最终通过证据为 `gui-choice-chain-green.json` 和 `gui-release-*.json`，汇总见 `release-matrix.json`。

- 完整 Python 275 项通过，C# 24 项通过；发布构建 0 警告、0 错误。
- 最终 DLL 的 15 类图形回归通过：五次发现连续选择、卡牌击杀、药水击杀、延迟生命条、实验体转阶段、千足虫复活、十动作连续链、暴政、战斗胜利、奖励、商店、锻造、宝箱、Boss 跨幕及死亡结算返回主菜单。十动作链在外部状态改变前只调用一次观察；外部操作仍会触发 `stale_state`。
- 最终 DLL SHA-256 为 `c8a66ea0fa977f82e2030111330ada2410a53c27e5b657124261c05d9e217a58`，构建、隔离运行与安装一致；备份及安装哈希见 `install.json`。RitsuLib 未改动。

前一候选的奖励回归被旧 MCP 0.26.0 常量断言阻断，移除该无行为意义断言后最终奖励回归通过；完整动作链中的同类旧断言也已移除。三张旧验证器复制的 Discovery 截图来自陈旧缓存，已移入 `unverified-screenshots/` 并排除截图证据；对应动作响应有效，后续启用实时测试捕获，MCP 截图工具的文件不受影响。

独立只读审阅未发现 Critical/Important 问题；一项测试覆盖命名意见要求 phase 模式证明实际转阶段，已补充对应目标的隐藏、复活事件和恢复生命断言并通过；三选一增量审阅无新增问题。

这些验证不能证明所有怪物、多人模式、第三方 Mod 或所有游戏机制均已覆盖；完整自动通关仍须实际测试。
