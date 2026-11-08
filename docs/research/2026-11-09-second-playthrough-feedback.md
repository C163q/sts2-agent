# 第二局游玩反馈核验

> 当前状态：已完成。共 3 项，已完成 3 项；原生规则对照、Happy Flower 修复及相关验证与文档均已完成，无遗留事项。

## 基线与证据

核对日期为 2026-11-09。反馈对应 Mod 0.83.0、MCP 0.86.0；游戏为 Linux release v0.107.1、build 59260271，RitsuLib 0.6.10。实现与构建目标为 Mod 0.84.0、MCP 0.87.0。

本机游戏安装目录为 `~/.local/share/Steam/steamapps/common/Slay the Spire 2`。原生证据来自其 `data_sts2_linuxbsd_x86_64/sts2.dll`：

- `CardModel.TryManualPlay`、`EnqueueManualPlay`、`CanPlayTargeting`：提交时检查当时条件，然后进入同步器。
- `NCardPlay.TryPlayCard`：目标与无目标出牌均调用 `TryManualPlay`，与接口复用的原生入口一致。
- `BulletTime.OnPlay`：先等待施法动画，再把手牌设为本回合免费。
- `Survivor.OnPlay`、`DaggerThrow.OnPlay`、`CardSelectCmd.FromHandForDiscard/FromHand`：两张牌共用弃牌选择；Dagger Throw 在选择前抽牌。
- `ActionQueueSet.PauseActionForPlayerChoice`：`CancelPlayCardActions` 取消尚未执行的出牌。
- `HappyFlower.AfterSideTurnStart/DoActivateVisuals`：回能与独立显示任务分开结束；`_isActivating` 控制临时显示计数。

上述类型反编译到忽略目录 `.tmp/2026-11-09-second-playthrough/source/`。原始游玩回执位于 `.tmp/live/ipc/responses/`，截图位于 `.sts2-agent/screenshots/`；本次独立测试证据位于 `.tmp/2026-11-09-second-playthrough/`。这些本机证据不纳入 Git。

## 逐项判断

### 1. Bullet Time 后的牌未提交

现象属实，属于原生快速连续入队行为。`7879b31bfb544b25b0ea7f6075921402.json` 中 Bullet Time 为 `played`，随后三张 Strike 和一张 Defend 均为 `not_submitted`，原因是原生能量不足说明；回执末尾剩余手牌已经显示 0 费。

接口逐项调用原生 `TryManualPlay`，没有提前计算整批总费用。Bullet Time 可在后项入队前扣除 3 能量，但其减费需要等待施法动画，因此后项在仍然收费的时刻被原生拒绝。后来的手牌减费不会重新提交已拒绝项。

