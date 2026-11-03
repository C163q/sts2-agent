# inspect_targets 场景与现有参数核验

> 当前状态：本轮核验、定稿与修复完成，inspect_targets 已核销。维持 default/full，不增加 summary，不改变原生目标范围；TARGET-01／02 及已审阅四工具的同类路径已按[实施记录](2026-11-03-inspection-error-recovery.md)修复并验证。下方原 full 样本保留历史核验基线；AnyPlayer／AllAllies／Osty 卡牌分支仅源码核对，没有新增实际调用样本，真正多人及第三方目标规则仍不属于已验证范围。暂无阻塞。

## 优先关注的问题

| 编号 | 优先级与状态 | 影响及证据 | 处理范围 |
| --- | --- | --- | --- |
| TARGET-01 | 中；本轮范围已修复 | 原生具体拒绝说明原先被 Python 模板覆盖；现在只公开 Mod 显式许可的 public_message，并补充四工具的参数说明，异常与控制字段仍隔离 | [实施与验证](2026-11-03-inspection-error-recovery.md)；其他工具的逐项错误审阅仍留在用户 TODO |
| TARGET-02 | 中；本轮范围已修复 | 查询原先在参数校验前清除许可；现四个读取工具的参数错误及明确拒绝保留已有许可。play_card 明确未提交的前置拒绝也可直接续接，未知结果仍清除 | 同一实施记录；不自动观察、重试，不由错误生成新许可，不放宽原生 stale_state 校验 |

以上共用问题已有 Python 回归与两组隔离游戏证据。目前没有发现独立于这两项的目标判定错误；静态核对和现有测试不能证明任意动画时刻或全部卡牌组合均正确。

目标范围沿用原生 UI：费用不足时 `targets` 仍可非空；自身、群体与随机牌的 `targets` 表示指示范围，不等于可传入的目标参数。结合 `playable/usable` 与 `requires_target` 判断，保留这些语义。

## 核对基线与证据

