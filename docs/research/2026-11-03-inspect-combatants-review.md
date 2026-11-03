# inspect_combatants 场景与现有参数核验

> 当前状态：本轮场景核验与错误审查完成，尚未核销。已记录 3 项问题，提供 21 份完整公开 JSON，完成 82 项 Python 回归、11 项错误探针及七组隔离对局与独立建筑师背景采样。参数、摘要与修复范围待定稿，未改运行代码；未验证分支见末节。暂无阻塞。

## 优先关注的问题

| 编号 | 优先级与状态 | 已确认的问题与影响 | 建议处理范围 |
| --- | --- | --- | --- |
| COMBATANT-01 | 中；待修复 | 当前画面不允许查看时，Mod 有明确的 `Combatant details are unavailable in the current screen.`，但没有显式许可公开该消息，MCP 仍返回 `The requested action is unavailable.`。本地未知字段也只返回通用参数错误；非法 preset 与参数对象类型的说明则已具体 | 使用现有安全公开错误机制；为未知字段明确列出允许参数。区分没有可读战场和正在拖动／打出卡牌，不转发异常堆栈或任意底层消息 |
| COMBATANT-02 | 中；待修复 | `GameTools.PURE_READS` 未包含本工具。已有成功观察后，原生 `illegal_action/invalid_request/expired_request` 会清掉旧许可，下一动作被 MCP 以 `observation_required` 拒绝；恢复提示也要求再观察。无需状态改变即可通过模拟传输复现，现有测试还明确断言此旧行为 | 接入已审阅四工具的明确读取拒绝恢复。仅保留原有许可，不制造新许可；过期状态、超时、异常、坏响应、取消和控制器冲突继续清许可，实际动作仍由 Mod 复核 |
| COMBATANT-03 | 中；验证入口待修复 | [verify_combatants.py](../../tests/game/verifiers/verify_combatants.py) 仍断言顶层没有 screen/allies、玩家只有 powers/orb_slots；[verify_mcp_combatants.py](../../tests/game/verifiers/verify_mcp_combatants.py) 还固定旧工具清单、旧玩家结构。当前正常响应也会被判失败，文档原先仍推荐它们 | 更新这两个专项脚本的结构、来源与工具发现检查，保留只读、语言、共享提示、前后令牌一致性断言；不以删掉断言解决。文档已标明限制 |

