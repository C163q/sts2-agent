# 手牌描边渐隐导致动作许可过期

当前状态：修复及验证完成。旧实现已复现 `stale_state`，修复后同一路径连续三局通过；完整图形回归共 15 局、16 步全部通过，无本次遗留检查。

## 基线与原始证据

- 核对日期：2026-11-01；代码基线 `7c8fd58`；游戏 Linux `v0.107.1`、RitsuLib `0.6.10`、基础观察 `schema_version=16`。
- 实测输入：`~/Program/workspace/tmp/sts2/mcp-evaluation-2026-11-01.txt` 及同目录 `mcp-evaluation-artifacts-2026-11-01/interaction-evidence.json`。仅处理第一节的连续动作问题，未实施 `summary` 预设。
- 原始文件响应位于 `.tmp/live/ipc/responses/`：`aa978d2cabe24cc79e013ddbcd8d6a97.json` 为 Dominate 成功回执，`2988e93bbf264b66838661bdf1925870.json` 为随后结束回合的 `stale_state`，`cf9a987e294246f7ac2ae92ebe8f0558.json` 为报错后的观察。

成功回执与报错后观察仅有剩余三张手牌的 `outline` 从 `cyan` 变为 `none`；能量均为 0，生命、力量、敌人、牌堆计数、页面和可用动作均相同。保留原始 JSON 属性顺序和转义、排除 `snapshot_id` 及附加 `transition` 后，回执正文的 SHA-256 为：

```text
766DE7DBE684BB16762AA96808CD45DACB1245A7DCC80B3360E2675B8EECF22F
```

仅将三处描边改为 `none`，得到报错后观察的令牌：

```text
70F5DE809AF529D2B57D9DF25AB0704373D312A128DB2E1DA344FD1CBE7343A6
```

哈希核验保存在 `.tmp/2026-11-01-hand-settling/original-evidence.json`。原始错误未保存拒绝瞬间的完整观察，不能单凭这两个样本确定当时的全部差异；隔离复现进一步验证了该故障路径。

## 原因与修复

游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的以下成员已经核对，反编译证据保存在 `.tmp/2026-11-01-hand-settling/source/`，不纳入 Git：

- `NHandCardHolder.UpdateCard()` 按原生可用性调用描边的 `AnimShow()` 或 `AnimHide()`。
- `NCardHighlight.AnimHide()` 用 `_curTween` 在 0.5 秒内把 shader 的 `width` 减到 0；显示及闪烁也使用同一有限补间。
- `Dominate` 的构造函数、关键词及 `OnPlay()` 确认其费用为 1、带消耗效果，出牌时施加易伤与力量，符合此次 `Bash → Dominate` 耗尽 3 能量的路径。

本项目 `CombatObservation.Card()` 将仍大于 0 的描边宽度投影成颜色，归零后才输出 `none`。因此渐隐中 JSON 可以连续 250 毫秒不变，但补间结束仍会改变完整观察哈希。原有 `CombatMotion.Pending()` 没有检查手牌描边，动作可在补间结束前返回 `player_ready/complete=true`。

修复在共用 `CombatMotion.Pending()` 中检查当前可见手牌的 `_curTween`，待有限补间结束后沿用原有稳定计时。观察仍读取实际画面；完整令牌、合法性复核、25 秒截止及选择优先停止规则保持原有语义。MCP 不自动刷新或重试失败动作。公共等待说明已同步至[动作完成与画面稳定](../development/end-turn.md#动作完成与画面稳定)。

## 验证范围

新增测试场景 `play:energy_chain`：3 能量，手牌为 Bash、Dominate、两张 Strike 及 Defend。`verify_kill_settling.py --scenario energy` 通过真实 MCP 串行查询目标、打出前两张牌，读取对应原始回执，等待 1 秒后直接结束回合；全程只有首次 `get_observation`，没有自动重试。额外等待用于跨过可能残留的渐隐，不授予新许可；回执还须满足能量为 0、剩余描边均为 `none`。该用例已加入默认图形冒烟清单。

- 修复前：`.tmp/2026-11-01-hand-settling/red/`，出牌成功后的 `end_turn` 返回 `stale_state`，回归用例按预期失败。
- 修复后：`.tmp/2026-11-01-hand-settling/green/`，15 局、16 步全部通过。包括同一路径连续三局、连续动作及同局续接、连续选牌、未结束选择的清理、锻造、商店、奖励、附加奖励宝箱及普通宝箱，以及卡牌击杀、药水击杀、Test Subject 特殊阶段和延迟生命条显示。击杀等既有用例还检查外部操作后真实 `stale_state` 仍被拒绝。
- 完整 Python 测试：294 项通过，日志为 `.tmp/2026-11-01-hand-settling/python.log`。
- 无游戏 C# 检查：27 项通过，日志为 `.tmp/2026-11-01-hand-settling/csharp-checks.log`。
- 图形清单更新后的框架单元复查：11 项通过，日志为 `.tmp/2026-11-01-hand-settling/gui-unit-final.log`。
- Mod 构建通过，无警告或错误。测试报告记录的 DLL SHA-256 与当前构建一致：`a50707639af719ce11d77d6e55bf00ffa1b922bf77dd1244ee27cdfded08718e`；自有测试游戏进程已清理。

以上游戏验证使用独立运行时、存档和 IPC；未推进用户的正式对局，未进行整局通关验证，也未替换正式游戏目录中的 DLL。正式游玩前须按[安装说明](../development/live-game.md#安装文件)更新 DLL 并完整重启游戏。
