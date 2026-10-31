# 出牌与目标查询

适用于 Mod `0.28.0`、MCP server `0.24.0`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10`。提供原生单人战斗中的一次手动出牌及只读目标查询；目标判定依据见 [源码调研](../research/2026-10-30-card-play-targeting.md)。

## 查询目标

`inspect_targets({"card_id": 7})` 查询当前可见且已识别的手牌。它不拖牌、不进入瞄准、不消耗随机数，不执行卡牌效果，也不准备动作许可。已有许可仅在查询成功且状态令牌未变时保留。只有正常出牌画面可查询，选牌、眼睛查看战场、其他页面覆盖及排队结算期间不可用。

药水使用同一查询工具，以 `potion_slot` 定位，不能同时传 `card_id`；格式见 [药水接口](potion-actions.md)。

返回结构示例，ID 和数值仅为说明：

```json
{
  "card": {"id": 7, "name": "Strike"},
  "playable": true,
  "target_type": "any_enemy",
  "requires_target": true,
  "targets": [{"id": 3, "kind": "enemy", "name": "Leaf Slime (S)"}],
  "reason": null
}
```

| 字段 | 含义 |
| --- | --- |
| `card` | 手牌稳定 ID 与完整英语显示名称，保留可见升级后缀，与观察及手牌详情一致；不附送效果正文 |
| `playable` | 当前正常出牌阶段、卡牌条件及目标条件允许提交；不是未来执行保证 |
| `target_type` | `none`、`self`、`any_enemy`、`all_enemies`、`random_enemy`、`any_player`、`any_ally`、`all_allies`、`osty` |
| `requires_target` | 调用时是否必须指定 `target_id`；原版单人卡牌中 `any_enemy` 和 `any_ally` 为 `true` |
| `targets` | 单体模式的当前可指定对象，或其他类型的当前指示范围；只包含可见对象 |
| `reason` | 可打出时为 `null`，否则给出简短原因；不输出内部 hook、隐藏规则或未来结果 |

`requires_target: false` 不保证可以打出。资源不足、不可打出关键词、卡牌自身条件、外部限制均由原生 `CanPlay` 判定。单体目标还检查存活、可命中、阵营、队友排除自身及原生单体禁止指定规则。群体、随机范围不套用单体的禁止指定限制。

防御的 `targets` 可以列出自己，表示自身指示框，但不能因此传入目标。随机牌的列表只是当前可能范围，不是预先抽取的命中结果，也不预测每一击或全部后续效果。范围为空不会自行增加一条禁止所有无目标牌的规则；实际能否提交由原生流程判断。

指示范围不等于具体效果最终命中列表。例如用原版测试 power 构造存活但不可命中的对象时，原生群攻仍可能对其造成伤害。工具保持原生结算，不用查询结果裁剪卡牌效果。

## 提交出牌

首次先调用 `get_observation`，之后可依据完整成功的动作结果直接继续，详见[MCP 动作许可](mcp.md#调用和错误语义)。`play_card({"card_id": 7, "target_id": 3})` 完成一次出牌及指定目标；不要求指定目标时使用 `play_card({"card_id": 8})`。卡牌 ID 不是手牌位置，目标 ID 使用原生战斗 `CombatId`，与敌人观察及期间事件一致。

要求指定时，即使只有一个目标也必须提供 ID。不要求时必须省略 `target_id`，传入多余目标会被拒绝；`null` 不是省略。卡牌 ID 范围为 `0..2147483647`，目标 ID 为 `0..4294967295`，两者都不接受布尔、浮点或字符串。

动作消耗旧观察许可，完整成功且可继续行动时由新观察接替；失败后须重新观察。提交前在游戏线程重查快照、阶段、队列、可见手牌与实际归属、卡牌规则及目标规则。执行调用原生 `TryManualPlay`，由同步器进入 `PlayCardAction`；不直接扣资源，不使用自动出牌替代手动出牌。

原生队列执行前还会再次检查。入队不表示效果已经生效；工具跟踪实际提交的动作，不因入队前短暂空队列而提前返回。

## 出牌后的边界

返回基础观察和 `transition`，事件结构复用 [期间事件](end-turn.md)。普通出牌可在同一回合返回 `player_ready`；出牌导致抽牌、自动出牌、伤害、死亡或胜负时记录已发生的可感知事件。

`player_ready` 返回前还会等待已识别的原生牌堆飞行结束及观察稳定，避免卡牌已结算但可见弃牌数尚未更新；完整保证与 `complete` 的含义见[动作完成与画面稳定](end-turn.md#动作完成与画面稳定)。

实际出现选择时返回 `choice_required`，随后使用 [选牌工具](card-selection.md)。发现的候选在打出后生成，微光先抽牌再选手牌；冲锋！！在少量候选被原生自动处理时直接继续结算。不能在 `play_card` 参数中提前附送后续选牌，也不能为了等待整张牌结束而阻塞在玩家选择上。

`action_canceled` 表示已观察到原生动作取消并恢复可行动，仍返回期间事件；不能把提交成功当成实际打出。`timeout`、`interrupted` 或事件缓冲截断时 `complete` 为 `false`。返回后先观察再决定，不自动补发未知结果的动作。

`available_actions` 的 `play_card` 表示当前可请求出牌，具体卡牌与目标仍须检查，并不保证每张手牌可打出。选择期间，包括通过眼睛查看战场，都不会提供普通出牌动作。

## 范围与验证

当前限制为已核对的原版目标类型和本地单人流程。真实多人及第三方自定义目标尚未接通；不将未知目标类型当作无目标类型提交。武装等手牌升级已经接入[选牌接口](card-selection.md#手牌升级)，出牌后需独立选牌及确认；其他未支持选择仍作为明确交互边界返回，具体范围以选牌指南为准。

隔离实例可用 `python3 scripts/run_roundtrip.py --play-scenario basic` 启动，再在另一终端运行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_card_play.py --scenario basic --report .tmp/roundtrip/play-basic.json
```

场景入口只在测试模式配置初始条件，不能用于正式对局。其他场景及实际通过范围见 [验证记录](../research/2026-10-30-card-play-validation.md)。构建通过不替代原生游戏、图形显示和 stdio MCP 行为验证。

验证动作返回后的可见计数时，另启动新图形实例 `python3 scripts/run_roundtrip.py --windowed --play-scenario basic`，再运行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_action_settling.py --report .tmp/settling-check/run.json
```

该检查通过真实 MCP 打出打击和防御、结束一个回合，并分别比较返回状态与无输入两秒后的状态，保存六张截图；重复执行须使用新的报告目录。结果及边界见[修复记录](../research/2026-10-30-action-settling.md)。

标准库文件客户端提供 `inspect_targets --card-id 7` 和 `play_card --card-id 7 --target-id 3 --expected-state <令牌>`；这些操作仍需 `--ipc-dir`。MCP 会话内部管理令牌，LLM 不接收原始令牌。
