# 同次动作的战斗记录交接

第七阶段已完成：371 项 Python、60 项纯 C# 和最终 DLL 的 10 个中文图形场景分批通过，包含 19 项交接原生检查及 49 项充能球回归。统一日志作用域、重置前释放、后续战斗启动采集及边界切换已接入；独立审阅无确认问题，暂无阻塞。

## 适用基线与原生证据

核对日期为 2026-11-01，游戏 Linux `v0.107.1`、release `59260271`，RitsuLib `0.6.10` 的兼容运行时。Mod `0.42.0`、MCP `0.40.0`、底层 schema `24`；当前行为维护在[事件契约](../development/end-turn.md#事件语义)。

证据来自游戏安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。忽略目录 `.tmp/2026-11-01-combat-handoff/source/` 保存本次定向反编译；`callers.txt` 为全程序集 IL 调用扫描结果，扫描工具只读程序集。

| 类型与成员 | 已核实的约束 |
| --- | --- |
| `CombatRoom.StartCombat` | 先创建或转换原生房间 UI，再 `SetUpCombat`，最后 `AfterCombatRoomLoaded` 启动任务 |
| `CombatManager.SetUpCombat` | 要求旧状态已重置，重建玩家战斗状态、牌堆及网络卡牌映射 |
| `CombatManager.StartCombatInternal` | 原生 UI 与新战斗状态已存在；等待执行器后触发开场及首回合 |
| `CombatManager.Reset` | 取消旧任务、清空历史与生物状态；其清理不应被当作新效果 |
| `RunManager.EnterRoom/EnterRoomWithoutExitingCurrentRoom` | 异步进入房间；建立或恢复父房间的流程与普通地图推进不同 |
| `CombatManager.EndCombatInternal` | 胜利及结束通知按原生流程发生；同场复活与阶段变化不更换 `CombatState` |
| `ActionExecutor.FinishedExecutingActions` | 队列没有当前执行任务时即可完成，不能用于证明暂停选牌中的原 `GameAction` 已完成 |
| `DecimillipedeSegment.GenerateMoveStateMachine`、`ReattachPower.DoReattach` | 死亡后先执行空的 `DEAD_MOVE`，下一敌方回合才执行治疗意图 `REATTACH_MOVE`，不是一回合后立即复活 |
| `Armaments.OnPlay`、`ChoicesParadox.AfterPlayerTurnStart` | 分别验证已有动作暂停选牌后恢复，以及新战斗首回合等待原生选择 |

当前没有确认原版普通卡牌在一次动作中直接连开两场战斗的路径。双 Boss 与事件战斗通常经奖励、选项或地图分次推进。本阶段验证的是通用记录器交接能力；隔离夹具通过原生房间 API 构造替换，不将其描述为某张原生卡牌的效果，也不自动跨过玩家选择。

## 实现与公开边界

`CombatJournalScope` 替代仅处理首场进入的 `CombatEntryCapture`。每次游戏动作管理一个统一作用域，已有战斗立即接入，出牌、结束回合、药水和选牌处理器均借用其记录器。原生重置前刷新、释放旧记录器，避免旧格挡清零、历史清理等进入效果日志；新战斗启动时先同步卡牌 ID，再建立新记录器。

房间进入任务与战斗启动期间不提前返回旧战斗胜利、普通完成或暂时的 `interrupted`；真实选择和人工输入仍可暂停。新战斗采用自己的可行动、选择或胜负边界，不沿用旧回合号。外部对局身份替换仍中断。伤害结果引用保留到本次动作最终刷新，已经释放的旧日志仍能补齐延后填写的格挡字段。

同次动作已有战斗后再次启动战斗时，预留 `combat_started`，仅含 `sequence/type`。新战场经过绘制且可读后发布，分隔后续事件的角色和卡牌 ID 作用域，不附送遭遇名、敌人列表、隐藏数值或未来结果。未展示的标记在本次动作结束或再次替换时丢弃，后续请求不补发。从战斗外进入首场战斗、同场复活、阶段变化及新回合不产生该标记。所有日志仍共用 512 个位置的缓冲；不新增公共工具、强制观察或自动重试。

绘制完成计数由 `OrbCapture` 移至 `VisibleUi`，与充能球入场判断共用；仍在主线程采样，图形模式使用 `FramePostDraw`，headless 使用过程帧回退。

## 验证与问题处理

所有游戏证据均使用独立中文实例、隔离 IPC 和存档，经真实 stdio MCP 调用；未接触正式游戏进程或安装。证据位于 `.tmp/2026-11-01-combat-handoff/`。

- 协议 `python-red.log` → `python-green.log`：3 项检查覆盖多个战斗复用卡牌 ID 时的日志保留、隐藏字段过滤，以及标记禁止携带其他玩法字段；旧实现有 6 个未知类型错误，接入后通过。
- `red-gui/`：旧 DLL 在原生替换后返回 `interrupted/complete:false` 与被覆盖画面，缺少新开场抽牌，还错误记录旧格挡 5→0 的重置清理。
- `green-gui/`：出牌和结束回合通过。选牌用例暴露夹具等待条件过早；核对 `ActionExecutor` 后改为先等原 `GameAction.State` 完成，避免在真正选牌前替换。
- `choice-gui/`：真正选牌完成后的父动作恢复，以及新战斗开场选择均通过；选择可继续，后续动作无需额外观察。
- `checks-gui/`：19 项原生检查通过，包含同次两次替换、重置清理排除、五张新开场抽牌、ID 与实际手牌对应、旧状态失效、单次有效订阅、同场新回合不重建、共享上限、隐藏标记不补发及异常释放。
- 独立只读审阅核对原生入口、统一等待、ID 同步、订阅释放和共享缓冲，未发现确认问题。最终验证结果见下表。
- `final-gui/` 的前 8 个用例通过；同场复活回归暴露旧验证器把 `DEAD_MOVE` 与 `REATTACH_MOVE` 当成同一次敌方回合。已核对目标程序集与实际公开治疗意图，改为两个明确的结束回合，并断言期间不出现新战斗标记；未修改游戏复活行为。

最终验证：

| 检查 | 结果与证据 |
| --- | --- |
| 完整 Python | 371 项通过，`python-final.log`；GUI 结束后沙箱外有界运行 |
| 纯 C# 回归 | 60 项通过，`csharp-final.log` |
| Mod 构建 | 0 警告、0 错误，`build-final.log` |
| 最终 DLL 中文图形 | 10 个场景分两批通过：`final-gui/` 前 8 项，修正验证器后 `remaining-gui/` 的同场复活及事件回归 2 项；汇总见 `verified-summary.json` |
| 交接与生命周期 | 19 项原生检查全部通过，`final-gui/checks/verify/evidence.json` |
| 相邻回归 | 药水和选牌首场入战、49 项充能球边界、同场死亡／复活及事件资源全部通过 |

两批使用同一 DLL，SHA256 为 `6de73d20d50c95da49a3df4bceaf3a30cef1f860f9931d5ca7975b261642eced`，与构建产物及隔离运行时副本一致；两个自有进程均已退出。实际精简回执保存在忽略目录 `handoff-receipt.json`。更新需要同时替换 DLL／清单和 Python，重启游戏并重连 MCP；本阶段没有更新正式安装。

## 未验证范围

不承诺任意第三方 Mod 绕过原生重置／启动入口后仍能自动交接，未进行完整自主通关或正式安装。事件种类本身仍有[覆盖审查](2026-11-01-transition-event-coverage.md)所列的其他缺项，`complete:true` 仍不证明记录了所有效果。