保留快速入队语义。需要前项减费或回能的连招，先单独完成前项，再按新费用提交。工具说明和[出牌指南](../development/card-play.md#连续出牌)明确这一使用方式。

### 2. 手动弃牌取消后续队列

现象属实，取消来自原生选择流程。`52c743badd6d4613ad9b78502bd607b1.json` 中 Dagger Throw 为 `resolving`，后续 Strike、Defend 为 `not_played`，同时返回 `choice_required/complete:true`。

`CardSelectCmd.FromHand` 打开手动选择时发出 `CancelPlayCardActions`，由原生队列取消后续出牌。保留此行为；逐张状态已区分未打出项，`complete` 表示到达选择边界。工具说明补足选择后检查更新的 `card_plays`、按当前手牌决定重新提交的用法。仍在 `queued/resolving` 的项继续由原生队列处理。

### 3. Survivor 与 Dagger Throw 自动弃牌

现象属实，两张牌遵循同一套候选数规则。`CardSelectCmd.FromHand` 在无候选时直接返回；未要求手动确认且候选数不超过最少选择数时，直接选中全部候选，否则打开选择。

`2c11354453df4501b035e92e09853800.json` 的批次顺序为 Footwork、Defend、Survivor、Piercing Wail。前两张已打出，Survivor 进入结算区后只剩 Piercing Wail，因此直接弃掉它；该牌后来没有进入出牌流程，状态为 `not_played`。排队本身不会把卡牌移出手牌。

`d1b82ce5c6164fa285d3da2abab41b7a.json` 中 Dagger Throw 打出后未抽到牌，唯一剩余的 Survivor 被自动弃掉。其他 Dagger Throw 在抽牌后有多个候选，因而打开手动选择。保留原生规则。

### 4. 完成回执后出现 stale_state

这局共找到 7 次，全部发生在 Happy Flower 触发后的回合返回。上一个完整状态与恢复观察的唯一字段差异，都是 `top_bar.relics[2].counter:3→0`。

| 过期错误回执 | 上一个完成回执 |
| --- | --- |
| `b59e676cb02a4f9a9b5354775c196530` | `7ca85f555f2b466b9a1b6a2e6230bfbb` |
| `15febb0c154b4b04a691a0f6b0d9140b` | `1a9a1fbeaf684f9c8aee1ade136f1856` |
| `0b1d2cf2c71d4279af32955d0b9aa096` | `ed880c94dfce414aaed1ffb336729c60` |
| `0ffe5a0376f9494bb7565bc8c86bdfda` | `c358013f2b30452ea11efdd28cdc0e32` |
| `b1311fa2b54f4bfe9be093098385072a` | `040b6dfa23a24427a9800cbed7503780` |
| `9086e1ad5b6842cd89e0159e2eb014e6` | `a5443bdeca024ee78227ed371fcf9818` |
| `c5938ebcece64e009424cf6789af1309` | `6de5fdfc989845f5bc245a3a19a38a20` |

原生 Happy Flower 每三回合回能，同时启动独立的 `DoActivateVisuals`。显示任务将计数暂设为 `3`，等待 `Cmd.Wait(1f)` 后恢复为 `0`。原有等待覆盖了队列、资源等动画和 250 毫秒静态观察，但遗漏该独立任务，导致过早返回。

这是接口问题，已在 [RunUi.ResourceMotionPending](../../src/Sts2Agent/Observation/RunUi.cs) 中扩展原有遗物激活等待，同时保留佩尔之翼分支。可见计数继续纳入状态令牌，外部动作仍会使旧许可失效。错误恢复继续要求读取当前状态。

### 5. target_id 是否应统一为可选

单体、群体和随机目标对应不同原生交互，现有参数规则符合这些区别。手牌正文可供理解效果，需要确认目标要求时，已有 `inspect_targets` 返回 `target_type/requires_target/targets`。

继续用该查询说明交互需求，保持 `inspect_hand` 的静态显示范围，省略无目标牌的 `target_id`。自动忽略多余目标会使明确指定对象的请求在不同范围上执行；本次保持前置拒绝，便于调用方修正参数。

## 验证

| 检查 | 结果与证据 |
| --- | --- |
| 修复前 Happy Flower 真实 MCP | `red-relic/report.json` 按预期失败：回执计数 3，0.3 秒后的采样为 0，沿用原许可出牌收到 stale_state |
| 修复后 Happy Flower 真实 MCP | `green-relic/report.json` 通过：连续 4 次结束回合覆盖两次触发；每次返回后采样至 1.6 秒令牌不变，可直接出牌；额外外部动作后仍依次拒绝 stale_state、observation_required |
| 原生 Bullet Time／弃牌对照 | `native-rules/report.json` 的 5 局全部通过：Bullet Time 原生接受结果为 `[true,false,false,false,false]`，结束时四张剩余牌均已显示 0 费；Survivor、Dagger Throw 在多个候选时打开选择并取消后续出牌，在唯一候选时自动弃牌 |
| Python 全量 | 860 项通过；补齐图形白名单后，套件与登记表另有 19 项通过 |
| C# 纯检查 | 155 个 PASS |
| Mod 构建 | 0 警告、0 错误；稳定性验证 DLL 与最终构建 DLL 哈希一致 |
| 文档与数据 | 183 个本地链接目标有效，改动的 Python／JSON 可解析，`git diff --check` 通过 |

独立实例使用临时存档与 IPC，结束后清理自有进程。本次修改没有安装正式游戏目录中的 Mod，也未在正式对局中重跑这些场景。
