# 中期游玩反馈开发核验

用户阅读结论见[反馈复核](2026-11-08-mid-playtest-feedback-review.md)。本文保存定位信息；核对基线为 `e1936c1`，Mod `0.81.0`、MCP `0.84.0`、schema 47，Linux 游戏 `v0.107.1`／release `59260271`，RitsuLib `0.6.10`。

## 原始游玩证据

截图 `.sts2-agent/screenshots/run01-13-inklets.png` 显示第 11 层另一场战斗的初始牌面，包含放血和地狱狂徒；`run01-11-combat3.png` 为第 8 层，不能作为第 13 层批次的瞬间画面证据。

已从 `.tmp/live/ipc/responses/` 找到包含报告四项输入与相同拒绝原因的原始响应：

- `646bb3e53f4a45bbb95d6f7b3286c10b.json`：schema 42，session `c9fc6a927d254e03a3f3e3fb56d977f5`，top_bar.floor 为 13。
- batch `9d4f4ab04baa4e3e9687f1b5fb65b72d`：card_id 5 地狱狂徒、2 放血、1 痛击、0 打击；状态分别为 played／played／not_submitted／played。
- 痛击原文 `I don't have\nenough Energy.`；能量事件为 3→1、1→2，最终 player.energy 为 2。
- 原请求文件未保留；以上以实际 card_plays 及事件内容对应反馈，不通过截图推断精确调用时机。

另有三份包含放血的批次，提取于 `.tmp/2026-11-08-mid-playtest-feedback/historical-batches.json`；其中仅地狱狂徒／放血的批次记录 3→1、1→3，与后续立即扣费时的合并差异一致。

## 当前代码与原生判断

| 入口 | 核对内容 |
| --- | --- |
| `GameAdapter.CardPlayRequest` | foreach 同步连续调用 CardSubmissionReason 和 ManualPlayBatch.Submit，提交循环内不 await 上一项结算；最后统一 ActionObservation |
| `GameAdapter.CardSubmissionReason` | 在原生调用之前执行 TargetInspection.Reason（调用 CanPlay）及 CanPlayTargeting，存在重复可打出判断 |
| `ManualPlayBatch.Submit` | 调用 CardModel.TryManualPlay；false 当前使用通用拒绝原因 |
| `CardModel.TryManualPlay` | 自身调用 CanPlayTargeting，再经 ActionQueueSynchronizer.RequestEnqueue 入队 |
| `CardModel.CanPlayTargeting`／`CanPlay` | 原生目标检查及当前资源检查；不将排队卡牌未来可能产生的资源计入 |
| `PlayCardAction.ExecuteAction` | 执行前再次检查手牌归属、CanPlay 及目标；入队成功不保证最终实际打出 |
| `Bloodletting.OnPlay` | 等待施法、损血，再 GainEnergy(2)；不是提交时立刻回能 |

移除重复可打出检查的建议不包括删除 UI 目标范围及对象身份检查，也不包括直接调用 EnqueueManualPlay、忽略 CanPlay 的原生判定，或等待结算后自动补发被拒项目。拒绝原因应在 TryManualPlay 返回 false 后读取，不能重新成为提交门控。该建议尚未实施。

新反编译文件位于 `.tmp/2026-11-08-mid-playtest-feedback/source/`：CardModel.cs、PlayCardAction.cs、NEnergyCounter.cs、Bloodletting.cs。输入为游戏安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256：

```text
d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03
```

## 能量合并依据

CombatResourceJournal.Energy 将通知目标值交给 VisibleResourceChange，公开值来自能量标签；SampleVisibility 等待实际端点。VisibleResourceChange.Changed 在已有待显示变化尚未到达标签时更新 expected；Sample 确认端点再发布。不读取未展示的中间数字补事件。

原生 NEnergyCounter.OnEnergyChanged 只触发特效，数字由 OnCombatStateChanged→RefreshLabel 更新。这说明模型通知本身不能证明画面数字曾显示该中间值。

已有纯检查 `tests/csharp/Sts2Agent.Checks/VisibleResourceChecks.cs` 明确要求合并未显示的中间值；本次未改实现，未重复运行全套测试。

## 当前隔离实测

临时脚本 `.tmp/2026-11-08-mid-playtest-feedback/probe.py` 使用现有 GameSession 与 play:bloodletting 场景，未增加测试入口、未重建 DLL。每个场景通过真实 stdio MCP 读取观察、战斗对象、手牌，再执行批量或单张出牌，最后核对能量事件连续性与最终观察。

- 报告：`.tmp/2026-11-08-mid-playtest-feedback/current-probe/report.json`，passed:true，两项通过。
- 完整 MCP 返回：同目录 `calls.json`；原生响应、日志与隔离存档：`game/`。
- batch：放血／打击均 played，energy_changed 20→21；single：20→22、22→21。最终均 21。
- 两项均确认 inspect_combatants.enemies 无 hp／block，get_observation 有这些数据。
- 自有游戏 PID 26843 已退出；MCP 会话通过上下文管理器关闭。
- 源码产物及独立测试运行时 DLL 均为 SHA-256 `d27202e6e103e0d3ce83e8e577da5d9bc6f74dee4722d7d61e5d3fe799507e3d`。

这两项不是当前版本四张牌连招的端到端复现；不可将原始 schema 42 回执标为当前 schema 47 的新实测。

## 战斗对象扩充的修改范围

CombatantInspection.PlayerText／EnemyText／AllyText 不含生命、格挡；combatant_details 明确投影现有字段，combatant_presets._source_paths 也未接入生命路径。当前范围与 `docs/development/combatant-inspection.md` 一致。

已有 CombatObservation.Health／Block 可复用；基础观察当前在共用战斗对象结果外组装这些字段。若补齐，宜将相同生命读取收敛到共用对象结果，基础观察再组装能量、手牌及计数，避免重复读取或从不同规则取得值。需要同步检查奥斯提的 block_shared_with、隐藏／死亡／无限生命和 sources 的子路径行为。
