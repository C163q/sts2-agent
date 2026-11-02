# get_observation：战斗主画面

> 当前状态：设计讨论中。战斗 summary 的生命、能量、空列表、手牌与顶栏规则已确认，遗物数量采用 relic_count，新增 top_bar 预设的要求与设计示例已记录；尚未修改实现。当前仅展开场景目录 01，其他场景仍待核验，get_observation 暂不核销。

总进度见[工具清单](2026-11-02-mcp-tool-review.md)，全部场景见[场景目录](2026-11-02-get-observation-review.md)。

## 范围与依据

调用为 `get_observation({"preset":"full"})`。当前只有 default、full、actions_only，没有 summary 或字段筛选参数。本文件区分当前 full 现状与下方待定的摘要设计。

源码基线 `0b81e8b`，MCP `0.48.0`、Mod `0.47.1`、schema `29`，游戏 `v0.107.1`、RitsuLib `0.6.10`。观察组装、参数与基础预设依据见[主记录](2026-11-02-get-observation-review.md#核对基线与证据)。战斗具体来源为 [CombatObservation](../../src/Sts2Agent/Observation/CombatObservation.cs)、[OrbInspection](../../src/Sts2Agent/Observation/OrbInspection.cs)、[SovereignBladeInspection](../../src/Sts2Agent/Observation/SovereignBladeInspection.cs)、[VisibleUi](../../src/Sts2Agent/Observation/VisibleUi.cs)。

这些实现读取当前显示标签、图标与已识别对象身份；可见性检查以节点、透明度、视口及祖先裁剪为依据，不等于对任意像素遮挡都能准确判断。当前规则见[信息边界](../observation.md)。本轮不修改该规则或游戏行为。

## 完整样本

每份文件都是完整玩法 JSON，没有省略数组、字段或空值；测试夹具准备的资源及牌组不能视为正常开局配置。输出仍使用英语游戏名称，正文说明使用中文。

| 样本 | 主要内容 | 来源 |
| --- | --- | --- |
| [combat.full.json](2026-11-02-get-observation-examples/combat.full.json) | 铁甲战士，三张手牌、三个敌人、空药水槽、普通与蜡质遗物 | 前一轮真实 MCP 样本，原始证据见主记录 |
| [orbs.full.json](2026-11-02-get-observation-examples/orbs.full.json) | 故障机器人，闪电 / 冰霜 / 黑暗 / 等离子球及空槽 | 前一轮真实 MCP 样本，原始证据见主记录 |
| [osty.full.json](2026-11-02-get-observation-examples/osty.full.json) | 亡灵契约师与奥斯提，含共享格挡标记、无计数状态图标 | 本轮真实 MCP，osty 场景 evidence.json 下标 0 |
| [regent-blade.full.json](2026-11-02-get-observation-examples/regent-blade.full.json) | 储君，星星数与悬浮君王之剑 | 本轮真实 MCP，blade 场景 evidence.json 下标 0 |
| [enchantments.full.json](2026-11-02-get-observation-examples/enchantments.full.json) | 带数字、灰暗、不带数字及 Spiral 附魔与升级牌名 | 本轮真实 MCP，enchantments 场景 evidence.json 下标 1 |

本轮原始证据根目录为 `.tmp/2026-11-02-get-observation-combat/gui/`，各场景数据位于 `<场景>/verify/evidence.json`。三个旧验证脚本通过 [full_output_arguments](../../tests/game/support/verification_actions.py) 显式提交 preset:full，虽然 evidence 中 arguments 记录的是调用辅助函数前的值，不能由其 null 推断成默认预设。本轮未改写旧版样本的 melted 值。

## 玩家、敌人与友方

| 路径 | full 当前内容 | UI 对应及解释 |
| --- | --- | --- |
| `scene` | `"combat"` | 当前仍处于战斗；不等于轮到玩家操作 |
| `screen.status` | 主画面通常为 `"visible"` | 可见不保证可出牌；交互仍依按钮与 available_actions 判断 |
| `turn` | 数字或 null | 结束回合按钮当前可读的回合号，不读取隐藏回合模型补值 |
| `player.character` | 如 IRONCLAD、DEFECT、REGENT、NECROBINDER | 当前可见角色身份 |
| `player.hp/max_hp/hp_display/block` | 当前生命、最大生命、显示形式与格挡 | 数值来自角色生命条；dead / infinite / hidden / unknown 不补出隐藏数字。生命条正常可读且无格挡图标时 block 为 0 |
| `player.energy/max_energy/stars` | 可见能量分子 / 分母、星星数 | stars:null 表示当前没有可读星星数字，不能当作 0 |
| `player.powers` | `{name, amount}` 数组或 null | 已显示状态图标及可读计数；没有计数标签时 amount:null，不自动返回说明正文 |
| `player.hand` | 按当前显示顺序排列的手牌，或 null | 牌的具体字段见下节；可读空手牌为 [] |
| `player.draw_count/discard_count/exhaust_count` | 数字或 null | 牌堆按钮当前显示的数量，0 与没有可读标签不同；不包含牌堆内容或抽取顺序 |
| `player.orb_slots` | 球对象 / 空槽的有序数组，或 null | 详见充能球说明 |
| `player.sovereign_blades` | 可见悬浮剑的 `{id, name}` 数组 | 只给身份，不给基础观察中尚未展开的伤害、铸造说明等；不是额外战斗单位 |
| `enemies` | `{id,name,hp,max_hp,hp_display,block,powers,intents}` 数组，或 null | 可见敌人从左到右；包括仍在显示的移除动画对象，不能据其存在直接断定仍能攻击 |
| `allies` | `{id,name,hp,max_hp,hp_display,block,powers}` 数组，或 null | 可见友方召唤物从左到右，奥斯提在这里，不在 enemies |
| `allies[].block_shared_with` | 适用时为 `"player"` | 该生命条实际显示的是玩家同一份格挡，不能重复相加；不适用时这个键本来就不存在，full 不会补一个 null |

### 普通手牌与可选字段

普通手牌的键为 `id/name/type/rarity/visual_card_pool/energy_cost/star_cost/unplayable_markers/outline`。基础观察不附 `description` 或 `hover_tips`，full 也不例外。

- `id` 是卡牌实例的稳定定位 ID，同名副本各自不同；不是数组下标，也不编码抽牌顺序。
- `name` 保留可见升级后缀；`type/rarity/visual_card_pool` 是已识别卡牌的固有身份属性，其中 visual_card_pool 表示卡面所属池，不保证等于当前角色。
- `energy_cost/star_cost` 是字符串或 null，因此可保留 X 等牌面写法；显示的当前费用不等于卡牌永久基础费用。
- 非默认费用颜色存在时另有 `energy_cost_color/star_cost_color`，取值 red、green、blue 或 other；默认颜色不输出该键，不输出 null。
- `unplayable_markers` 只记录 energy / star 等当前资源不足图标；`outline` 为 none / cyan / gold / red / other。它们是画面标记，不能替代具体卡牌的合法性判断。
- 可见附魔另有 `enchantment:{name,dimmed,amount?}`。amount 仅在牌上标签确实显示数字时存在；dimmed 对应图标灰暗，不应擅自解释为某种具体机制。没有可见附魔时整个键不存在；不能将缺失 amount 当作 0 或 1。

### 充能球、奥斯提与君王之剑

- 充能球数组按原生激发队列排列，首项为最先激发的槽位，不按球在屏幕上的横坐标排序。`orb_slots:null` 表示当前不可完整读取，`[]` 表示没有槽位，数组项 null 表示已确认空槽。
- 非空球包含 name、passive、evoke。后两个数字只取当前显示标签；例如当前样本闪电为 passive:3、evoke:null，黑暗为 passive:6、evoke:6，等离子两者为 null。不根据机制知识补出未显示数值。悬停详情由 inspect_combatants 提供。
- 奥斯提的状态图标也只给名称和可见数字；其主动攻击或死亡来源属于动作 transition，不由本次静态观察回放。身体仍在但生命数字隐藏时，hp/max_hp 保持 null，不能补成 0。
- 君王之剑的 id 与绑定卡牌实例相同；悬浮对象在绕行时按稳定 ID 排列，避免公转造成列表反复重排。其悬停卡牌预览属于 inspect_combatants，基础观察只给当前可见身份。

### 敌人意图

`intents` 是当前显示意图的 `{category,value}` 数组；value 为标签字符串或 null，例如数字或多段攻击标签。category 来自实际渲染的意图图标，不来自怪物下一招模型。

当前识别 attack、card_debuff、death_blow、debuff、buff、defend、escape、heal、hidden、sleep、status、stun、summon、unknown；未识别的可见图标用 unrecognized，图标本身不可读时 category 可以为 null。意图容器不可见时 intents:null，可见但没有可读意图时可为 []。

基础观察不返回意图悬停正文、偷牌身份、逃脱倒计时说明或下一招计划；详情由 inspect_combatants 提供。`notes.enemy_attack_intents` 在至少一项可读敌人意图存在时附加，说明攻击意图已经包含当前预览修正，不应重复计算；这不是新增敌人状态，也不保证等于实际扣血量。

## 顶栏、按钮及上下文

| 路径 | full 当前内容 | 说明 |
| --- | --- | --- |
| `top_bar.hp/max_hp` | 顶栏生命数字 | 与 player 生命条独立采样，不能假定永远可读或永远一致；动画期间可能不同 |
| `top_bar.gold/floor/ascension/deck_count` | 当前显示数字或 null | 分别为金币、总楼层、进阶等级、牌组数量；deck_count 不是手牌和战斗各牌堆数量之和 |
| `top_bar.room_icon/bosses` | 当前房间图标与可见首领名称 | 房间图标用资源文件名；bosses 内未知但已显示的图标保留 null 槽位，不补未显示首领 |
| `top_bar.potion_slots` | 按腰带位置排列的 `{name}` 或 null | 数组项 null 是空槽；整个字段 null 是不可读。适用时药水对象还会带 bouncing；商店特定提示不属于本轮战斗主画面 |
| `top_bar.relics` | 按显示顺序排列的 `{name,counter,melted}`，或 null | counter 只取图标上的数字；melted 对蜡质为 false / true，对非蜡质或不可读为 null。没有正文 |
| `top_bar.map_visible/deck_visible/settings_visible` | 布尔值 | 入口是否在画面中可见，不等于该按钮已经启用或对应工具可执行 |
| `buttons.end_turn` | `{text,enabled}` 或 null | 当前显示按钮文字与启用状态；可能显示结束回合或取消结束回合文字，不只有固定的 End Turn |
| `available_actions` | 当前可用工具名称数组 | 不含本工具、截图与测试入口，不带参数；列出 play_card 或 inspect_targets 不保证任意卡牌或目标合法 |

主画面没有覆盖页时，full 仍保留 map、selection、rewards、rest_site、treasure、shop、ancient、event、divination、confirmation、epilogue、run_result 的实际空值。某些过渡或组合状态可能存在对象，不能把当前样本里的 null 当成永久规则。

本工具没有 action transition、stop_reason、独立 player_turn 字段、当前抽牌顺序、普通手牌正文或所有图标悬停正文。更详细的信息应按现有接口读取，不能在设计摘要时把这些内容当作 full 已有字段。

## 战斗 summary 已确认规则（未实现）

以 default 的内容及空值语义为基础生成摘要。以下为已确认的战斗规则，不是当前工具已有输出；其他场景的 summary 行为尚未决定。

| 内容 | 规则 | 源码核对及边界 |
| --- | --- | --- |
| 生命 | 合并为 health，正常如 70/80，无限为 ∞，hidden 显式 null | 玩家、敌人、友方使用同一规则；保留 dead / unknown 的可区分表示，不能把死亡当作隐藏或补出数值 0 |
| 能量 | 合并为 energy，如 3/3，移除独立 max_energy | 完整可读时为分数字符串；任一数字不可读时不拼接假值，按普通不可读字段处理 |
| 空列表 | powers、orb_slots、sovereign_blades 为 [] 时省略 | powers 对玩家、敌人与友方统一处理。orb_slots:[null,null,null] 表示三个已确认空槽，数组非空，必须保留位置与数量 |
| 手牌 | 沿用 inspect_hand.summary 的牌字段 | 直接复用共享 card_summary：id、name、type、energy_cost、可见 star_cost、特殊费用颜色、unplayable_markers、outline、可见 enchantment；移除 rarity 与 visual_card_pool，不添加正文 |
| 顶栏 | 仅 gold、potion_slots、deck_count、relic_count，不返回 relics | relic_count 表示当前持有遗物数量，不按图标是否位于视口内截断。统一使用单数名词，与 deck_count、draw_count 等计数字段一致。不可读时不能生成 0 |

未提及的字段暂以 default 为基础保留；例如 block、stars、牌堆计数、敌人意图、友方共享格挡标记、buttons、available_actions、适用 notes。保留它们不代表后续不能继续精简，只避免在本次草案之外自行删字段。

### 合并生命的映射

| 当前显示 | 摘要值 |
| --- | --- |
| numeric，hp:70、max_hp:80 | `"health":"70/80"` |
| infinite | `"health":"∞"` |
| dead | `"health":"dead"` |
| hidden | `"health":null`，作为本摘要明确保留的空值例外 |
| unknown | `"health":"unknown"`，表示已有显示但当前无法识别其格式 |

格式化应使用完整验证后的显示状态，不能先丢失判断所需字段，再按默认数字拼接；显式 health:null 不应被后续普通空值过滤删除。

### 遗物清单与计数口径

- 取消本次涉及的遗物清单按视口位置剔除条目的条件；以原生遗物栏登记的持有条目计数，不能只对旧版 OnScreen 过滤后的数组求长度。名称采用 relic_count，不采用 relics_count，也不表示可见条目数量。
- 原生 NRelicInventory 使用 FlowContainer 自动换行；本设计不以屏幕矩形位置作为持有遗物是否存在的依据。核对对象为游戏 v0.107.1 的 `MegaCrit.Sts2.Core.Nodes.Relics.NRelicInventory`，本地反编译证据 `.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Relics.NRelicInventory.decompiled.cs` 的 RelicNodes、Initialize、Add、Remove；当前过滤在 CombatObservation.TopBar 与 RelicInspection.VisibleHolders。
- 保留整个顶栏 / 遗物栏不可读、显式隐藏、透明、无有效图标等真实显示状态的边界；不把不可读当作没有遗物，不补未展示的未来获取结果。列表与总数的实现须区分“持有条目数量”和“当前可展开的图标详情”，不能以悬停条目筛选替代总数。
- 实施时核对 inspect_relics 的清单筛选，移除对应的屏幕位置限制，保持其正常可悬停等条件；计数不能依赖 inspect_relics 是否能展开某个禁用条目。其他对象的视口过滤与 transition 的实际可见事件采集不因本项改为全局跳过。

### 新增 preset:top_bar（未实现）

基于现有 actions_only 的 scene、screen、available_actions，以及有待处理选择时的 selection.type/status，再加入 top_bar。正确名称为 actions_only，不新增 action_only 别名。

- top_bar 保留 default 中本来提供的所有顶栏字段，移除遗物明细 relics，加入 relic_count；不套用战斗 summary 对顶栏的四字段限制，也不把顶栏 hp/max_hp 改成战斗单位的 health。
- 不附 player、enemies、allies、turn、buttons、房间正文、notes 或占卜图片；上下文范围与 actions_only 一致。有选择时只提供原有 type/status，不附候选与按钮。
- 保留数组中的空槽；顶栏不可读时按 default 省略，不伪造空顶栏或零数量。错误返回与动作许可刷新规则沿用其他观察预设。
- 适用于当前能够读取顶栏的场景，不改变 UI；各场景的 summary 仍单独核验。无需专用调用顺序，读取信息不足时才选择此预设或其他查看工具。
- 预设提示词保持简洁，候选英文：`top_bar adds top-bar values and relic_count to actions_only; use inspect_relics for relic details.` 不加入固定刷新频率或必须先观察的要求。

### 设计示例

[战斗 summary 示例](2026-11-02-get-observation-examples/combat.summary-design.json)与[top_bar 示例](2026-11-02-get-observation-examples/combat.top-bar-design.json)由既有 combat.full.json 按以上设计转换；是可审阅的设计样例，不是当前 MCP 已实现或实测的新预设输出。样例使用同一测试画面的两件遗物、三个空药水槽，未编造当前游戏数值。

### 当前 inspect_hand.summary 的实际样式

以下为既有真实 MCP 样本中三张牌的完整摘要片段；原始调用位于 `.tmp/2026-11-02-get-observation-combat/gui/enchantments/verify/evidence.json` 数组下标 4，参数 preset:summary。省略了该手牌列表的其他三张牌，未省略这三张牌各自的字段。

```json
{
  "hand": [
    {
      "id": 5,
      "name": "Strike",
      "type": "Attack",
      "energy_cost": "1",
      "unplayable_markers": [],
      "outline": "cyan",
      "enchantment": {"name": "Sharp", "dimmed": false, "amount": 3}
    },
    {
      "id": 7,
      "name": "Strike",
      "type": "Attack",
      "energy_cost": "1",
      "unplayable_markers": [],
      "outline": "cyan",
      "enchantment": {"name": "Clone", "dimmed": false}
    },
    {
      "id": 8,
      "name": "Strike",
      "type": "Attack",
      "energy_cost": "1",
      "unplayable_markers": [],
      "outline": "cyan"
    }
  ]
}
```

附魔现状：CombatObservation.Card 只有在已识别卡牌的附魔标签与匹配图标可见时才加入 enchantment，HandInspection.Card 在这个结果上增加正文及提示。因此无可见附魔时 full 同样缺少该键；不是 full 过滤了 enchantment:null，而是原生本来未生成此字段。只有 amount 标签未显示时，附魔对象仍可存在但 amount 键不存在。当前输出 shape 的 enchantment 本身不接受 null。

### 待继续讨论

- 其他保留字段是否继续精简，以及 summary 在战斗覆盖页和其他场景中的行为。
- 实施尚未开始；上述已确认规则作为后续实现依据，不在后续对话中重复询问已确认项目。此次仅更新设计与示例，没有新增游戏运行或修改工具行为。

## 本轮验证与未覆盖项

- 复用 3 个既有 GUI 场景，全部通过，共 29 次真实 MCP 调用；含奥斯提动作与共享格挡、君王之剑预览与攻击、基础观察附魔与专门手牌查看的一致性检查。证据中的原生检查和前后快照另计，不混入 MCP 调用数。
- 报告：`.tmp/2026-11-02-get-observation-combat/gui/report.json`。同一隔离进程 PID 65881 完成 3 个独立测试局并退出，报告有 shutdown_seconds；未修改正式游戏安装或存档。
- 实测 DLL SHA-256 为 `607c3aab3c985d3a231fe17b38ada12082e615320f7c0831937523f662eca08e`，与当前构建及上一轮 full 样本所用 DLL 一致。
- 新增的 3 份完整 JSON 逐对象等同于对应实测返回，并通过当前 observation_details 校验；既有 2 份战斗样本沿用其原始实测证据。文档链接及围栏另作检查。
- 本轮未新采集全部意图图标、全部费用颜色、X / 星星不足、死亡 / 无限生命、所有 power 及动画中间帧；这些分支的说明来自当前源码，不能视作本轮逐个游戏实测通过。需要进一步讨论其中某个字段时，再针对性补充完整样本及 UI 证据。
- 工具逻辑、版本、参数和持续维护的接口契约均未改变；本轮交付为战斗现状材料，等待用户提出字段或参数建议。