前两项属于[用户 TODO](../development/TODO.md#当前工具审阅结束后处理)的本工具范围；不据此勾销其他工具的完整审阅。COMBATANT-03 是验证设施缺口，不代表生产工具已经返回错误玩法信息。上述问题优先于新增筛选或摘要。

## 核对基线与证据

- 核验日期：2026-11-03；代码 `fb4749d`，Mod `0.52.0`、MCP `0.53.0`、原生 schema `34`。这是本次证据基线；当前版本统一维护于[README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`，release、build `59260271`；RitsuLib `0.6.10` 的该版本兼容运行时。游戏目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll`，本轮复核 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 隔离采样 Mod DLL SHA-256：`3dbcd6fd019826352f48f7265aea72372f4a8049c69b8ad2cf226de0fb464bc1`。中文 UI，独立测试存档和 IPC，不安装正式 Mod。
- 原生入口：[GameAdapter](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[CanInspectCombatants 与 available_actions](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[统一观察上下文](../../src/Sts2Agent/Observation/ObservationContext.cs)。读取由 [CombatantInspection](../../src/Sts2Agent/Observation/CombatantInspection.cs)、[CombatObservation](../../src/Sts2Agent/Observation/CombatObservation.cs)、[OrbInspection](../../src/Sts2Agent/Observation/OrbInspection.cs)、[SovereignBladeInspection](../../src/Sts2Agent/Observation/SovereignBladeInspection.cs)、[HoverTipText](../../src/Sts2Agent/Localization/HoverTipText.cs)负责。
- MCP：[工具定义](../../src/sts2_mcp/mcp_catalog.py)、[派发与动作许可](../../src/sts2_mcp/game_tools.py)、[详情校验](../../src/sts2_mcp/output/combatant_details.py)、[预设](../../src/sts2_mcp/output/presets.py)、[公开错误](../../src/sts2_mcp/output/error_output.py)。
- 原生悬停证据复核自同一程序集的本地反编译产物：`.tmp/2026-11-01-power-descriptions/source/Nodes.Combat.NPower.cs` 的 OnHovered、`.tmp/2026-11-01-minion-attribution/source/NIntent.cs` 的 OnHovered、`.tmp/2026-11-01-orb-events/source/Nodes.Orbs.NOrb.cs` 的 OnFocus、`.tmp/2026-11-02-companions/source/Nodes.Combat.NCreature.cs` 的 ShowHoverTips，以及同目录 NSovereignBladeVfx 的 UpdateHoverTip。没有将它们当作新增 UI 实测。原调查见[状态动态说明](2026-11-01-power-descriptions.md)、[同伴与悬浮剑](2026-11-02-companions.md)。
- 本轮采样与模拟错误探针保存在不入库的 `.tmp/2026-11-03-inspect-combatants-review/`。入库示例仅包含公开玩法 JSON，内部令牌、路径、进程信息和测试配置不进入返回示例。

## 当前参数与职责

```json
{"preset":"full"}
```

目前只有通用 `preset`，支持 default/full，省略时为 default。没有 summary、对象 ID 筛选或 sources 筛选；未知字段拒绝，不忽略。MCP 参数在 Python 校验与投影，原生文件操作不接受玩法参数。

该工具显式读取玩家、可见敌人及友方召唤物的状态说明、当前意图解释、已生成充能球说明和悬浮君王之剑的牌面预览。不触发鼠标悬停、不改变语言或页面、不进入瞄准、不执行动作、不预演伤害或未来招式。成功读取本身可提供下一步动作许可，不要求先调用 get_observation；能否出牌或结束回合仍独立判断。

工具描述当前为：

```text
Read visible combatant powers, enemy intent explanations, occupied orb help and floating Sovereign Blade previews.
Unavailable while aiming or playing a card.
```

第二句的实际整次门控是手牌 `InCardPlay`，包括卡牌拖动／瞄准／打出流程；不是独立检查所有 `NTargetManager.IsInSelection`。剑的正文另有全局瞄准与攻击动画门控。后续提示词宜明确为卡牌操作期间，避免把所有形式的瞄准一概解释为整次拒绝。

## 返回结构与 UI 语义

| 字段 | 当前含义 |
| --- | --- |
| scene/screen | 从本次基础快照复制的统一上下文；建筑师是 epilogue，不因读取战斗背景改为 combat |
| player | 可见玩家的 powers、orb_slots、sovereign_blades；无玩家可见节点时为 null，不提供玩家名称、生命、格挡、能量或星星 |
| enemies[] | 按战场横坐标排列的敌人 id/name/powers/intents；ID 与基础观察一致 |
| allies[] | 同样按位置排列的友方召唤物 id/name/powers，奥斯提不进入 enemies |
| powers[] | 实际可悬停图标的 name/amount；amount 来自标签，不以模型层数补齐 |
| intents[] | 当前渲染的 category/value，不读取 Monster.NextMove；可悬停且 HasIntentTip 为真时提供对应正文 |
| player.orb_slots | 原生队列和空槽，与基础观察一致；未悬停标签读不到的数值仍为 null |
| player.sovereign_blades[] | 可见剑所绑定卡牌的稳定 id/name，不是完整手牌格式，不额外提供独立铸造层数 |
| hover_tips[] | title/description/sources。标题与正文同时相同才合并，不因标题相同合并不同层数、拥有者或回合数的正文 |
| notes | 需要时保留意图数值与未完成选择的导航说明，不增加 card_values |

本工具没有 `available_actions`、turn、顶栏、生命和格挡汇总或 transition；由 get_observation 提供基础战况和可用动作。它也不返回目标可选范围，后者由 inspect_targets 提供。

`sources` 是本次详情返回内的路径，例如 `player.powers.0`、`enemies.1.intents.0`、`allies.0.powers.0`、`player.orb_slots.0`、`player.sovereign_blades.0`。下标从 0 开始，只对本次结果有效，不能当成生物 ID。详情只保留可悬停条目，因此 power/intent 下标不保证与基础观察的数组下标相同；同一对象可关联多个提示，一个提示也可关联多个对象。

充能球 hover_tips 可出现其当前被动／激发值，即使基础数字标签尚未显示；这是显式查看可获得的信息，不能把这些数字回填到 orb_slots 的未显示字段。空槽在数组中为 null，不生成占用球正文；通用空槽帮助由 inspect_ui 提供。

悬浮剑的正文来自原生 `PileType.Deck` 预览，按可见绑定卡牌重算预览而不改写原牌缓存；正文以 title/description 表达，没有完整卡牌的费用、类型和悬停解释结构。其他原生 CardHoverTip 也投影为标题与正文，例如 Swipe 已公开的被偷卡牌预览；不推断偷牌来源、隐藏牌堆顺序或未来归还结果。

### full 与 default

full 保留原生已生成的 null；default 仅按公共规则省略普通 null，数组中的空充能球槽位不删除。无可读玩家为 player:null；容器隐藏时 powers/intents 为 null；容器可见但无可读条目时为 []。可见无计数图标的 amount:null 不等于 0。上述未知、空、零值不能互换。

球和剑仍沿用各自非滚动战场的可见性边界；本工具不存在应取消的可浏览列表视口截断。隐藏、离屏、透明或不可悬停图标不补全文；未知提示类型或绑定失效使整次读取失败，不返回猜测内容。

## 场景目录

以下按真正的结构／读取分支分组；不同怪物和状态名字属于内容变化，不逐个列为独立协议。下方链接均为本轮隔离游戏的完整公开响应，没有用省略号截断。调用与来源位置见[样本清单](2026-11-03-inspect-combatants-examples/manifest.json)；ID 只在对应测试局有效。

| 实测样本 | 完整 JSON |
| --- | --- |
| 普通战斗，无状态图标，混合攻击／塞牌意图 | [combat.full](2026-11-03-inspect-combatants-examples/combat.full.json) |
| 四种球与一个空槽；可见数字和悬停数字不同 | [orbs.full](2026-11-03-inspect-combatants-examples/orbs.full.json)、[orbs.default](2026-11-03-inspect-combatants-examples/orbs.default.json) |
| 扩大球槽、再生成闪电球 | [orbs-expanded.full](2026-11-03-inspect-combatants-examples/orbs-expanded.full.json)、[orbs-channelled.full](2026-11-03-inspect-combatants-examples/orbs-channelled.full.json) |
| 奥斯提及其状态说明 | [osty.full](2026-11-03-inspect-combatants-examples/osty.full.json) |
| 悬浮剑及铸造后的正文，15 → 31 点预览 | [blade.full](2026-11-03-inspect-combatants-examples/blade.full.json)、[blade-forged.full](2026-11-03-inspect-combatants-examples/blade-forged.full.json) |
| 偷窃草蜢第一回合、偷牌后，逃脱计数 5 → 4 | [hopper.full](2026-11-03-inspect-combatants-examples/hopper.full.json)、[hopper-after-steal.full](2026-11-03-inspect-combatants-examples/hopper-after-steal.full.json) |
| 未完成选牌，眼睛切回战场，保留导航 note | [pending-selection-battlefield.full](2026-11-03-inspect-combatants-examples/pending-selection-battlefield.full.json)、[default](2026-11-03-inspect-combatants-examples/pending-selection-battlefield.default.json) |
| 建筑师背景 | [epilogue.full](2026-11-03-inspect-combatants-examples/epilogue.full.json) |
| 主菜单、事件、选择页拒绝 | [main-menu](2026-11-03-inspect-combatants-examples/error-main-menu.full.json)、[event](2026-11-03-inspect-combatants-examples/error-event.full.json)、[selection](2026-11-03-inspect-combatants-examples/error-selection.full.json) |
| 牌组、弃牌堆、地图覆盖拒绝 | [deck](2026-11-03-inspect-combatants-examples/error-deck.full.json)、[pile](2026-11-03-inspect-combatants-examples/error-pile.full.json)、[map](2026-11-03-inspect-combatants-examples/error-map.full.json) |
| 不支持的 summary、未知 enemy_id 参数 | [unsupported-summary](2026-11-03-inspect-combatants-examples/error-unsupported-summary.full.json)、[unknown-argument](2026-11-03-inspect-combatants-examples/error-unknown-argument.full.json) |

**读取分支总表：**下表同时列出已采样与源码支持的分支；不以表格条目代替逐场景实测。

| 场景 | 当前行为 |
| --- | --- |
| 正常战斗，玩家／敌人没有状态 | 成功，保留可见空状态列表和当前意图说明 |
| 同类状态由多个对象持有 | 成功；相同标题和正文共享 sources，计数或描述不同则分开 |
| 特殊意图、倒计时状态、被偷卡牌预览 | 成功；只解释当前显示的提示，不枚举后续招式 |
| 故障机器人充能球 | 成功；球槽保留空位，正文包含当前原生悬停说明 |
| 亡灵契约师与奥斯提 | 成功；独立 allies，状态来源不占用敌人下标 |
| 储君与君王之剑 | 成功；剑身份与显式牌面正文分开，悬浮动画不改变来源排序 |
| 选牌覆盖战斗 | 拒绝，不穿透候选页 |
| 眼睛切回战场，但选择仍待完成 | 成功；notes.selection 提示返回选择，不表示现在可以正常出牌 |
| 地图／牌组／牌堆／模态框覆盖战斗 | 拒绝，不自动关闭覆盖 |
| 建筑师可见战斗背景 | 成功，scene:epilogue、screen.view:epilogue |
| 敌方回合或动作队列忙碌 | 没有额外的玩家回合／队列为空门控；只在采样时战场与悬停对象可读、且不在卡牌操作中时成功，不承诺动画过程稳定 |
| 没有战场的主菜单、事件、商店、火堆、宝箱等 | 拒绝，不把不可用伪装为成功空列表 |
| 战后仍保留可见战场节点，未被奖励或结果页覆盖 | 按可见战场门控判断，scene 沿用统一入口，不强制改写为 combat；未新增自然过渡实测 |
| 隐藏玩家／状态容器／意图容器、单独禁用悬停 | 按前述 null／空列表与悬停边界表达；不是读取整个后台模型 |
| 非法参数、坏响应、超时、异常、控制器冲突 | 顶层 error；不能按成功空数据处理，具体错误审查见下一节 |

## 错误与恢复逐项核对

| 路径 | 当前表现 | 判断 |
| --- | --- | --- |
| 未知字段，例如 enemy_id | 本地 invalid_request，correct_request，旧许可保留，无 IPC | 许可正确；原因需改为明确只支持哪些参数 |
| summary 或非法 preset 类型、非对象参数 | 本地 invalid_request，已有具体固定说明，旧许可保留 | 正确；当前未支持 summary 本身不是错误 |
| 明确原生 illegal_action | 原生原因丢失，旧许可清除，recovery:get_observation | COMBATANT-01/02 |
| 明确原生 invalid_request／expired_request | invalid_request 需纠正请求，但两种拒绝均清除已有许可 | COMBATANT-02；本工具正常 MCP 参数校验后很少触发原生 invalid_request，不能冒充 GUI 已触发 |
| 首次调用即拒绝，之前没有许可 | 保持没有许可 | 正确，修复也不能生成许可 |
| 成功读取 | 校验整个响应后使用本次令牌，允许后续动作独立校验 | 正确，不要求固定再 get_observation |
| stale_state、timeout、game_error、坏结构／来源、连接异常、取消、控制器冲突 | 清除或不发布许可；未知执行结果不能自动重试 | 保持共用保守策略；没有把所有错误都认定为可继续 |

11 项独立模拟传输探针保存在 `error-probe.json`：4 种本地参数拒绝保留许可且 end_turn 实际提交，3 种明确原生拒绝均导致下一 end_turn 被 MCP 拦截；另外检查 stale_state、game_error、timeout 与坏成功响应仍清许可。模拟验证复现的是 Python 许可路径，原生可见性拒绝另由隔离游戏采样核对，不将二者混为同一证据。

## 参数与摘要候选，尚未定稿

有三种合理范围：

1. 维持 default/full，仅修错误和验证入口。最少改动，但仍须整批读取所有长说明。
2. **建议：沿用 inspect_ui 的方向，增加 summary 与 sources 精确筛选。** summary 保留现有对象身份、状态计数、意图、球槽、剑引用、提示标题及来源，仅删除 hover_tips[].description；full/default 提供所选来源的完整说明。保留必要 notes。不引入伤害预测或新的机制字段。
3. 按生物 ID、球槽等分别设计过滤。适合按对象查看，但玩家、球、剑与敌人使用不同定位体系，需要多个参数；暂不建议先加一套复杂筛选。

第二种若采用，建议 sources 与 inspect_ui 使用相同规则：可选字符串数组、按精确路径匹配、合并缺失项错误、空数组表示不取悬停提示；共享提示只保留命中的来源。身份数组保留原下标、不压缩或重排，防止来源错指。仍先读取并校验完整数据，不因过滤绕过失败。

summary 的作用是说明索引，不等于 get_observation 战斗摘要。若认为已有基础观察足以索引状态，也可以只接受 sources，不增加 summary。是否省略空列表、进一步改变球槽或意图字段，都留待逐项讨论，不提前实施。

## 有依据的小范围重构

- 读取可用性在 CanInspectCombatants 和 CombatantInspection.ReadAll 重复判断，可用同一“不可用原因”入口供 available_actions、拒绝说明及最后读取复核使用；保留读取端的状态复核，不仅依赖之前菜单列出的可用动作。
- 错误与许可直接接入前一轮已有共用层，不再创建本工具专属恢复机制。
- 原生 CombatObservation.Powers 与详情 Powers 有意使用不同的可悬停筛选；不能为减少重复直接把基础图标列表替换为详情列表，否则会丢失仍可看见但不可悬停的图标。若后续抽取共用读取，应显式保留这项差异，本轮不需扩大到整个观察架构。

## 验证与剩余范围

- 已运行现有 MCP、同伴、上下文与 default 预设测试：82 项通过。它们包含明确拒绝后清许可的旧断言，因此通过不代表 COMBATANT-02 已解决。
- 11 项错误探针通过“当前行为”断言，复现问题；不是修复后的通过记录。
- `gui-3/report.json` 为 passed：自有进程 PID 23489，七个独立测试局及主菜单样本；`ending-gui/report.json` 为 passed：另一自有进程 PID 23946，胜利奖励及建筑师背景。逐次通过真实 stdio MCP 读取 full/default，比较共用空值规则、同一状态的重复读取、所有悬停来源及读取前后原生观察；截图与原生文件响应一并保留。21 份入库 JSON 逐份与证据原样比较，不由旧版本响应补字段。
- 两个自有进程均已关闭。无运行代码变化，未安装正式 Mod；本次采样不是旧验证脚本已修复的证据。
- `gui/` 首次采样因脚本把空抽牌堆误当成覆盖页而失败；空堆返回原生反馈并保持战场符合现有契约。改为先正常打出防御，再查看非空弃牌堆。`gui-2/` 采集完地图覆盖后，多做了一次原生不允许的 close_map，返回 `The current map cannot be closed.` 而终止；测试开局地图不保证能关闭。最终采样在地图拒绝记录完成后按独立局生命周期清理，不修改地图动作规则。两份失败目录保留，不称为全绿批次。
- 将本轮真实原生响应通过替代传输回放给 `verify_combatants.main`，在第 39 行旧顶层字段断言复现失败；`verify_mcp_combatants` 的旧清单／结构问题按源码确认，没有将其运行标为通过。已同步开发指南：撤下旧脚本的可用命令示例并标注限制，同时将“瞄准”明确为实际 InCardPlay 门控；问题与未修复状态以本记录跟进。
- 本轮没有修改运行代码，不需要为文档重新构建 Mod；游戏采样使用上述已构建 DLL。
- 玩家或状态／意图容器被单独隐藏、禁用悬停、HasIntentTip:false 和卡牌拖动门控，本轮核对源码及既有原生检查，没有逐一新增公开响应样本；敌方回合、自然战后过渡和球／剑攻击动画的每个时点同样没有逐帧新采样。
- 尚未新增全部状态、所有意图／球／多剑组合、真正多人、第三方悬停类型、任意图层像素遮挡或动画竞态穷举；模型模板正确不等于所有生命周期均已实测。
