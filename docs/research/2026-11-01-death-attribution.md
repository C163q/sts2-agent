# 伤害与关联死亡来源核查

当前状态：已完成。已修复关联清理误归因及反伤后重复死亡，14 个 GUI 场景与自动检查通过；无剩余实施项，尚未正式安装。

## 基线与证据

任务基线 `1aefaa4`；Linux 游戏 `v0.107.1`、release `59260271`，RitsuLib `0.6.10` 兼容运行时。修复版 Mod `0.42.1`；MCP `0.40.0`、底层 schema `24` 与工具参数保持不变。核对始于 2026-11-01，验证延续到 2026-11-02。

反馈为外部 `playtest-2026-11-01-r8/report.txt`，关键证据为同目录 `evidence-part-4.json` 的步骤 179–187。新增 summary 建议未纳入此次修改。

本地证据位于不纳入 Git 的 `.tmp/2026-11-01-minion-attribution/`；`source/` 为安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll` 的定向反编译。核对成员：

- `CreatureCmd.Damage`、`KillWithoutCheckingWinCondition`：伤害结算后调用死亡流程；最后一个主要敌人死亡时，对剩余次要敌人调用 `Kill`，内部直接清零 HP。
- `Creature.LoseHpInternal`、`DamageResult.WasTargetKilled`：实际生命损失及该次命中的致命接收者。
- `DoomPower.DoomKill`：只对传入实例执行明确处决；关联清理不属于该列表。
- `TheObscura.IllusionMove`、`Parafright`、`MinionPower`：原生召唤与次要敌人身份；修复不依赖这些怪物名称。
- `LivingFog.BloatMove`、`GasBomb.ExplodeMove`：原生召唤；召唤物先攻击玩家，再调用 `Kill(Creature)` 自毁。
- `DeathBlowIntent`、`NIntent.OnHovered`：可见特殊意图与原生悬停说明。基础观察读取绘制图标和数字，详情使用当前显示意图的 hover tip。

## 原因与修复

原来的伤害异步上下文覆盖整个 `Damage` 调用，包含其内部死亡处理。随从清理调用 `LoseHpInternal` 时仍带着首领所受攻击的上下文，因此被错误生成同一张牌的 `damage` 和 `died.source`。

现在在通用死亡入口建立独立上下文。仅当死亡实例属于该次真实致命命中的接收者，或属于明确 Doom 处决列表，才保留来源；递归处理同一实例可保留原来源。关联清理清除外层牌、攻击者与伤害标记；其中的公开 HP 清零可产生 `hp_changed`，死亡来源为 `null`，不虚构额外伤害。嵌套真实伤害仍建立自己的上下文，异常或返回后恢复调用者。

活雾反伤用例另发现原生重复死亡通知：Gas Bomb 在攻击前被 Thorns 杀死后，仍继续造成攻击伤害并调用自身 `Kill`，再次触发 `Died`。`regression-gui/fog_thorns/` 保留修复前的两条死亡记录，第一条为 Thorns、第二条为 `null`。记录器现按实例保留死亡状态，未复活前只发布一次死亡；原生 `Revived` 清除标记，同次调用内复活后再次死亡仍分别记录。新日志从已有尸体状态建立基线，不补发重复死亡。

这一修复收紧了[事件契约](../development/end-turn.md#事件语义)中的“已核实来源”：来源表示本次直接效果，不能代表整条动作因果链。原有行为违反该要求，已同步补充边界说明；不新增推测性的死亡原因字段。

## 验证

`red-gui/` 在修复前通过真实 MCP 复现：Anger+ 对首领损失 3 HP，随后错误报告对 Parafright 的 15 点伤害与牌来源。`green-gui/` 的单体修复用例通过；群攻断言最初误设为 3，核对原生 `Thunderclap.CanonicalVars` 后改为 4。`verified-gui/` 的 Doom 分支误将敌方正常攻击也纳入“对敌无伤害”断言，已限定敌方接收者，并核对处决发生在目标一方回合结束时。`remaining-gui/` 的意图断言误要求包含 `die`，原生实际用词是 `destroyed`；删除该多余词语判断，保留工具与原生完整提示、图标和数字的相等校验。各失败目录保留，不覆盖证据。

最终验证：

- 编译通过，0 警告、0 错误；纯 C# 检查 60 项通过，全量 Python 371 项通过（33.003 秒）。日志为 `build-verified.log`、`csharp-verified.log`、`python-final.log`。
- 14 个中文真实 GUI 场景使用同一最终 DLL，分两批通过：`final-gui/` 前 11 项，以及修正夹具配置后的 `final-regression-gui/` 3 项。后者总报告通过；前者保留失败配置记录，不能视为一次完整 14 项全绿运行。汇总为 `verified-summary.json`。
- 包含 5 项死亡／复活原生检查与 19 项战斗交接检查；独立只读审阅未发现确认的问题。两个最终隔离游戏进程均已退出。
- 测试 DLL SHA-256：`36d74ebf2ac76c1746be9088ef3195075788e79bd5ee2674206c9fedb503f356`，与构建输出及隔离运行时一致。未更改正式安装、正式存档或其他 agent 的对局。

真实 MCP 样例保存在 `corrected-minion-receipt.json`、`gas-bomb-end-turn.json`、`gas-bomb-thorns-end-turn.json`。中英文原生意图悬停截图位于 `final-gui/game/native-gas-bomb-zhs.png`、`native-gas-bomb-eng.png`，保留该进程最后一次采集；已实际查看，图标、8 点数字及悬停说明一致。各场景的完整提示对照另存于各自 `verify/evidence.json`。

已核对的回执与 UI：

| 场景 | 结果 |
| --- | --- |
| Anger+ 单体击杀首领 | 首领损失 3 HP 且死亡来源为 Anger+；随从 15 HP 清零为 `hp_changed`，死亡来源为 `null`，无额外牌伤害 |
| Thunderclap 群攻 | 随从真实命中为 4 HP，剩余 11 HP 的清理不记为伤害；两个目标均被真实致命命中时，两条死亡保留牌来源 |
| Doom、Fire Potion | 首领保留明确处决或药水来源，关联清理不继承；Doom 回执中此前的敌方攻击仍正常保留 |
| 活雾自然召唤、自爆 | `death_blow` 数字为 8；`inspect_combatants` 的 Death Blow 提示与原生中英文悬停一致，中文标题为“濒死一击”；攻击的 `actor` 为 Gas Bomb，自身清零无额外伤害，死亡来源为 `null` |
| 卡牌击杀／首领死亡清理 Gas Bomb | 前者保留 Strike 的直接命中和死亡来源；后者不生成对召唤物的伤害，死亡来源为 `null` |
| Thorns 击杀 Gas Bomb | 实际反伤损失 7 HP，死亡来源为 Thorns 且只记录一次；原生攻击仍继续对玩家造成 8 点伤害 |
| 原生死亡、重接与再死亡 | 同一日志为 `died → revived → died`；重复通知被过滤，新日志不补记已有尸体，作用域正常释放 |

测试设施的另两处错误也保留：`fog-gui/fog_cleanup` 在正确进入奖励页后，误把 `enemies:null` 当数组遍历；`final-gui/phase_revive` 漏配 `play:kill_chain`，对 46 HP 目标的普通 Strike 未触发击杀。前者按奖励页合同修正，后者补齐 1 HP 夹具并同步[套件配置说明](../development/gui-testing.md)。两处均未修改生产玩法。

## 范围

生产代码只改变事件采集，不改写游戏状态或动作。测试专用夹具通过原生房间、召唤和设置命令准备低血量场景；活雾自然召唤用例通过真实 `end_turn` 推进。中英文意图悬停入口仅在隔离套件模式开放，不属于公开 MCP 工具。

未知死亡来源保持 `null`；不能仅凭它判定逃跑、自毁、清理或其他原因，也不从内部 move 名称推断。原生仍触发死亡的召唤物保留 `died`，不将其改写成玩家造成的直接伤害。未承诺任意第三方 Mod 自定义死亡流程的完整归因。
