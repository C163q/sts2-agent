# 共享卡牌格式覆盖与例外核验

> 当前状态：已完成字段清点和悬浮君王之剑的当前版本实测；已确认 face 不含正文、展开牌面 full/default 增加悬停解释，以及牌组／牌堆移除 detail_level、改用 preset。尚未实施。本文逐项列出共享牌面入口的范围及其外部字段，供核验后进入实现；没有新增临时卡牌模式。主记录见[inspect_hand 核验](2026-11-03-inspect-hand-review.md)。

## 已确认的内部规则

| 内部模式 | 正文 description | 悬停解释 | 空值 |
| --- | --- | --- | --- |
| `face_full` | 不返回，包括 description:null | 不返回 | 保留其他已有 null |
| `face_default` | 不返回 | 不返回 | 按统一 default 规则过滤 |
| `full` | 返回，未知／不可读时为 null | 返回允许查看的解释 | 保留 null |
| `default` | 同 full | 同 full | 按统一 default 规则过滤 |
| `summary` | 不返回 | 不返回 | 使用既有共享摘要及普通空值规则 |

普通完整卡牌统一使用这些模式。半隐藏手牌和商店基础观察采用 face；已展开候选、比较及结算牌采用 full/default，增加此前未提供的悬停解释。summary 保持现有共用卡牌摘要，加经 UI 核实的 Affliction；不增加 text 等中间模式。

这是信息范围的明确调整：当前部分牌面只有正文、没有解释，不能仅通过把已有输出改名为 full 声称完成迁移。原生采样、Python 类型校验和最后的输出投影均需接入，尤其不能让完整读取产生的解释在旧白名单中被丢弃。

get_observation 和 inspect_selection 已有 full/default/summary。inspect_run_result 目前只有 full/default，本轮不额外给它新增公开 summary；其卡牌仍接入相应的内部格式。工具 preset 与其内部牌面模式由场景明确映射，face 内部永不按情况添加正文。

## 全部标准牌面入口

以下路径以玩法 JSON 根为起点。返回基础观察的动作及页面工具也沿用同一映射，不能只修改 get_observation 而漏掉动作回执。卡牌存在、身份是否可见、牌面是否展开等仍由原生页面判断；被覆盖或未揭示的数据不得由格式化补出。

| 工具／场景 | 卡牌对象路径 | full/default 的内部模式及迁移要求 |
| --- | --- | --- |
| 基础观察的当前手牌 | `player.hand[]` | face_full／face_default；summary 用共享摘要 |
| 基础观察的手牌选择候选及未展开卡包 | `selection.cards[]`、`selection.bundles[].cards[]` | 当前仍半隐藏的牌用 face；已展开的候选用 full/default。调用位置先确定展开状态，模式本身固定 |
| 基础观察的三选一、奖励、网格、牌组／牌堆选择等展开候选 | `selection.cards[]` | full/default；保留正文并新增对应悬停解释 |
| 基础观察的升级比较 | `selection.upgrade_preview.before/after`、`selection.upgrade_previews[].before/after` | full/default；增加解释，保持比较两侧身份和空值 |
| 基础观察的附魔／变牌比较 | `selection.enchant_previews[].before/after`、`selection.transform_previews[].before/after` | full/default；增加解释；未知随机结果 after:null 仍由比较容器保留 |
| 基础观察的结算／解锁／本局详情卡牌 | `run_result.cards[]` | full/default；增加解释；保持 card:N ID |
| 基础观察的商店商品 | `shop.items[].card`，仅 kind:card | face_full／face_default，summary 仍用共享摘要；价格及购买 ID 留在外层 |
| inspect_hand | `hand[]` | full/default/summary；保留当前手牌整数 ID |
| inspect_selection 的候选及卡包 | `selection.cards[]`、`selection.bundles[].cards[]` | full/default/summary；已有正文及解释继续返回 |
| inspect_selection 的所有比较牌 | 上述四类 upgrade/enchant/transform 比较路径 | full/default/summary；当前 Python 比较结构会丢掉逐牌解释，迁移需补齐 |
| inspect_deck | `deck[]` | full/default/summary；移除旧 detail_level；保留 deck:N ID、排序及升级预览 |
| inspect_pile | `cards[]`，status:opened | full/default/summary；移除旧 detail_level；保留 pile:N ID 及原生展示顺序 |
| inspect_shop | `shop.items[].card`，仅 kind:card | full/default；以后新增 summary 时也复用共享摘要，不在本轮提前新增其公开预设 |
| inspect_run_result | `run_result.cards[]` | full/default；保持 card:N ID；不自动增加其他结算工具参数 |

这些标准对象的全部当前顶层字段均归共享入口：`id/name/type/rarity/visual_card_pool/energy_cost/star_cost/energy_cost_color/star_cost_color/unplayable_markers/outline/enchantment/description/hover_tips`；已有附魔对象的 `name/amount/dimmed` 也统一读取与投影，Affliction 新增 `affliction.name`。UI 不存在的外观属性不能凭模型补出；身份 ID 仍允许各工具现有的整数、字符串或外层商品 ID 表示。

