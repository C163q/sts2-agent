# inspect_combatants 场景与现有参数核验

> 当前状态：本轮场景核验与错误审查完成，尚未核销。已记录 3 项问题，提供 21 份完整公开 JSON，完成 82 项 Python 回归、11 项错误探针及七组隔离对局与独立建筑师背景采样。已确认 summary 完全省略 hover_tips，sources 同时筛选对象数据及关联说明，[] 只保留场景上下文及必要 notes；细粒度定位、显式 null 与修复范围待定稿，未改运行代码。未验证分支见末节。

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

## 参数与摘要设计

### 已确认、尚未实现

summary 表示不悬停时能够看到的对象信息，完全省略整个 hover_tips，包括标题、正文及来源。例如 power 只给 name/amount，意图给 category/value，球槽与剑保留基础观察能够看到的字段。其余普通 null 按 default 规则处理，球槽的真实空位不删除。

sources 筛选对象数据及其关联悬停说明，不仅裁剪 hover_tips；preset 决定被选中对象的信息精简程度。两项独立组合：

| 调用条件 | 数据范围 | 悬停说明 |
| --- | --- | --- |
| 省略 sources，default/full | 全部对象 | 读取允许提供的说明 |
| 省略 sources，summary | 全部对象的静态信息 | 不出现 hover_tips |
| sources:["enemies"]，default/full | 仅敌人数据 | 仅敌人关联说明，共享提示裁掉其他来源 |
| sources:["enemies"]，summary | 仅敌人的静态数据 | 不出现 hover_tips |
| sources:[]，任意 preset | 不返回 player/enemies/allies 等对象字段 | 不出现 hover_tips |

scene、screen 和仍适用的 notes 保留；仅用于解释已过滤内容的 note 不保留。例如选择仍未完成时保留 notes.selection，而没有敌人意图数据时移除 notes.enemy_attack_intents。部分路径失败时仍可返回 errors。显式筛掉字段不是“不可见”，full 也不把未选中的对象填成 null 或空数组。

未指定筛选表示全部；[] 表示选中集合为空，不作为“全部”的别名。现有 inspect_hand.card_ids、inspect_selection.card_ids、inspect_relics.relic_indices、inspect_ui.sources 已采用这一集合语义；显式 JSON null 目前会被参数校验拒绝。新 sources 是否额外接受显式 null 表示全部仍待定稿，不擅自改变其他已审阅工具。

### 设计 JSON 示例

以下按已确认规则投影入库 full 样本，只用于说明拟实现契约，**不是已实现接口的实测返回**。数值沿用原样本，不新增游戏机制信息。

调用 `{"preset":"summary","sources":["enemies"]}`，投影[草蜢原始样本](2026-11-03-inspect-combatants-examples/hopper.full.json)：

```json
{
  "scene": "combat",
  "screen": {
    "status": "visible"
  },
  "enemies": [
    {
      "id": 1,
      "name": "Thieving Hopper",
      "powers": [
        {
          "name": "Escape Artist",
          "amount": 5
        }
      ],
      "intents": [
        {
          "category": "attack",
          "value": "17"
        },
        {
          "category": "card_debuff",
          "value": ""
        }
      ]
    }
  ],
  "notes": {
    "enemy_attack_intents": "Enemy attack intents already include current preview modifiers, including effects on you. Do not apply those modifiers again; the number is not guaranteed HP loss."
  }
}
```

调用 `{"preset":"summary","sources":[]}`，投影[待选牌战场样本](2026-11-03-inspect-combatants-examples/pending-selection-battlefield.full.json)：

```json
{
  "scene": "combat",
  "screen": {
    "status": "visible"
  },
  "notes": {
    "selection": "Selection pending; return with set_selection_view(view=\"selection\") before choosing."
  }
}
```

普通战斗若没有仍适用的 notes，空筛选结果只含 scene/screen；不创建空 notes 占位。

### 分组与精确路径建议

sources 同时支持具体对象／条目和分组前缀，按点分隔的路径段匹配；细粒度定位规则待定稿。

| 选择器 | 拟选择的数据及关联说明 |
| --- | --- |
| player | 玩家的状态、充能球及悬浮剑 |
| player.powers | 全部玩家状态 |
| player.orb_slots.0 | 第一个球槽 |
| player.sovereign_blades.0 | 第一把悬浮剑 |
| enemies | 所有敌人 |
| enemies.0 | 第一个敌人的状态及意图 |
| enemies.0.intents | 第一个敌人的全部意图 |
| enemies.0.intents.0 | 第一个敌人的第一个意图 |
| allies.0 | 第一个友方召唤物 |

- 精确命中或以“选择器加一个点”开头的实际来源命中；enemies.1 不匹配 enemies.10。多个选择器取并集，去重并保留原生顺序。
- 细粒度选择保留必要的所属对象身份，避免只得到数值却不知道属于哪个敌人；不附送未选中的其他状态、意图或玩家信息。
- 空分组本身合法，例如 enemies:[] 下选择 enemies；没有悬停提示的可见条目仍可返回静态数据。不存在的对象下标、不支持的字段或格式错误的路径合并到 errors，有效部分继续返回。
- sources:[] 不生成 hover_tips:[]，也不保留空的对象字段；它是空选中集合，不是保留全部基础数据、只隐藏说明的替代 preset。
- 数组筛选不能把返回位置冒充原选择器下标，悬停来源须关联正确对象；尤其不能用 null 补齐未选中的球槽，因为 null 在球槽中已经表示真实空位。细粒度实现需确定紧凑列表与原位置映射，或其他明确的定位方式；在此之前不把此前“保留全部数组、仅筛提示”的方案当作实施依据。
- 先读取并校验工具要求的完整数据，再应用选择与 preset，不因空筛选放过错误响应；结果仍不生成新的未知信息。

inspect_ui 当前只筛悬停提示且仅做精确匹配；本轮不擅自扩大其职责。可复用通用参数校验和共享提示投影，不能将两个工具的对象筛选语义强行合并。

## 有依据的小范围重构

- 读取可用性在 CanInspectCombatants 和 CombatantInspection.ReadAll 重复判断，可用同一“不可用原因”入口供 available_actions、拒绝说明及最后读取复核使用；保留读取端的状态复核，不仅依赖之前菜单列出的可用动作。
- 错误与许可直接接入前一轮已有共用层，不再创建本工具专属恢复机制。
- 静态对象列表与悬停能力须分离。当前详情 Powers/Intents 会跳过 MouseFilter.Ignore 条目，不能仅删除现有 full 的 hover_tips 就宣称 summary 与基础画面一致。应共用已核对的可见图标读取，只有说明生成受可悬停条件限制；统一核对 get_observation 与本工具的图标／标签边界，避免不同 preset 因悬停条件产生不同对象下标。这是已确认静态摘要要求涉及的小范围重构，不扩展到整个观察架构。

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
