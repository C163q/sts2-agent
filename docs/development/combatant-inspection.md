# 战斗对象与充能球详情

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。`inspect_combatants` 查看当前已展示的玩家、敌人、友方召唤物、充能球与悬浮君王之剑；不执行动作、不触发实际鼠标悬停、不修改语言、目标或游戏流程。场景遵循[统一上下文](observation.md#场景上下文)，建筑师背景仍为 epilogue。

## 参数与预设

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| preset | default | full 保留完整静态数据及可读取的原生悬停说明；default 经[共用空值规则](mcp.md#输出预设)过滤；summary 合并生命显示，完全省略 hover_tips，并过滤普通 null |
| sources | 省略／null | 选择对象或条目及其关联说明；省略或 null 取全部，[] 不取任何对象，只保留 scene/screen、仍适用的 notes 和路径错误 |

```json
{"preset":"summary","sources":["enemies"]}
```

sources 接受非空字符串数组或 null，重复路径去重，结果保持原生顺序；未知参数、错误类型和不支持的 preset 整次 invalid_request。成功读取本身刷新动作许可，无须固定再调用 get_observation；明确拒绝保留已有许可，未知结果与状态过期的规则见[MCP 错误语义](mcp.md#调用和错误语义)。

## 数据范围

| 字段 | 内容 |
| --- | --- |
| scene/screen | 本次快照的房间／结算场景和页面；不因查看战场对象改写 scene |
| player／enemies[]／allies[] 的 hp/max_hp/hp_display/block | full/default 的可见生命、生命显示状态和格挡，与基础观察相同；没有格挡图标时为 0，生命条不可读时为 null |
| player／enemies[]／allies[] 的 health | summary 的生命摘要：例如 "70/80"、"∞"、"dead"、"unknown"；隐藏生命显式保留 null |
| player.powers | 当前展示的状态 name/amount |
| player.orb_slots | 原生球槽队列，保留真正的空槽 null；每个球为 name/passive/evoke，数值只取已展示标签 |
| player.sovereign_blades | 当前悬浮剑的绑定卡牌 id/name，沿用基础观察与手牌的稳定 ID；按 ID 排列 |
| enemies | 从左到右的敌人 id/name、生命、格挡、powers/intents；意图为 category/value |
| allies | 从左到右的友方召唤物 id/name、生命、格挡、powers；奥斯提不进入 enemies |
| allies[].block_shared_with | 实际格挡控件跟踪本地玩家时为 "player"，表示玩家同一份格挡的重复显示 |
| hover_tips | full/default 的原生主说明与附带解释，title/description/sources；summary 完全不返回 |
| source_indices | 筛选压缩数组时的原下标映射，键为未筛选结果中的数组路径；没有压缩则不增加该项 |
| errors | 无法匹配的选择器合并为 combatant_sources_unavailable，sources 保留首次请求顺序；有效部分继续返回，isError:false |
| notes | 与返回内容相关的数值说明、未完成选择的导航，以及 full/default 的不可悬停提示 |

能量、手牌、牌堆计数及可用动作分别通过 inspect_hand、牌堆工具或 get_observation 查看。不可读玩家在 full 中为 player:null；隐藏容器为 powers/intents:null，已展示但没有条目为 []；无显示计数为 amount:null，不以模型 Amount 补齐。default/summary 省略普通 null，球槽数组中的真实空位与 summary 的 health:null 保留。

## 对象与来源筛选

路径针对**当前未筛选的本工具列表**，不是生物 ID，也不保证与其他工具或下一次读取的下标相同。使用点分隔的完整路径段匹配；enemies.1 不匹配 enemies.10。

| 路径示例 | 选择范围 |
| --- | --- |
| player | 玩家生命、格挡、状态、球槽、悬浮剑 |
| player.block / enemies.0.block | 玩家／第一敌人的格挡 |
| enemies.0.hp / enemies.0.max_hp / enemies.0.hp_display | full/default 的第一敌人生命字段 |
| enemies.0.health | summary 的第一敌人生命摘要 |
| player.powers / player.powers.0 | 全部玩家状态／第一条状态 |
| player.orb_slots.0 | 第一球槽，包括真实空槽 |
| player.sovereign_blades.0 | 第一把悬浮剑 |
| enemies | 全部敌人 |
| enemies.0 | 第一敌人的生命、格挡、状态与意图 |
| enemies.0.intents / enemies.0.intents.0 | 第一敌人的全部意图／第一条意图 |
| allies.0 / allies.0.powers.0 | 第一友方召唤物／其第一条状态 |

多个路径取并集；父路径已包含子路径时不重复返回。选择状态／意图时保留所属敌人或友方的 id/name，不附送其他未选中分支。合法空分组返回空分组，没有悬停说明的条目仍可返回静态数据；不存在的下标、错误路径或不支持的字段进入 errors。筛选不跳过原生响应的完整校验。

叶路径对应当前预设的未筛选输出：full/default 使用 hp、max_hp、hp_display，summary 使用合并后的 health。选择生命或格挡不会附送其他状态及悬停说明。

数组紧凑返回，不用 null 填补未选中的位置。例如选择 enemies.2.powers.1，可产生以下定位映射：

```json
{
  "source_indices": {
    "enemies": [2],
    "enemies.2.powers": [1]
  }
}
```

此时返回 enemies 的第 0 项对应原第 2 项，其 powers 第 0 项对应原第 1 项。hover_tips.sources 与 note 中的路径仍为规范地址 enemies.2.powers.1，**可直接复用于后续 sources**；它们在存在映射时不是压缩后 JSON 的直接数组路径。整个父数组被选择时不增加无意义映射。共享说明只保留命中的来源，避免附送其他对象的信息。

## 读取边界

get_observation 的 full/summary 和本工具 summary 共用战斗对象读取入口的静态级别，包含可见生命、格挡和同伴共享关系；基础观察另行组装资源与手牌。两工具共用生命摘要格式。内部静态结果保留原始 null、空列表和数字，各工具最后应用自己的公开预设。full 在同一静态顺序上补充说明，不能因鼠标交互禁用而移除状态或意图。

底层 schema 48 的战斗对象必须包含完整生命字段；旧响应未提供这些字段时按旧格式读取，不推断缺少的数字。部分生命字段、错误类型或不合法显示状态均视为坏响应，空 sources 不能掩盖这些问题。

支持无遮挡战场及原生可查看的建筑师背景。选牌覆盖、地图、牌组、牌堆、模态框、未就绪或隐藏战场拒绝；通过眼睛切回战场可读，保留 notes.selection。没有额外要求必须是玩家回合或动作队列为空，但不保证动画任意时点都稳定。

拖动、瞄准或打出卡牌（InCardPlay）时，静态 summary 仍可读，full/default 返回具体拒绝并提示使用 summary；不把此门控误写为所有全局瞄准模式。工具列入 available_actions 表示至少存在支持的读取方式，不保证任何 preset 都能立即成功。

身体身份按实际战场显示判断；附属图标及计数不因屏幕坐标越界而截断，仍检查显隐、透明、纹理、缩放和真实裁剪。原生 UI 队列之外的旧球图像不枚举，任一真实槽位隐藏或被裁剪时整个 orb_slots 为 null，不能把未知槽当空槽。可见性不是任意 Mod 图层的逐像素遮挡判断。

球正文来自当前 NOrb 的原生 HoverTips，可以包含显式悬停才看见的被动／激发数字；这些数字不回填静态槽位字段。空槽通用帮助由 inspect_ui 提供。剑正文为可见绑定卡牌的原生 PileType.Deck 预览，在副本上刷新数值，不修改原牌缓存、不提供独立铸造数或隐藏卡牌位置。

状态使用当前 PowerModel 实例的动态原生说明，意图使用已显示 NIntent 绑定的模型、目标和拥有者；不读取 Monster.NextMove 或未来招式。标题与正文同时相同才共享提示，不因名称相同合并不同层数或回合数。英语格式化、Escape Artist 倒计时及施加者缓存的边界见[状态说明记录](../research/2026-11-01-power-descriptions.md)。

## 不可悬停与错误

图标展示但交互被禁用时，静态条目仍保留；full/default 在 notes.hover_tips_unavailable 中给出固定 message 与相关 sources。不猜测禁用原因或恢复时间。summary 和基础观察不尝试读取悬停，不附这条 note；sources 过滤同步裁剪它，空筛选不保留。原生本就 HasIntentTip:false 的意图没有说明，不算交互禁用。

无法识别的悬停类型、失效绑定、坏来源或格式异常仍整次失败，不能降级为普通 note 或由 [] 掩盖。意图预览数值的 note 只在返回相关意图数据时保留，规则见[数值说明](observation.md#数值预览说明)；没有 card_values note。

## 文件入口与验证

文件客户端默认 full，支持与 MCP 相同的预设和筛选：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_combatants --preset summary --sources enemies
```

底层文件请求只接受可选内部参数 level:summary/full，省略为 full；sources 由客户端投影。--raw 保留原生包装及控制信息，不做筛选投影。Python 转换原生响应时传 operation="inspect_combatants"，以同样规则生成可选的悬停状态 note。正常游戏加载与 IPC 配置见[加载指南](live-game.md)。

verify_combatants.py 与 verify_mcp_combatants.py 已使用当前共用契约断言，核对只读令牌、场景、静态字段、来源和共享说明；stdio 检查使用独立截图配置，避免依赖个人配置中的工具数量。运行期间避免手动改变游戏：

```sh
python3 -m tests.game.verifiers.verify_combatants --ipc-dir .tmp/live/ipc --output .tmp/live/combatant-inspection.json --report .tmp/live/combatant-inspection-check.json
```

完整预设、对象筛选、球／剑／同伴、错误续接及不可悬停 note 使用[combatant_presets 清单](../../tests/game/data/gui_suite_combatant_presets.json)，执行方法见[图形测试](gui-testing.md)。set_test_combatant_hover 仅在测试模式与套件双门控下开放文件请求，测试脚本 finally 恢复，不属于 MCP 玩法工具。

源码核对与验证证据见[工具审阅](../research/2026-11-03-inspect-combatants-review.md)和[实施记录](../research/2026-11-03-combatants-implementation.md)，适用范围以各记录注明的基线与用例为准。全部状态模板、第三方悬停、多人模式及任意动画组合尚未穷举验证。