手牌及部分专项详情把逐牌 hover_tips 合并到顶层，这属于容器处理，不等于未接入 full。新增解释应保持与卡牌、比较侧别的关联；before/after 共用一个原牌 ID，不能只按该 ID 合并后丢掉侧别。默认优先保留既有共享提示结构；新增的比较解释可在对应 before/after 卡牌中承载。

基础观察的地图、牌组／牌堆覆盖页目前没有实际卡牌主体，仍是已记录的独立 TODO；不能把“没有返回该对象”冒充另一个卡牌格式例外。此次参数迁移不自行标记该 TODO 完成。

## 不属于牌面预设的全部结构化卡牌信息

以下是本次按当前原生生产点和 Python 公开结构核对的例外清单。它们有明确的信息职责，不通过 full/face/summary 生成卡面；可共用身份名称、正文格式化或引用构造函数，避免散落重复规则。

| 类别与场景 | 精确路径／字段 | 保留原因与处理入口 |
| --- | --- | --- |
| 悬浮君王之剑的外观身份 | 基础观察和 inspect_combatants 的 `player.sovereign_blades[].id/name` | 玩家此时看到悬浮物体；只提供身份，详情通过关联悬停解释提供 |
| 指定手牌的目标查询 | inspect_targets 的 `card.id/name` | 标明本次查询的是哪张牌；playable、target_type、requires_target、targets、reason 属于动作合法性，不是牌面字段 |
| 动作中的卡牌身份 | 所有动作回执的 `transition.events[].card.id/name` | 播报打出、抽到、弃置、消耗、获得、移除、升级、降级、附魔或永久数值变化，不能借回放附送整张卡牌当前状态 |
| 动作效果来源 | `transition.events[].source.kind/name`，仅 kind:card | 只有来源名称，不保证存在当前可操作 ID；例如伤害由哪张牌产生 |
| 悬浮剑的卡牌悬停正文 | inspect_combatants 的 `hover_tips[].title/description/sources`，sources 包含 player.sovereign_blades.N | 与生物、能力、意图和充能球共用提示容器；不凭悬浮物体生成费用等字段 |
| 其他卡牌预览悬停文本 | 各专项详情的 `hover_tips[].title/description`，或嵌套 hover_tips | CardHoverTip 被转成预览卡名称与正文；可能还有 card_ids、sources、slot_indices、relic_indices 等关联字段。没有候选 ID，不补完整卡面 |
| 选牌界面提供的附魔说明 | get_observation 和 inspect_selection 的 `selection.enchantment.title/description` | 这是本次将施加的附魔说明，区别于 `selection.cards[].enchantment.name/amount/dimmed`；不随卡牌 summary 删除正文 |
| 选择和比较的身份／状态元数据 | `selection.selected_ids[]`、`selection.bundles[].id`、`selection.transform_previews[].random`、比较 before/after 对象本身的 null | 由选择容器维护，里面非空的卡牌对象才交共享牌面入口 |
| 共享解释及诊断的 ID 关联 | `hover_tips[].card_ids[]`、筛选参数 card_ids、`errors[].card_ids[]` | 引用与错误定位，不是新的卡牌对象；筛选、去重、顺序、比较侧别由容器维护 |

卡牌名出现在事件选项、奖励文字、先古之民对白、提示正文或结算 texts 中时，仍是原生 UI 文本，不解析并补成卡牌对象。当前没有单独公开的“永久变化前后卡面数值”结构：card_stats_changed、card_energy_cost_changed、card_enchantment_changed 事件只包含 card 身份与 pile，校验器明确拒绝额外的 before/after 牌值；不能误列为尚未归类的牌面格式。

### 悬浮剑的当前真实 JSON

基础观察中 `player.sovereign_blades` 的完整值为：

```json
[
  {
    "id": 5,
    "name": "Sovereign Blade"
  }
]
```

inspect_combatants 同样返回这个身份列表，并在 hover_tips 中增加下面这条完整关联提示：

```json
{
  "title": "Sovereign Blade",
  "description": "Retain.\nDeal 15 damage.",
  "sources": ["player.sovereign_blades.0"]
}
```

经过本次测试局正常打牌锻造后，说明变为 `Retain.\nDeal 31 damage.`，身份保持相同。随后打出该剑的 damage.source 为 `{"kind":"card","name":"Sovereign Blade"}`，actor 是玩家 The Regent；不是悬浮剑作为独立生物攻击。

完整真实响应分别为：[基础观察](2026-11-03-card-format-examples/blade-observation.full.json)、[初始生物详情](2026-11-03-card-format-examples/blade-combatants.full.json)、[锻造后详情](2026-11-03-card-format-examples/blade-forged-combatants.full.json)、[打出剑的回执](2026-11-03-card-format-examples/blade-play.full.json)。上面仅摘出相关字段，不将字段摘录冒充整个响应。