- 核验日期：2026-11-03；代码提交 `96c8471`，Mod `0.51.0`、MCP `0.52.0`、原生 schema `34`。这是阶段性核验基线；持续维护的版本统一见[README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`，release、build `59260271`；RitsuLib `0.6.10` 的该游戏兼容运行时。重新核对游戏目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 原生入口：[CardPlayRequest](../../src/Sts2Agent/Adapter/GameAdapter.CardPlay.cs)、[PotionRequest](../../src/Sts2Agent/Adapter/GameAdapter.Potions.cs)、[available_actions](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。读取：[TargetInspection](../../src/Sts2Agent/Observation/TargetInspection.cs)、[PotionActions](../../src/Sts2Agent/Actions/PotionActions.cs)。
- MCP：[工具注册](../../src/sts2_mcp/mcp_catalog.py)、[派发与动作许可](../../src/sts2_mcp/game_tools.py)、[卡牌参数与目标校验](../../src/sts2_mcp/output/card_play_details.py)、[药水参数与目标校验](../../src/sts2_mcp/output/potion_action_details.py)、[公开错误映射](../../src/sts2_mcp/output/player_output.py)、[通用 preset](../../src/sts2_mcp/output/presets.py)。
- 本轮重新反编译 `MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.AllowedToTargetCreature/OnCreatureHovered/_Process` 与 `NCardPlay.ShowMultiCreatureTargetingVisuals`，保存在不入库的 `.tmp/2026-11-03-inspect-targets-review/source/`。CardModel、PotionModel、CombatState.PlayerCreatures 的证据复核沿用相同程序集的既有反编译产物；来源与相关规则见[出牌调研](2026-10-30-card-play-targeting.md)、[药水调研](2026-10-30-potion-actions.md)、[同伴调研](2026-11-02-companions.md)。
- RitsuLib 的 `CardModelIsValidTargetAnyPlayerPatch` 在单人时接受空目标，多人时要求玩家目标；本轮对照作者源码提交 `772f280964f2efc7c7e2f29fc59844e68616dd57` 的本地证据 `.tmp/ritsulib-end-turn-review/src/Combat/CardTargeting/`，没有把多人源码分支当作联机实测。
- 历史实机范围见[出牌验证](2026-10-30-card-play-validation.md)与[药水验证](2026-10-30-potion-actions-validation.md)。本轮将其中 24 份原生目标响应通过**当前**参数 schema、目标校验和公开投影，保存为[完整 JSON 示例](2026-11-03-inspect-targets-examples/manifest.json)；逐份与原结果去掉内部 snapshot_id 后比较一致。它们是历史实测经当前代码重新校验，不能标为当前版本的新游戏实测。

## 当前参数与工具用途

两种调用互斥，必须且只能提供一种定位：

```json
{"card_id": 5, "preset": "full"}
```

```json
{"potion_slot": 0, "preset": "full"}
```

| 参数 | 当前规则 |
| --- | --- |
| `card_id` | 当前可见、已识别手牌的稳定整数 ID，范围 0–2147483647；不是手牌序号，不接受 deck:N／pile:N |
| `potion_slot` | 从 0 开始的药水槽位，整数范围 0–2147483647；计入空槽，但被查询的槽位必须有支持的药水 |
| `preset` | 默认 default；仅支持 default/full。full 保留 null，default 使用共用规则省略普通 null；目前没有 summary |

不能同时传 card_id 与 potion_slot，也不能都不传。布尔、浮点、数字字符串、null、未知参数和 `target_id` 均不接受。它一次只查一个对象，没有批量或目标 ID 筛选参数。

本工具回答“这张牌／这瓶药水现在能否提交、是否要求指定目标、当前指示范围是什么”，不替代 `inspect_hand`／`inspect_potions` 的正文和悬停解释，也不提供伤害预测、执行计划或随机结果。查询不进入瞄准、不改变页面，不运行卡牌／药水效果；成功读取可直接为下一步动作提供当前许可，不要求固定先调用 get_observation。

当前工具描述是：

```text
Query exactly one hand card or potion for usability, requires_target and targeting range.
Does not enter aiming or resolve randomness; targets do not predict every effect.
```

成功结果没有 scene、screen、available_actions、资源总量或 transition。本轮场景统一约定没有给原本不返回 scene 的工具新增该字段。

## 场景目录与完整 full 示例

下面每个链接都是完整的公开返回 JSON，没有省略字段。调用参数及原始证据文件、数组下标见[样本清单](2026-11-03-inspect-targets-examples/manifest.json)。ID 仅在对应隔离对局内有效，不能直接用于当前游戏。

### 手牌分支

手牌查询要求正常本地出牌阶段、玩家存活、战斗无遮挡、没有待处理选牌、手牌不在拖动／打出模式、动作队列为空且未进入瞄准。**并不要求资源足够**；正常出牌画面中的不可打出牌仍可成功查询。

| 场景 | 完整 full 示例 | 当前结果 |
| --- | --- | --- |
| 指定敌人的打击 | [card-enemy](2026-11-03-inspect-targets-examples/card-enemy.full.json) | any_enemy，requires_target:true；即使只剩一名候选，实际出牌仍须传目标 ID |
| 防御，指向自身 | [card-self](2026-11-03-inspect-targets-examples/card-self.full.json) | self，requires_target:false；列出自身也不能传 target_id |
| 群体攻击 | [card-all-enemies](2026-11-03-inspect-targets-examples/card-all-enemies.full.json) | all_enemies，requires_target:false；列出当前指示范围 |
| 随机攻击 | [card-random](2026-11-03-inspect-targets-examples/card-random.full.json) | random_enemy，requires_target:false；列出可能范围，不预先选中随机对象 |
| 能量不足 | [card-energy](2026-11-03-inspect-targets-examples/card-energy.full.json) | playable:false，reason 为 Not enough Energy.；敌人范围仍保留 |
| 星星不足 | [card-stars](2026-11-03-inspect-targets-examples/card-stars.full.json) | playable:false，reason 为 Not enough Stars. |
| 无可指定对象 | [card-no-target](2026-11-03-inspect-targets-examples/card-no-target.full.json) | any_enemy，targets:[]，playable:false，No valid target. |
| 无需指定目标，当前指示范围为空 | [随机](2026-11-03-inspect-targets-examples/card-random-empty.full.json)、[群体](2026-11-03-inspect-targets-examples/card-all-enemies-empty.full.json) | 可以 targets:[] 且 playable:true；不擅自增加“任何牌都必须有活敌人”的限制 |
| 不可打出关键词、无目标类型 | [card-unplayable](2026-11-03-inspect-targets-examples/card-unplayable.full.json) | none，requires_target:false，targets:[]，playable:false |
| 没有存活队友 | [card-no-allies](2026-11-03-inspect-targets-examples/card-no-allies.full.json) | any_ally，requires_target:true，targets:[]，No living allies.；这是隔离夹具放入 Mimic 的样本，不表示正常单人会提供这张多人牌 |
| 卡牌自身条件不满足 | [card-condition](2026-11-03-inspect-targets-examples/card-condition.full.json) | Grand Finale，playable:false，This card cannot be played now. |
| 外部效果禁止出牌 | [card-hook](2026-11-03-inspect-targets-examples/card-hook.full.json) | 仍是同一成功结构，reason 为通用不可打出提示；不泄露内部 hook 身份 |

还识别到三个没有实际调用样本的支持分支，暂不编造卡名或把假设输出标为实测：

| target_type | 代码行为与核对范围 |
| --- | --- |
| any_player | 当前单人接口不要求显式目标，范围为自身；RitsuLib 单人规则一致。未选择具体卡牌新增游戏验证 |
| all_allies | 不要求显式目标，范围为存活 PlayerCreatures；CombatState.PlayerCreatures 仅含玩家，**不包含奥斯提**。与原生群体指示实现一致；GlimpseBeyond 源码使用此类型但限定多人，未将其写成普通单人场景 |
| osty | 不要求显式目标，范围为所有者奥斯提在通过可见性判断时的实例；原生 NCardPlay 有相同的奥斯提指示分支。本轮未确认目标版本有哪些正常可获得卡牌实际声明此类型，也未新增有／无奥斯提的调用样本 |

奥斯提实际参与攻击不代表牌的 target_type 必为 osty。例如已核对 Unleash 的目标类型仍是 any_enemy，Bodyguard 召唤奥斯提但类型是 self；不能从正文中的角色推断鼠标目标类型。君王之剑也不能仅因出现在画面上就成为可选目标，本工具只返回对应原生目标规则下的对象。

### 药水分支

药水查询沿用正常使用／丢弃的场景门控：单人或测试多人、玩家存活、对局未结束、顶栏可交互、无待处理选牌／瞄准／忙碌队列，并通过相应战斗或战斗外页面的可用性检查。能否查询与具体药水能否使用分开：自动药水、战斗专用药水和禁止移除时仍可成功返回 usable:false。

| 场景 | 完整 full 示例 | 当前结果 |
| --- | --- | --- |
| 战斗中指定敌人的火焰药水 | [potion-enemy](2026-11-03-inspect-targets-examples/potion-enemy.full.json) | any_enemy，requires_target:true，使用时须传整数目标 |
| 战斗中自身类型药水 | [potion-self](2026-11-03-inspect-targets-examples/potion-self.full.json) | self，requires_target:false，范围列出自身的整数 CombatId |
| 战斗中 AnyPlayer 正面药水 | [potion-any-player](2026-11-03-inspect-targets-examples/potion-any-player.full.json) | 单人时无需指定，范围为自身；不表示可选奥斯提 |
| 战斗外果汁等可随时使用药水 | [potion-noncombat](2026-11-03-inspect-targets-examples/potion-noncombat.full.json) | any_player，requires_target:false，自身范围 ID 为字符串 self；实际使用时仍省略 target_id |
| 战斗外查询战斗专用药水 | [potion-combat-only](2026-11-03-inspect-targets-examples/potion-combat-only.full.json) | usable:false，discardable:true，This potion can only be used in combat. |
| 自动触发的瓶中精灵 | [potion-automatic](2026-11-03-inspect-targets-examples/potion-automatic.full.json) | usable:false，但可以 discardable:true |
| 当前禁止移除药水 | [potion-cannot-remove](2026-11-03-inspect-targets-examples/potion-cannot-remove.full.json) | usable:false、discardable:false；不把丢弃状态与使用状态混为一个字段 |
| 群体药水 | [potion-all-enemies](2026-11-03-inspect-targets-examples/potion-all-enemies.full.json) | all_enemies，requires_target:false；范围不表示指定某名敌人 |
| 商店外观页，恶臭药水可投掷商人 | [potion-merchant](2026-11-03-inspect-targets-examples/potion-merchant.full.json) | targeted_no_creature，requires_target:true，目标为字符串 merchant |
| 地图盖住商人 | [potion-merchant-map](2026-11-03-inspect-targets-examples/potion-merchant-map.full.json) | 查询仍可成功，usable:false，targets:[]，No valid target. |
| 商品页已打开 | [potion-merchant-inventory](2026-11-03-inspect-targets-examples/potion-merchant-inventory.full.json) | 查询仍可成功，usable:false，This potion cannot be used here.；须回到可投掷的商人界面 |

战斗外的事件、先古之民、休息处、宝箱、商店、地图、奖励和占卜在满足页面门控时共用上述药水结构，没有按房间另加字段。历史样本的房间与原生条件见药水验证记录；本轮没有逐房间重跑。恶臭药水在战斗中变为 all_enemies，与商人场景属于不同目标规则，不应按药水名称固定解释。

### 覆盖、特殊阶段与错误

| 情况 | 当前结果 |
| --- | --- |
| 卡牌选择页，或通过眼睛查看战场但选择仍未完成 | 不能查询手牌／药水目标；手牌信息可由 inspect_hand 读取不表示当前允许查询正常出牌目标 |
| 地图覆盖战斗，或牌组／牌堆覆盖战斗 | 不能查询手牌／药水目标；不会自动关闭覆盖 |
| 战斗外地图 | 正常顶栏药水可查询；被地图遮住的商人不会成为恶臭药水目标 |
| 战斗外牌组／牌堆、模态弹窗、过渡或忙碌结算 | 通过统一场景门控拒绝；不穿透页面、不等待到下一可操作阶段再自动查询 |
| 敌方回合、战斗已结束、玩家死亡、主菜单 | 正常目标查询不可用，不以 playable:false 冒充已读取到具体卡牌 |
| ID 已离开手牌／未知或锁定牌／不支持的自定义卡牌目标类型 | illegal_action，不返回猜测范围；手牌 TargetedNoCreature 未支持 |
| 槽位为空／越界／药水归属不符／不支持的目标类型 | illegal_action，不返回成功空对象 |
| 参数不合法 | invalid_request；不向游戏发送请求 |
| 成功传输但目标 JSON 不符合协议 | transport_error，禁止把部分未经校验的内容当作成功结果 |
| 游戏未连接、超时、控制器被另一连接占用 | 沿用 MCP 共用连接与错误语义，不是目标查询专属返回结构 |

以下错误示例保留**原核验基线**的公开映射，不是本轮游戏触发：[非法参数](2026-11-03-inspect-targets-examples/error-invalid-request.full.json)、[不可操作或找不到对象](2026-11-03-inspect-targets-examples/error-illegal-action.full.json)、[连接或响应协议错误](2026-11-03-inspect-targets-examples/error-transport.full.json)。本次修复后的真实错误见[实施记录](2026-11-03-inspection-error-recovery.md#真实-mcp-错误示例)。`full/default` 均不裁剪错误。

## full、default 与字段含义

手牌完整示例：

```json
{
  "card": {"id": 5, "name": "Strike"},
  "playable": false,
  "target_type": "any_enemy",
  "requires_target": true,
  "targets": [
    {"id": 1, "kind": "enemy", "name": "Leaf Slime (S)"},
    {"id": 2, "kind": "enemy", "name": "Leaf Slime (M)"},
    {"id": 3, "kind": "enemy", "name": "Twig Slime (S)"}
  ],
  "reason": "Not enough Energy."
}
```

来自上述 card-energy 的完整样本。此时 default 与 full 一致；可用时 full 的 `reason:null` 在 default 中省略。名称的 nullable 契约同样按公共预设处理，不在缺少可读名字时用模型内部标识补齐。

- `card/potion` 只是当前查询对象的身份引用，不接入完整卡牌格式，不附送正文、费用或附魔等。`targets[]` 同样是生物／商人引用；本工具既不是手牌摘要，也不是生物详情。
- `playable/usable` 表示采样时可提交，不保证之后实际执行成功；查询到提交之间仍会重新检查状态。
- `requires_target` 是动作参数要求。为 true 时必须从当前 targets 选 ID，即使只有一个；为 false 时必须省略，不能传 self、null 或范围中的某个整数。
- `target_type` 区分指定、自身、群体、随机与奥斯提等行为，不能仅靠 requires_target 和 targets 的数量推断。例如群体与随机可以返回完全相同的对象集合。
- `targets` 不是每一击或所有后续效果的命中名单。不预抽随机数、不模拟召唤、不把查询时的范围用于裁剪实际结算。
- `reason` 成功可用时为 null，否则为简短提示。卡牌目前按能量、星星、无队友的顺序选原因，其余条件统一提示不可打出；不是完整的条件失败清单。
- `discardable` 仅药水存在，独立于 usable；自动药水和战斗外战斗药水均说明该字段不能由 usable 推断。
- 生物可见性仍检查实际节点及屏幕范围，这是非滚动战场的对象边界；不属于已取消的可浏览列表视口筛选。不补未入场、隐藏或被覆盖的目标。

## 参数与输出定稿

维持现有 card_id／potion_slot 互斥定位与 default/full，不增加 summary、批量或目标筛选参数。当前 default 已足够精简；身份、真假值、空范围、目标类型与 reason 都保留，各自承担不同的 UI 或操作含义。本轮只修复上述错误输出与恢复路径。

如果未来改动目标读取，可将手牌与药水重复的生物引用、名称、可见性组装做小范围复用；不应合并两者的目标合法性与 Self 规范化。原生 CardModel 与 PotionModel 已明确注明它们的 Self 参数不同；现在也没有因此重构执行流程的必要。

## 验证与剩余范围

- 原基线运行 `timeout 60s .tmp/mcp-venv/bin/python -m unittest tests.python.test_card_play tests.python.test_potion_actions tests.python.test_default_presets`：38 项通过，覆盖定位互斥、类型与 ID、公开返回校验、full/default 和许可行为；测试中的预期非法响应日志不表示测试失败。
- 24 个历史原生目标响应均通过当前 schema、目标校验、公开投影及结果一致性检查；另提供 3 个当前错误映射示例。
- 核对主记录链接、样本 manifest 和 JSON 内容，执行 `git diff --check`。没有变更运行代码，不要求重新构建 Mod。
- 未新增 RNG 无副作用实验或动画竞态测试；不得以 Python 测试替代这些验证。错误修复的两组 GUI 实测另见实施记录；AnyPlayer／AllAllies／Osty 卡牌分支、真正多人、第三方类型、全部药水自定义条件及任意 Mod 图层仍不是本轮实测结论。
- 后续已完成错误修复、四工具回查及两组隔离游戏验证，结果、代码变更和未验证范围以[实施记录](2026-11-03-inspection-error-recovery.md)为准。原始 38 项及历史样本校验不代替该记录的本次验证；未取样类型保持上文源码核对边界。本工具按已确认范围核销，其他工具的错误审阅继续留在用户 TODO。
