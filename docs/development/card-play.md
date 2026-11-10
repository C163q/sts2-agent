# 出牌与目标查询

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

提供原生单人战斗中的单张出牌、连续入队及只读目标查询；目标判定依据见 [源码调研](../research/2026-10-30-card-play-targeting.md)。

含 null 的字段说明与示例按 full 表达；默认输出的空值处理见[公共预设](mcp.md#输出预设)。

成功结果的 `scene/screen` 来自本次快照，表示当前房间与覆盖状态，统一规则见[MCP 上下文](mcp.md#成功结果的场景上下文)。

## 查询目标

`inspect_targets({"card_id": 7})` 查询当前可见且已识别的手牌。查询为只读操作，成功时刷新动作状态令牌。只有正常出牌画面可查询，选牌、眼睛查看战场、其他页面覆盖及排队结算期间不可用。

药水使用同一查询工具，以 `potion_slot` 定位，不能同时传 `card_id`；格式见 [药水接口](potion-actions.md)。

本工具使用通用 default/full，不提供 summary；现有字段已是紧凑查询。参数错误和明确读取拒绝保留已有许可，失败不会生成新许可；完整规则及公开错误说明见[MCP 错误语义](mcp.md#调用和错误语义)。

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

基础观察、相关详情和满足续接条件的成功动作结果均可提供当前状态令牌，详见[MCP 动作许可](mcp.md#调用和错误语义)。`play_card({"card_id": 7, "target_id": 3})` 完成一次出牌及指定目标；不要求指定目标时使用 `play_card({"card_id": 8})`。卡牌 ID 不是手牌位置，目标 ID 使用原生战斗 `CombatId`，与敌人观察及期间事件一致。

要求指定时，即使只有一个目标也必须提供 ID。不要求时必须省略 `target_id`，传入多余目标会被拒绝；`null` 不是省略。卡牌 ID 范围为 `0..2147483647`，目标 ID 为 `0..4294967295`，两者都不接受布尔、浮点或字符串。

动作消耗旧观察许可，完整成功且可继续行动时由新观察接替；Mod 明确标记为提交及 UI 变化之前的拒绝可保留原许可，例如能量不足、缺少／多余目标或指定对象不在当前范围。结果未知或没有该标记的失败仍须重新观察，规则见上述 MCP 错误语义。提交前在游戏线程重查快照、阶段、队列、可见手牌与实际归属、目标参数及可见目标范围。卡牌费用及可打出条件由原生 `TryManualPlay` 决定，返回 false 后才读取公开拒绝原因；不在 Mod 中提前重复调用 CanPlay／CanPlayTargeting 阻止提交。接受后由同步器进入 `PlayCardAction`，不直接扣资源，不使用自动出牌替代手动出牌。

原生队列执行前还会再次检查。入队不表示效果已经生效；工具跟踪实际提交的动作，不因入队前短暂空队列而提前返回。

## 连续出牌

`play_cards` 在一次请求中按数组顺序尝试原生手动入队，允许上一张尚未结算。每张牌的效果仍依次执行：

```json
{
  "cards": [
    {"card_id": 7, "target_id": 3},
    {"card_id": 8},
    {"card_id": 9, "target_id": 3}
  ],
  "preset": "default"
}
```

cards 为必填非空数组，允许一张；每项仅接受 card_id 与按目标要求提供的 target_id，类型及范围沿用单张接口。所有牌必须是调用开始时已识别的手牌，同一 ID 不得重复；不同副本分别使用自己的 ID。目标可以直接使用已有观察中的当前对象 ID，不要求先 inspect_targets。preset 支持 default/full，默认 default。

所有参数、初始卡牌与目标引用、目标参数是否应提供均在提交前整体校验，错误指出数组项，整批不执行。初始目标引用只确认当前可见对象身份，当前合法范围仍在实际提交该项时重查。费用不预扣、不求总和，也不预测后续抽牌或减费。某项当前不能提交时记录原因并继续后项；选择、胜负、战斗／回合变化或页面覆盖后停止新增提交。已入队的牌执行时失效则遵循原生处理，不回滚、不补发、不自动换目标。

原生入队检查当时的费用与资源。前项已经扣费而回能或减费尚未生效时，后项可能被原生拒绝。例如 3 能量连续提交 Bullet Time 和多张 1 费牌时，Bullet Time 可以先扣光能量，在其减费效果生效前，后项被拒绝并记为 `not_submitted`。依赖回能或减费的连招应先单独打出前置牌，等回执返回后查看新费用，再提交后续批次。

手牌选择会取消原生后续出牌，包括候选较少而自动选择的情况；发现牌、独立候选及弃牌堆选择通常暂停队列，选完继续。弃 1 张且只剩 1 个候选时，Survivor 和 Dagger Throw 共用的原生选择流程直接弃掉该牌，包括已排队但仍在手中的牌；Dagger Throw 先抽牌，候选数以抽牌后为准。尚未入队的项保持未提交，不保存为之后执行的计划。不能预填后续选择答案。当前迁移验证见[v0.111.0 记录](../research/2026-11-10-v0.111-migration-investigation.md)，旧版原生行为见[连续出牌核验](../research/2026-11-04-play-card-review.md)及[游玩反馈核验](../research/2026-11-09-second-playthrough-feedback.md)。

## 逐张结果

批量调用额外返回 `card_plays:{batch_id,results}`。batch_id 是独立的控制关联标识，后续选牌回执使用同一值；results 按原输入顺序保留所有项，含从 0 起的 index、card_id、target_id、status 和 reason。index 是请求数组位置，不是牌堆位置；default 省略普通 null，full 保留。此列表不附送牌面或内部数值。

| status | 含义 |
| --- | --- |
| not_submitted | 未提交，附公开原因；可以是当前条件不符，也可以是遇到边界后停止提交。 |
| queued | 已确认进入原生队列，尚未开始执行。 |
| resolving | 原生正在处理，可能等待选择，不代表已完整结算。 |
| played | 已可见地进入真实手动出牌流程且原生动作结束；不保证正文每项效果都发生。 |
| not_played | 入队后取消或结束，但没有实际进入出牌流程；原生执行检查拒绝时附当时的公开原因，其他情况附已确认的取消／结束说明。 |
| unknown | 异常、未能观察实际出牌或上下文替换，结果无法确认。 |

原生 Finished 同时包含实际打出与取消后结束等情况。工具追踪入队、执行、取消与真实 CardPlaying，据此生成逐张状态；自动出牌另以期间事件记录。

单张提交时与批量执行时的能量、星星等原生拒绝共用公开文本。批量只在 `PlayCardAction` 的实际 `CanPlay` 检查失败处记录该原因，避免把选择或胜负导致的队列取消误报为资源不足。记录入口见[CardPlayFailureCapture](../../src/Sts2Agent/Actions/CardPlayFailureCapture.cs)。

选择边界仍立即返回，transition.complete 表示本次边界已到达。未完成批次保留只读追踪，在后续带 transition 的成功动作回执附加更新后的完整 card_plays；终结状态发布后释放。基础观察和普通详情不回放该列表。外部新局／战斗替换会清理旧追踪；超时不撤销原生队列，不提供跨进程恢复或持久任务查询。

完成选择后，结合更新后的 `card_plays` 和当前手牌重新决策：`queued/resolving` 仍由原生继续处理；想继续打出的 `not_submitted/not_played` 项须在确认卡牌仍可用后重新提交。

零项提交但请求有效时也返回成功动作回执及逐项原因；参数／引用／阶段的整批前置拒绝走 error。部分提交不能声称整批未执行。仅经核实的前置拒绝保留已有许可，未知结果不续接；当前 action_canceled 仍须先读取状态，沿用单张接口策略。

任一项为 unknown 时，须先读取当前状态，再提交下一次动作；选牌窗口已显示时可以使用 inspect_selection。正常的 queued/resolving 不触发这条额外读取要求，可以直接继续选牌。

## 出牌后的边界

返回[精简动作回执](mcp.md#动作返回格式)，事件结构复用 [期间事件](end-turn.md)。普通出牌可在同一回合返回 `player_ready`；出牌导致抽牌、自动出牌、伤害、死亡或胜负时记录已发生的可感知事件。

`player_ready` 返回前还会等待已识别的牌堆飞行、生物退场及有限 UI 过渡，避免可见牌堆计数或敌人列表继续变化；完整保证与 `complete` 的含义见[动作完成与画面稳定](end-turn.md#动作完成与画面稳定)。

实际出现选择时返回 `choice_required`，随后使用 [选牌工具](card-selection.md)。发现的候选在打出后生成，微光先抽牌再选手牌；冲锋！！在少量候选被原生自动处理时直接继续结算。不能在 `play_card` 参数中提前附送后续选牌，也不能为了等待整张牌结束而阻塞在玩家选择上。

`action_canceled` 表示已观察到原生动作取消并恢复可行动，仍返回期间事件；不能把提交成功当成实际打出。`timeout`、`interrupted` 或事件缓冲截断时 `complete` 为 `false`。返回后先观察再决定，不自动补发未知结果的动作。

`available_actions` 的 `play_card`／`play_cards` 表示当前可请求出牌，具体卡牌与目标仍须检查，并不保证每张手牌可打出。选择期间，包括通过眼睛查看战场，都不会提供普通出牌动作。拒绝说明区分选牌、地图、卡牌浏览、过渡及当前阶段；卡牌不可打出原因复用原生 UI 气泡，保留其公开的阻止来源标题，不增加隐藏规则说明。

## 范围与验证

原生手动出牌及批次提交见 [GameAdapter.CardPlay](../../src/Sts2Agent/Adapter/GameAdapter.CardPlay.cs)，目标读取见 [TargetInspection](../../src/Sts2Agent/Observation/TargetInspection.cs)，逐张结果校验见 [card_batch_details](../../src/sts2_mcp/output/card_batch_details.py)。

当前限制为已核对的原版目标类型和本地单人流程。真实多人及第三方自定义目标尚未接通；不将未知目标类型当作无目标类型提交。武装等手牌升级已经接入[选牌接口](card-selection.md#手牌升级)，出牌后需独立选牌及确认；其他未支持选择仍作为明确交互边界返回，具体范围以选牌指南为准。

隔离实例可用 `python3 scripts/run_roundtrip.py --play-scenario basic` 启动，再在另一终端运行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_card_play --scenario basic --report .tmp/roundtrip/play-basic.json
```

场景入口只在测试模式配置初始条件，不能用于正式对局。其他场景及实际通过范围见 [验证记录](../research/2026-10-30-card-play-validation.md)。构建通过不替代原生游戏、图形显示和 stdio MCP 行为验证。

验证动作返回后的可见计数时，另启动新图形实例 `python3 scripts/run_roundtrip.py --windowed --play-scenario basic`，再运行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_action_settling --report .tmp/settling-check/run.json
```

该检查通过真实 MCP 打出打击和防御、结束一个回合，并分别比较返回状态与无输入两秒后的状态，保存六张截图；重复执行须使用新的报告目录。结果及边界见[修复记录](../research/2026-10-30-action-settling.md)。

标准库文件客户端提供 `inspect_targets --card-id 7` 和 `play_card --card-id 7 --target-id 3 --expected-state <令牌>`；这些操作仍需 `--ipc-dir`。MCP 会话内部管理令牌，LLM 不接收原始令牌。

文件客户端连续出牌使用 `play_cards --cards '[{"card_id":7,"target_id":3},{"card_id":8}]' --expected-state <令牌>`，支持 --preset default/full；非 raw 输出保留文件客户端的完整观察范围，MCP 仍返回精简动作回执。
