# default 预设与空值语义审查

当前状态：输出契约审查完成；已确认覆盖全部玩法 JSON 工具，过滤例外方案待确认。尚未修改工具实现、默认值或游戏 Mod。

## 范围与基线

- 核对日期：2026-11-02；代码基线 `d831af2`，MCP / Mod `0.47.1`，原生 schema `29`。
- 本次核对项目的输出构造、验证、投影及相关测试，不改变游戏 API 的调用和可见信息边界；未进行新的游戏内实测。
- 已确认新增 `preset:"default"`，并将它作为省略 `preset` 时的行为；`full` 保留本工具现有完整输出，包括原有空值。已有 `summary`、`selectable`、`actions_only` 保持各自行为，不自动叠加 default 的过滤。
- 覆盖全部 42 个玩法 JSON 工具；可选的第 43 个工具 `capture_screenshot` 只返回文件信息，本轮不加 preset。
- `get_observation` 本轮只增加 default 的空值过滤，不设计新的 summary。`inspect_deck` 和 `inspect_pile` 的 `detail_level` 保持独立，默认仍为 summary；`preset:"full"` 不会擅自将它改成 full。
- 动作工具的 full 指保留现有的精简动作回执，仍不附送完整观察；default 在该回执上过滤空值。

## 已核对的入口

| 范围 | 当前实现与审查重点 |
| --- | --- |
| 工具目录 | [mcp_catalog.py](../../src/sts2_mcp/mcp_catalog.py) 声明 42 个玩法工具，只有观察、手牌、选牌、遗物、地图这 5 个工具已有 preset |
| 调用和权限 | [game_tools.py](../../src/sts2_mcp/game_tools.py) 在完整结果校验后处理令牌；不能对内部结果提前过滤，否则会破坏停止边界和合法性判断 |
| 输出声明 | [game_output.py](../../src/sts2_mcp/output/game_output.py) 的 GAMEPLAY 递归展开得到 288 个 nullable 路径，包含重复卡牌结构；专门读取器仍有更严格的字段与状态检查，不能只看总表 |
| 专门读取器 | [inspection_details.py](../../src/sts2_mcp/output/inspection_details.py) 的 READERS，以及目标、牌组、牌堆的独立分派；覆盖只读详情、查看操作和全部动作的投影入口 |
| 事件 | [transition_details.py](../../src/sts2_mcp/output/transition_details.py)、[TurnJournal.cs](../../src/Sts2Agent/Events/TurnJournal.cs)、[CardAdditionJournal.cs](../../src/Sts2Agent/Events/CardAdditionJournal.cs)；核对事件必需字段、未知数值、来源和公开去向 |
| 牌面比较 | [SelectionInspection.cs](../../src/Sts2Agent/Observation/SelectionInspection.cs)、[selection_presets.py](../../src/sts2_mcp/output/selection_presets.py)；升级、附魔、确定变牌、随机变牌和筛选后的预览 |
| 槽位和引用 | [CombatObservation.cs](../../src/Sts2Agent/Observation/CombatObservation.cs)、[OrbInspection.cs](../../src/Sts2Agent/Observation/OrbInspection.cs)、[player_output.py](../../src/sts2_mcp/output/player_output.py)、[combatant_details.py](../../src/sts2_mcp/output/combatant_details.py)；数组位置及共享提示的索引不能变化 |
| 图像与最终封装 | [divination_details.py](../../src/sts2_mcp/output/divination_details.py)、[mcp_server.py](../../src/sts2_mcp/mcp_server.py)；占卜 PNG 存在 ImagePayload.image 中，复制成普通 dict 会丢图；文字 JSON 与 structuredContent 应保持一致 |

## 推荐的统一规则

采用递归删除对象中值为 null 的键，并集中保留以下三类例外。按结构路径判断，不在各工具中散布补回字段的代码，也不对所有同名字段一概豁免。

### 1. 数组中的 null 元素全部保留

只删除对象键，不删除数组元素，也不改变数组长度和顺序。已核实需要保留的位置包括：

- `potion_slots[]`、`top_bar.potion_slots[]`：null 是已确认空槽，药水动作及共享说明通过槽位下标引用。
- `player.orb_slots[]`：null 是空充能球槽，队列位置决定激发顺序，悬停来源也通过下标关联。
- `top_bar.bosses[]`：null 保留实际存在、但暂未识别名称的首领图标位置。

该规则对所有数组生效，避免未来新增槽位遗漏。数组中的非空对象可以继续过滤内部普通空值，但不能因过滤后得到 `{}` 而删除该对象；`[{}, null]` 仍能区别已占用但信息不可读的位置与空槽。

### 2. transition.events 中已有的 null 完整保留

建议将事件作为一组稳定的事实记录，保护每个已验证事件及其嵌套引用，而非只保护 before / after：

| 已存在的空值 | 需要保留的含义 |
| --- | --- |
| `before:null`、`after:null` | 状态变化的端点不可读、没有公开数字，或计数不适用；双方都为 null 时，状态图标仍可能发生 applied / removed |
| `hp_loss:null` | 伤害事件存在，但无法从 UI 确认生命损失数值，不能解读成 0 |
| `card_added.pile:null` | 已看到新增卡牌身份，但本次尚无公开去向，不能猜为 deck 或当前所在牌堆 |
| `source:null` | 没有可可靠归属的公开来源，不能补成上一张牌；活雾小怪自爆等场景尤其需要避免误读 |
| 身份引用中的 `name:null` | 实体或卡牌 ID 已知，但尚无可公开的名称；不得用模型补全 |

