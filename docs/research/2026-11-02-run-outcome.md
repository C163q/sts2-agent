# 终章胜负停止原因修复

当前状态：已完成。共 3 项，已完成 3 项；停止原因修复、文档、Python 404 项、C# 60 项、构建及 3 个隔离图形场景均通过，独立审阅完成。无剩余实施项和阻塞，未安装正式 Mod。

## 要求与实现计划

1. 补充 Python 回归测试及原生结算验证：胜利接受 `run_won`，保留剧情 HP 归零事件和 `Victory...?`；普通事件死亡仍为 `run_lost`，建筑师对话和后续翻页仍为 `action_completed`。
2. 在 `RunResultInspection` 读取原生结算界面选择横幅使用的 `_history.Win`；`NonCombatBoundary` 仅在结算页就绪后返回对应胜负。结算翻页关闭胜负报告，继续使用 `action_completed`。Python 接受新增枚举，不授予终局动作连续执行许可。更新 Mod／MCP 版本及接口说明。
3. 运行 Python、C# 检查和构建；使用独立测试进程验证胜利、战斗死亡与事件死亡，核对实际回执、画面与后续结算流程，审阅后提交。

本次沿用用户已确认的设计并在当前工作区执行，不安装正式 Mod，不操作正式存档。基础观察不新增胜负字段，不提前公开建筑师结局，HP 归零不等于失败；`run_won` 表示原生按胜利结算，不表示击败建筑师。

## 证据与根因

- 核对基线：提交 `4dd7a8c`；Mod／MCP `0.44.0`、schema `25`；Linux 游戏 `v0.107.1`、RitsuLib `0.6.10`。
- 游戏证据：安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- `RunManager.WinRun()` 先调用 `OnEnded(true)`，再执行 `GuaranteeKillAllPlayers()`。`OnEnded()` 的原生重复处理保护不阻止本项目 Harmony postfix 收到之后的调用；`EventTaskTracker` 只记录失败，可能因此将剧情死亡错误解释为本局失败。
- `NGameOverScreen._Ready()` 初始化 `_history`；`InitializeBannerAndQuote()` 依据 `_history.Win` 选择 `BANNER.falseWin` 或失败横幅。因此读取相同判据不会增加 UI 之外的胜负信息。不能按标题字符串、进阶解锁文字或玩家当前生命猜测结果。
- 实测反馈：工作区外 `playtest-2026-11-02-r10/outcome-observation.txt` 与 `evidence-part-8.json` 第 345～347 步。`proceed` 返回 `run_lost` 及 HP 25→0，但当前结算显示 `Victory...?` 和 `Ascension 7 unlocked!`。
- 原终章文档已要求不能因剧情 HP 归零改判失败，实际停止原因却仍为 `run_lost`。本次修复实现并补充明确的 `run_won` 契约；事件文档同步说明已显示结算的胜负优先于剧情死亡回调。
- 相关源码：`src/Sts2Agent/Actions/EventTaskTracker.cs`、`src/Sts2Agent/Adapter/GameAdapter.Rewards.cs`、`src/Sts2Agent/Observation/RunResultInspection.cs`。目标 DLL 反编译证据保留在忽略目录 `.tmp/2026-11-02-available-actions/source/`，本次已核对 DLL 哈希一致。

## 验证记录

Python RED：新增测试在旧枚举校验处报 `Invalid turn transition`。原生 GUI RED：旧 DLL `502fd377…17d2` 在胜利最后 `proceed` 返回 `run_lost`，触发新增 `run_won` 断言；实际 HP 80→0 事件完整保留。证据位于 `.tmp/2026-11-02-run-outcome/gui-red/`，自有进程 PID 12005 已关闭。

当前 Python 完整检查 404 项通过（33.521 秒），构建 0 警告、0 错误。C# 60 项通过；最终 DLL 为 `873ac2689d7ee3d1f94e6cf767f5cf4a07965f3881d95f14991daac7fa8211a3`。独立只读审阅未发现功能问题，两处当前版本说明已同步。新版 `victory_unlock` 完整通过：末次 `proceed` 返回 `run_won`、HP 80→0、标题 `Victory...?`，结算就绪；直接操作下一页被要求重新读取，后续统计、解锁与返回菜单均为 `action_completed`。

3 个图形场景均通过，证据位于 `.tmp/2026-11-02-run-outcome/gui-green/`：

| 场景 | 调用数 | 结果 |
| --- | --- | --- |
| `victory_unlock` | 106 | 建筑师对话未提前判胜，末次前进为 `run_won`；统计、21 个解锁流程页面及返回菜单成功 |
| `death` | 45 | 原生普通死亡显示失败横幅；后续翻页及返回菜单均为 `action_completed` |
| `event_death` | 48 | 原生事件致死返回 `run_lost`，保留最大生命及 HP 变化；后续结算及返回菜单成功 |

胜利与事件死亡首屏截图已人工核对。三个自有进程 PID 13481、14017、14234 均已关闭；最终验证使用同一 DLL 哈希。文档内部链接与代码块闭合检查通过，Git 空白检查通过。

未验证多人、第三方结算 UI 改写、每日挑战榜单或正式存档；没有重新跑所有图形烟雾场景。基础观察字段、动作许可和真实结算流程不扩展。Mod／MCP 更新为 `0.45.0`、schema `26`，使用时需替换正式 DLL／清单并完整重启游戏，更新 Python 后重连 MCP。

当前接口说明见[终章与一局结算](../development/run-ending.md)。
