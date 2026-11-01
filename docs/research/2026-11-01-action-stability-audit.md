# 动作回执后的令牌稳定性审查

当前状态：修复、同类链路审查及验证完成。Anger 原故障已在旧实现复现；修复后八个新增稳定性用例、既有场景和退场回归共 21 局、22 步全部通过。独立只读审阅未发现需修正的问题。`summary` 预设不在本次范围；正式安装状态见末节。

## 基线与实玩证据

- 日期：2026-11-01；代码基线 `133e0fd`；Linux 游戏 `v0.107.1`、RitsuLib `0.6.10`、观察结构版本 16。
- 输入：`~/Program/workspace/tmp/sts2/playtest-2026-11-01/summary-notes.txt` 及同目录 `evidence.json`，不采用其 `lagecy/` 旧记录作为本次证据。
- 原始 IPC 响应位于 `.tmp/live/ipc/responses/`。`741080410b8a49bb8b0036710194fc28.json` 是 Anger 成功回执；`5df147ebc5e24fb9b752a0a7b0c4afbb.json` 是失败后读取的状态。两者除令牌与战报外，仅弃牌数从 5 变为 6，能量、生命、手牌、敌人、页面和可用工具均相同。

保留原始属性顺序和转义，排除 `snapshot_id` 与附加 `transition` 后，回执正文 SHA-256 与其令牌一致：

```text
684F29589601E6CDB309E324C25C590C54DE6741E10E2ECD68C3A79815EF0583
```

仅将 `discard_count` 从 5 改为 6，即得到失败后观察的令牌：

```text
17282902F87D2C7967E759C13609E9E23B1E17B180B1B8EE6B6BFCF9A8C04BF4
```

核验结果保存在 `.tmp/2026-11-01-action-stability-audit/original-evidence.json`。这两个采样不等于拒绝瞬间的逐帧日志；隔离游戏中的同一路径复现进一步确认了预览等待缺口。

## 根因与修复

核对游戏安装目录内 `data_sts2_linuxbsd_x86_64/sts2.dll`，本次原生证据保存在 `.tmp/2026-11-01-action-stability-audit/source/`，不纳入 Git：

1. `Anger.OnPlay()` 添加副本后调用 `CardCmd.PreviewCardPileAdd(..., 2.2f)`；该调用不等待预览及后续飞牌完成。
2. `CardCmd.PreviewInternal()` 根据牌堆与布局选择容器。全局 UI 有普通、散列、事件、网格四个容器；战斗 UI 另有普通、散列两个容器。卡牌先展示，再由延迟回调创建 `NCardFlyVfx`。
3. `NCardFlyVfx.PlayAnim()` 在到达牌堆时调用 `InvokeCardAddFinished()`，可见牌堆计数到此才更新。逻辑入堆和动作队列清空均早于这一步。
4. 原有 `RunUi.CardPreviewsPending()` 只读取四个全局容器；共用 `ActionObservation()` 还仅在 `combat_won` 时检查它。于是普通出牌在预览期间既没有匹配的飞牌节点，也没有变化的 JSON，连续 250 毫秒不变后即可提前返回。

修复统一检查全部六个原生预览容器，并将预览等待应用于 `player_ready`、`action_completed`、`action_canceled` 和 `combat_won`。检查使用仍在树中且未排队删除的临时卡牌节点，不以当前可见性过滤，因为覆盖或入场中的预览仍会产生后续飞牌。随后沿用飞牌、生物及资源等待和原有稳定判定。

`choice_required` 继续优先返回，不等待被用户选择暂停的父流程。工具名称、参数、观察字段、完整状态哈希、截止时间和客户端不自动刷新重试的规则均保持原有语义。补丁版本为 Mod `0.34.1`，MCP server 仍为 `0.29.0`。

## 同类链路审查

审查沿 `GameAdapter.Observe()` 中参与令牌计算的字段分组，核对数据何时更新、更新前是否存在独立有限流程，以及停止边界的覆盖位置。表中“未发现新增缺口”是本次源码核对结论，不代表已穷举所有卡牌和 Mod 机制。