### 其他例外的真实字段示例

inspect_targets 中的卡牌引用，来自[完整目标查询](2026-11-03-card-format-examples/target-reference.full.json)：

```json
{"id":5,"name":"Strike"}
```

动作中的卡牌引用，来自上述打出剑回执的 card_played 事件：

```json
{
  "card": {"id":5,"name":"Sovereign Blade"},
  "autoplay": false,
  "source": null,
  "target": {"id":1,"kind":"enemy","name":"Leaf Slime (S)"},
  "type": "card_played",
  "sequence": 2
}
```

CardHoverTip 文本预览，来自[十张手牌 full](2026-11-03-inspect-hand-examples/ten-cards.full.json)中的一条完整提示；关联的是生成它的 Blade Dance，而不是可操作的 Shiv 实例：

```json
{
  "title":"Shiv",
  "description":"Deal 4 damage.\nExhaust.",
  "card_ids":[5]
}
```

选牌提供的附魔说明，来自历史真实[附魔候选](2026-11-02-get-observation-selection-examples/enchant-candidates.full.json)，并已用当前 SELECTION_OUTPUT 与 DeckEnchantSelection 核对字段结构：

```json
{
  "title":"Sharp",
  "description":"Increases damage on this card by 2."
}
```

选择身份元数据的实际例子见[已选手牌升级](2026-11-02-get-observation-selection-examples/hand-upgrade-selected.full.json)中的 selected_ids:[7] 和[卡包候选](2026-11-02-get-observation-selection-examples/bundle-candidates.full.json)中的 id:bundle:0。这些历史样本保留原基线，不表示本轮重新执行该场景；不改写历史文件。

## 牌组／牌堆参数迁移范围

本轮已明确纳入参数与卡牌信息的同步迁移，取消此前“先保留旧摘要，等专门工具核验”的处理：

- MCP inspect_deck 和 inspect_pile 移除 detail_level，接受 preset:full/default/summary，默认 default。旧 detail_level 请求应返回 invalid_request，不保留另一套摘要别名。
- full/default 的卡牌接入共用 full/default；summary 接入共用卡牌摘要，不再保留旧七字段摘要。full 与 default 的卡牌正文和解释范围相同，只由统一空值规则区分。
- 不再返回 detail_level，也不额外要求返回 preset 回显；沿用其他查看工具的返回风格。
- inspect_deck 的 view_upgrades、sort_by、descending，及 inspect_pile 的 pile 与 opened/empty/unavailable 状态保持。ID 和原生排序／抽牌顺序边界不变。
- 同步清理文件协议／CLI 中的旧公开字段和参数；原生采样与 MCP 输出投影保持分层，原生完整采样不再由 detail_level 切成两套数据。CLI 若做 preset 投影，复用共用 Python 实现。
- Python 的通用 preset 包装、牌组／牌堆校验、共享提示合并、原生 DeckOptions/PileOptions、相关验证脚本及现行文档需要一起迁移，不能只改 MCP schema 后继续按默认旧 summary 读取原生数据。

变化包括：省略参数时默认会得到带正文／解释的 default；显式 summary 会省略稀有度／卡池并保留经采样核实的外观。它们是已要求的行为调整，不再作为“无损重构”承诺保持旧输出。

## 证据与实施次序

- 核验基线：提交 `4fa3a9f`，Mod 0.50.0、MCP 0.51.0；游戏 Linux v0.107.1 release build 59260271，RitsuLib 0.6.10 的对应兼容运行时。当前兼容版本统一见[README](../../README.md#当前版本与前提)。
- 本轮悬浮剑测试的 DLL 与当前构建相同，SHA-256 为 `eedee2ff5b7ba98325f8b42bf03fe19767094ba8fa0b807864820ee59ca80e30`。一个隔离游戏进程执行已有 verify_companions 的 blade 场景，通过正常卡牌动作检查锻造和伤害归属，测试局清理通过，PID 35939 已关闭。
- 完整证据在 `.tmp/2026-11-03-card-format-coverage/blade-gui/`；公开 JSON 的来源、数组下标及参数见 [manifest](2026-11-03-card-format-examples/manifest.json)。目标查询复用前轮同一原生 DLL 的真实样本，明确标记来源。
- 核对生产点：CombatObservation、HandInspection、SelectionInspection、BrowsedCard、DeckInspection、PileInspection、ShopInspection、RunResultInspection、SovereignBladeInspection、CombatantInspection、TargetInspection、HoverTipText、EnglishEventText，以及 TurnJournal、RunInventoryJournal、PermanentCardCapture；对应核对 game_output、selection_details、run_ending_details、deck_details、pile_details、transition_details、player_output 等 Python 白名单和投影。
- 实施仍先处理 Affliction、附魔空值和直接相关的小范围重构；随后统一普通牌面、增加已确认的展开牌解释，迁移牌组／牌堆 preset，并接入手牌资源。此处不宣称已完成实现，不核销尚未完整核验的工具。