只保留事件本来就有的字段，不为缺失的 actor、source、target 等添加 null，也不补造事件。这个范围略宽于逐字段白名单，但事件通常较短，能避免后续新增事件忘记登记关键空值；原有 `events:[]` 和事件顺序完整保留。

### 3. 已展开的牌面比较保留 before / after 两侧子树

保护以下路径中的 before 和 after，包括两侧对象内部的空值：

- `selection.upgrade_preview`
- `selection.upgrade_previews[]`
- `selection.enchant_previews[]`
- `selection.transform_previews[]`

随机变牌的 `random:true, after:null` 必须保留，表示未公开结果。确定比较的某一侧也可能只有原牌 ID、不可读名称与正文；两侧费用等字段中的 null 同样属于比较信息，不能只保留最外层 before / after 键。

未展开或被筛选掉的整个 `upgrade_preview:null` 可以省略；不能因此生成新预览。预览存在时保留两侧原有内容，也不为原本缺失的字段补 null。

## 其余空值的处理结论

| 字段类别 | default 的建议处理与解释 |
| --- | --- |
| 非当前场景对象，例如 `event:null`、`selection:null`、`rewards:null` | 删除；scene、screen、现有状态标记和 available_actions 保留 |
| 被覆盖对象内部的正文、按钮、选项等空值 | 删除；保留该对象及 `status:"covered"`，不补回底层内容 |
| `powers`、`intents`、`hand`、`cards`、`selected_ids`、整个 `orb_slots` 等集合为 null | 可以省略；省略表示本输出没有提供可用内容，绝不能当作 `[]`。已有 `[]` 必须保留，表示明确返回了空集合；详情筛选后的 `[]` 仍遵循各工具已有筛选语义 |
| 普通生命、资源、计数、意图值、充能球数值 | 删除 null；缺失不能推成 0。现有 hp_display、意图类别、球名等非空信息照常保留 |
| 普通卡牌名称、类型、费用、正文等空值 | 删除 null；已知 ID、匿名名称、可见标记仍保留。不推断隐藏身份、免费、可打出或无效果；不新增星费或附魔信息 |
| 普通遗物 `counter:null`、`melted:null` | 删除；缺失不等于 counter 为 0 或 melted 为 false。显式 full 与已有 summary 仍保留原有空值；蜡质遗物 false / true 均保留 |
| `current_node:null` | 可以省略，仍表示当前输出没有节点 ID；不据此推断所在房间或合法选路，使用 can_travel 和 selectable_nodes |
| 商店 `price:null`、`affordable:null` | 删除；不能推成免费或不可负担，enabled / used 及物品身份照常保留 |
| `reason:null`、无标题提示 `title:null`、奖励 `linked_group:null`、未显示的占卜工具或对话等 | 删除；可用性、失败原因、实际提示正文、奖励身份与占卜阶段仍以返回的非空信息为准 |
| `0`、`false`、`""`、`[]`、`{}` | 全部保留，不能使用真值判断顺便删除 |

default 必须明确声明“省略空值不表示零、否或空集合”；它不是变化增量，也不能将某次省略理解为沿用上次值。调用者需要明确空值时可以请求 full。此次不额外引入 unknown / not_applicable 等状态枚举，因为现有 null 本身未区分所有原因。

## 方案比较

1. **推荐：统一递归过滤，加上述三类结构例外。** 常规观察与详情可以精简，事件和比较关系保持完整，新增工具也容易接入。
2. **最小字段白名单。** 只逐个保护 before / after、hp_loss、pile 等路径，事件还可再省少量字符，但增加事件类型或引用结构时容易漏登记。
3. **所有未知数值和集合均保留。** 更保守，但大量不可读数据仍然占位，且许多字段同时表达不适用和未知，难以一致分类，不能充分达到本次精简目的。

## 接入约束与验证计划

- 提供一个公共输出预设入口与一个集中处理保留规则的函数；default / full 属于输出控制参数，不转发给原生动作。
- 过滤发生在完整原生结果验证、动作权限处理、现有摘要或卡牌 / 遗物 / 地图筛选之后，不能在序列化全局启用忽略 null。
- 统一 schema 组合须保留必需参数、未知参数拒绝、deck 排序依赖等约束；`inspect_targets` 的 oneOf 分支同样必须接纳 preset，不能只修改最外层 properties。复制共享 schema，避免影响截图等工具。
- 保留现有参数错误、原生错误、部分 errors、超时与动作令牌规则；default 不得把验证失败隐藏为较短的成功响应，也不能造成动作被重复发送。
- default / full 不改变原生页面、筛选范围、游戏状态或暴露的信息来源；实际 UI 操作仍由各工具原有参数决定。
- 必须保留占卜 ImagePayload 的图片，确保 default 和 full 均带原有 PNG，actions_only 仍不带图；MCP 文本 JSON 与 structuredContent 使用同一结果。
- 后续验证覆盖 42 个工具的 schema 与分派、省略 / 显式 default 等价、full 保真、已有预设兼容、详情筛选、全部三类例外、空容器、0 / false、未知身份、图片、错误和权限处理。
- 选择、药水、充能球、遗物、事件、地图、结果页使用已有可定位的实测证据与对应回归场景；实现后补足代表性实际 MCP 调用验证，不以本次静态审查替代游戏验证。
- 当前审查不需要改变原生 schema 或 Mod 的行为。实现时按实际变更决定版本更新，不因 Python 输出投影而虚构原生协议变化。

## 待确认

是否采用推荐方案：default 只删除普通对象键中的 null，同时保留所有数组 null 元素、完整事件记录中的 null，以及已展开牌面比较两侧子树中的 null。其余值、既有预设与详情级别保持原有语义。