| 字段或链路 | 核对依据 | 结论与覆盖 |
| --- | --- | --- |
| 抽牌、弃牌、消耗和牌组计数 | `CardPileCmd`、`CardCmd.PreviewInternal`、三类飞牌、`NCombatCardPile`、`NTopBarDeckButton` | 修复延迟飞牌前的六容器缺口；不以内部牌堆数填充观察。牌组标签由完成事件同步更新，缩放补间不改变计数。 |
| 手牌增减、费用、描边 | `NHandCardHolder`、`NPlayerHand`、`NCard`、`CombatObservation.Card` | 原生入手牌流程、完成队列、已覆盖的描边补间及观察稳定共同约束；闪光不改变费用字段。补测真实生成手牌及抽牌。 |
| 能量与最大能量 | `NEnergyCounter.RefreshLabel`、`OnCombatStateChanged` | 标签按状态通知同步更新；资源旋转不改变输出。补测增加能量，不新增对循环动画的等待。 |
| 星星 | `NStarCounter._Process`、`UpdateStarCount` | 显示值有平滑过程；保留真实标签与观察稳定判定，补测实际获得星星后的延迟采样。 |
| 双方生命、格挡、能力与意图 | `NHealthBar`、`NPower`、`NPowerContainer`、`NIntent`、`CombatMotion` | 既有有限补间和死亡任务等待仍生效；能力数字同步刷新，移除节点走队列删除。回归击杀、特殊阶段、延迟生命条和描边。 |
| 顶栏生命、金币、药水、遗物计数 | `NTopBarHp`、`NTopBarGold`、`NPotion`、`NRelicInventoryHolder` | 常规生命及遗物数字按事件更新；金币 `_alreadyRunning` 和药水 `_obtainedTween` 已等待。遗物图标获得动画与计数标签分开；初入涅奥的生命渐显属于初始化读取，普通观察仍不承诺等待。 |
| 奖励、休息处、宝箱、商店 | 对应 `*Inspection.Ready`、`RelicObtainTracker`、`ShopTransactions` | 已检查页面可见性、有限入场、原生按钮、事务与遗物任务；全局预览检查继续复用统一实现。既有图形回归覆盖这些入口。 |
| 先古之民、事件与跨房间任务 | `AncientInspection.Busy`、`EventInspection.Ready`、`EventTaskTracker`、`NavigationTasks` | 已跟踪选择和进入任务、正文显示及按钮入场；未发现本次同源预览以外的新缺口。本次未重跑全部事件和跨幕场景。 |
| 选牌、预览确认与查看战场 | `CardSelection.AwaitingInput`、`SelectionInspection`、`ActionSettling` | 已有禁点时间及网格描边等待；选择优先且不等待作答。回归连续选牌和未结束选择的跨局清理。 |
| 地图、覆盖层、确认弹窗 | `MapView.Ready`、`RunUi.Transitioning`、`EventConfirmation` | 页面及跨幕补间、遮罩和放弃任务已有各自边界；改变查看页面后 MCP 不续接旧许可。未新增行为。 |
| 占卜、终章与结算 | `DivinationTasks`、`DivinationInspection.Ready`、`RunResultMotion`、`RunResultInspection.Ready` | 已识别揭开、正文、计分和解锁过程。占卜临时对白原已排除在许可哈希之外；本次不扩展排除字段，也未重跑全部专属场景。 |
| 会话、对象代际和动作许可 | `Observe`、`BridgeMod`、`scripts/game_tools.py` | 游戏主线程采样，完整状态复核在输入提交前；详情仅保留相同令牌，视图和失败清除许可；会话锁与取消规则不变。真实外部动作仍须使旧许可失效。 |

## 验证及限制

- 修复前：`.tmp/2026-11-01-action-stability-audit/red/`，Anger 成功后等待 3.5 秒窗口，再出牌返回 `stale_state`，新回归按预期失败。
- 首次修复验证：`green/` 中 Anger、TURBO、Blade Dance 通过；Pommel Strike 的令牌采样及后续出牌正常，但新夹具预置三张抽牌堆卡牌时未播放入堆预览，初始显示为 0，导致数量差断言失败。夹具现使用原生预览及有限等待准备可见初始计数，不改写标签或放宽断言。
- 最终图形验证：`final/report.json` 记录固定 21 局、22 步全部通过。八个新增稳定性用例之外，还覆盖连续动作及同局续接、能量耗尽后的描边、连续选牌、未结束选择的清理、锻造、商店、奖励、两类宝箱，以及卡牌击杀、药水击杀、特殊阶段和延迟生命条。自有游戏进程已清理。
- 完整 Python 回归：294 项通过，日志为 `.tmp/2026-11-01-action-stability-audit/python.log`；无游戏 C# 检查 27 项通过，日志为同目录 `csharp.log`。最终 Mod 构建无警告、无错误。
- 冒烟清单更新后的框架单元复查：11 项通过，日志为同目录 `gui-unit-final.log`；独立只读代码审阅未发现需修正的问题。
- 图形报告中的 DLL SHA-256 与最终构建一致：`83a378f425052383952e9846c4d346dc654ca3863b2c437990e68103ff2c0142`，随附清单版本为 `0.34.1`。

新增 `verify_action_stability.py` 经真实 MCP 取得回执，随后按 0、0.25、0.75、1.5、3.5 秒目标时刻调用底层只读观察，并记录实际经过时间；IPC 耗时可能使采样晚于目标。诊断不刷新 MCP 连接保存的许可。每个样本须保持回执令牌，随后须成功续接出牌，并通过外部动作验证真实过期仍被拒绝。六个真实卡牌用例覆盖生成弃牌、手牌、抽牌、生命、能量及星星；另两个夹具以防御触发预置的原生普通/散列抽牌堆预览，覆盖两个战斗容器。Anger 与散列布局已加入默认图形冒烟清单。

本次全部游戏检查使用隔离进程、存档和 IPC，没有推进用户正式对局。没有完成整局通关、所有事件/结算的重新实测或任意第三方异步流程验证。

## 安装状态

核对当前正式安装目录的文件时，DLL SHA-256 为 `a6ff24e0de78bb19a392a0df187126c60bca8fff6ec87503a62bc214c831b4c5`；其 `CombatMotion.Pending()` 尚不含上一轮手牌描边等待。安装文件检查不等于确认实玩记录或当前运行进程加载了哪份程序集。Anger 故障已独立在包含上一轮修复的仓库基线上复现，不能归因于未安装上一轮补丁。

本次未替换正式安装文件。游玩前须按[安装说明](../development/live-game.md#安装文件)一同替换 `Sts2Agent.dll` 和 `Sts2Agent.json`，完整重启游戏以加载 Mod `0.34.1`；只更新 Python MCP 脚本不能更新已加载的游戏内实现。
