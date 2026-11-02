# get_observation 选牌界面核验

> 当前状态：实施与验证中。完整候选、共用卡牌摘要、网格已有附魔及滚动节点刷新已实现，正在执行隔离 GUI 回归；原有 39 份 full 文件保留为 e728b7e 的历史基线。其他房间摘要仍待各自核验，get_observation 整体尚未核销。

范围对应[场景目录](2026-11-02-get-observation-review.md)的 02、03、04 组，包括候选、已选、确认预览、查看升级、眼睛切换及覆盖页。这里的“选牌”包含 `view_cards` 结果确认页；普通牌组／牌堆浏览、商店商品卡、尚未打开的奖励行、结算解锁卡不属于待处理卡牌选择。

## 基线与证据

- 核对日期：2026-11-02；项目基线 `d835095`，MCP `0.49.0`、Mod `0.48.0`、schema `30`。
- 游戏 Linux `v0.107.1`、release `59260271`，RitsuLib `0.6.10`。程序集为游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 隔离测试 Mod SHA-256：`1a01c03463397642ae2f641f7f7c280dd64cdfce18fc7cecff8c4a1b709f87eb`。夹具使用独立测试局准备牌组、数值和房间；这些数值不代表正常开局配置。
- 游戏源码证据：上述程序集的 `CardSelectCmd`、`NPlayerHand`、`NCardGridSelectionScreen` 及下表的页面类型；预览另核对 `NUpgradePreview`、`NEnchantPreview`、`NTransformPreview`。反编译文件仅存于 `.tmp/2026-11-02-observation-selections-review/`，不纳入 Git。
- 项目实现：[CardSelection](../../src/Sts2Agent/Actions/CardSelection.cs)、[SelectionInspection](../../src/Sts2Agent/Observation/SelectionInspection.cs)、[SelectionActions](../../src/Sts2Agent/Actions/SelectionActions.cs)、[观察组装](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[观察投影](../../src/sts2_mcp/output/observation_presets.py)、[选择校验](../../src/sts2_mcp/output/game_output.py)。现行接口见[选牌说明](../development/card-selection.md)。

## 已识别的界面

| selection.type | 原生页面／入口 | 候选与确认方式 | 需要单独核验的变化 |
| --- | --- | --- | --- |
| `choose_one` | `NChooseACardSelectionScreen`，例如 Discovery | 若干张生成牌中选一张，通常点击即提交；可选跳过以实际按钮为准 | 查看战场、覆盖与返回 |
| `reward` | `NCardRewardSelectionScreen`，卡牌奖励 | 点击选一张；替代按钮通过 `selection_option` | 跳过、佩尔之翼献祭、浮木重掷；重掷后 ID 更新 |
| `grid` | `NSimpleCardSelectScreen`，简单网格 | 按提示单选／多选，可等待确认 | 已选集合、禁用／启用确认、滚动候选 |
| `combat_pile` | `NCombatPileCardSelectScreen`，战斗牌堆选择 | 从指定战斗牌堆的原生筛选候选选择 | 原生数量限制、确认；不等同于普通牌堆浏览 |
| `deck` | `NDeckCardSelectScreen`，牌组一般选择／移除 | 从牌组选择，按原生偏好进入确认页 | 确认页使用 `cards` 显示选中原牌，没有独立 removal_preview 字段 |
| `hand` | `NPlayerHand.Mode.SimpleSelect`，弃牌／保留等 | 原生过滤后的手牌；按数量要求选择／确认 | 手牌不因 full 自动展开正文；允许零张以实际 min_select 为准 |
| `hand_upgrade` | `NPlayerHand.Mode.UpgradeSelect`，例如武装 | 手牌候选，选中后显示一组升级前后牌面 | 单数 `upgrade_preview`、取消／改选、眼睛与覆盖；唯一候选可能由游戏直接处理，无选择页 |
| `deck_upgrade` | `NDeckUpgradeSelectScreen`，火堆／事件升级 | 候选网格，选中后显示升级比较 | 查看升级复选框；单牌前后比较，多牌确认可能只展示升级后牌面 |
| `deck_enchant` | `NDeckEnchantSelectScreen`，附魔 | 候选网格及选择级附魔说明，选中后确认 | `enchantment` 与卡牌已有附魔含义不同；单牌模拟附魔，多牌确认按原生展示原牌 |
| `deck_transform` | `NDeckTransformSelectScreen`，变牌 | 候选网格，选中后显示变牌比较 | 查看升级；随机结果 `after:null, random:true`，不把轮播插图当成已经确定的结果 |
| `bundle` | `NChooseABundleSelectionScreen`，牌包选择 | 通过 `bundle:N` 选择整包，再确认 | 包选择页使用 `bundles`；预览页选中整包内容移入 `cards`，`bundles:[]` |
| `view_cards` | `NSimpleCardsViewScreen`，例如潘多拉魔盒结果 | 结果确认，min_select／max_select 都为 0 | 可查看升级、确认；卡牌可阅读，不能用 select_card 当候选选择 |
| `unsupported` | 未被识别的 `NCardGridSelectionScreen` 子类或手牌模式 | 人工输入边界，不提供可选牌 | 不伪造成功候选；本轮不以支持的页面冒充未知选择实测 |

场景表示底层房间：火堆升级是 `scene:rest_site`、先古之民牌包是 `scene:ancient`；选牌不会统一变成 `scene:selection`。`screen.status:covered` 可能只表示战场／房间被选择覆盖，此时 `selection.status:visible` 仍可正常选择。

## full 的读取范围与字段

调用参数统一为 `{"preset":"full"}`。以下保留基线 `e728b7e` 的设计依据；实施后的当前契约见开发指南及文末实施结果。完整返回样本另列，不能把 inspect_selection 的返回改名作为本工具示例。

- 公共选择字段：`type/status/prompt/min_select/max_select/selected_ids/cards/options/can_view_battlefield/can_view_upgrades/view_upgrades`。按钮保留 `id/text/enabled`，其含义以本次文字为准。
- 基础卡牌包含 `id/name/type/rarity/visual_card_pool/energy_cost/star_cost/unplayable_markers/outline`；特殊费用颜色与实际显示的附魔按条件增加。没有可见附魔时连 full 也不生成 `enchantment` 字段。
- 已展开的非手牌候选与比较牌可包含 `description`；full 基础观察不主动生成所有正文，也不附 inspect_selection 的悬停帮助。手牌选择仍保留静态手牌的信息范围。
- 专有字段：`hand_upgrade.upgrade_preview`；`deck_upgrade.upgrade_previews`；`deck_enchant.enchantment/enchant_previews`；`deck_transform.transform_previews`；`bundle.bundles`。它们不是每种选择都拥有的字段。
- 候选只读取当时可见卡牌节点；网格屏幕外候选由 `inspect_selection` 显式读取。已选 ID 不限于此刻可见的候选，确认预览也不是新候选。
- 已展开比较的 before／after 使用原牌 ID；看不到的原牌侧可能只含 `id/name:null/description:null`。随机变牌的整个 after 可以为 null。公共 default 对比较子树保留这些空值，不能补成升级前／变牌后的隐藏数据。
- `battlefield`：待处理选择仍在，但 `cards/prompt/min_select/max_select/selected_ids/view_upgrades` 为 null，按钮为空；已展开比较隐藏。战场本身按可见范围返回。
- `covered`：地图、牌组／牌堆或其他页面覆盖选择时，不提供隐藏候选或比较；返回 `notes.selection` 提醒先关闭当前查看页。强制地图是否可关闭仍以 available_actions 为准。
- `unsupported`：返回选择类型与状态，以及人工输入提示；不恢复隐藏候选。

## 摘要设计时需要区分的内容

1. **普通候选与确认页**：deck 移除确认页把选中的原牌放在 `cards`；deck_upgrade 等确认页则可能 `cards:[]`，内容转入专有 previews。不能只压缩 cards 后就声称覆盖了选牌摘要。
2. **牌包的两种布局**：未选包时 cards 为空、bundles 有内容；确认包时恰好相反。摘要必须同时处理两条路径，并保留包 ID 的整包操作语义。
3. **卡牌附魔与本次操作**：`cards[].enchantment` 是卡牌上已显示的附魔；`selection.enchantment` 是这次准备施加的附魔名称与说明。多牌附魔确认页按原生展示原牌，不替玩家预先计算附魔后数值。
4. **看不到与没有结果**：多牌升级／附魔的 before 可能保留 ID 而牌名未知；随机变牌 after 为 null。它们都不能当作空对象删除，更不能从牌组数据或动画补全。
5. **操作 ID 与升级克隆**：查看升级后，卡名／费用／正文可能变化，但候选 ID 仍指向原牌。比较两侧的相同 ID 表示同一张牌，不是重复候选。
6. **数量限制与滚动**：数量上限不等于屏幕当前可见候选总数；selected_ids 也不应随候选裁剪。实施前的 40 张牌样本中，基础观察只返回 15 张可见牌，inspect_selection 则读取全部 40 张。眼睛和覆盖页只改变可见信息，不能偷偷取消待处理选择。

## 完整 full 返回样本

下列文件均为设计阶段真实 stdio MCP 的 `get_observation({"preset":"full"})` 返回，保留整个玩法 JSON、所有原有空值、完整数组和 notes，未改名、补字段或截断。每个样本对应一张隔离游戏截图，截图及完整调用序列留在本地证据目录。这里只保存 JSON；这些选择页没有额外 MCP 图像内容。

| 场景 | 底层 scene／选择类型 | 完整 JSON（括号为证据数组下标） |
| --- | --- | --- |
| 生成牌单选 | `combat`／`choose_one` | [候选页](2026-11-02-get-observation-selection-examples/choose-one-candidates.full.json)（2）、[查看战场](2026-11-02-get-observation-selection-examples/choose-one-battlefield.full.json)（5）、[牌组覆盖](2026-11-02-get-observation-selection-examples/choose-one-deck-covered.full.json)（8）、[返回选择](2026-11-02-get-observation-selection-examples/choose-one-returned.full.json)（12）、[地图覆盖](2026-11-02-get-observation-selection-examples/choose-one-map-covered.full.json)（16） |
| 手牌保留 | `combat`／`hand` | [候选页](2026-11-02-get-observation-selection-examples/hand-candidates.full.json)（2）、[已选／确认页](2026-11-02-get-observation-selection-examples/hand-selected.full.json)（5） |
| 手牌升级 | `combat`／`hand_upgrade` | [候选页](2026-11-02-get-observation-selection-examples/hand-upgrade-candidates.full.json)（2）、[已选／确认页](2026-11-02-get-observation-selection-examples/hand-upgrade-selected.full.json)（5）、[查看战场](2026-11-02-get-observation-selection-examples/hand-upgrade-battlefield.full.json)（8）、[牌组覆盖](2026-11-02-get-observation-selection-examples/hand-upgrade-deck-covered.full.json)（11）、[返回选择](2026-11-02-get-observation-selection-examples/hand-upgrade-returned.full.json)（15）、[地图覆盖](2026-11-02-get-observation-selection-examples/hand-upgrade-map-covered.full.json)（19） |
| 网格多选 | `event`／`grid` | [候选页](2026-11-02-get-observation-selection-examples/grid-candidates.full.json)（1）、[已选／确认页](2026-11-02-get-observation-selection-examples/grid-selected.full.json)（4） |
| 战斗牌堆 | `combat`／`combat_pile` | [候选页](2026-11-02-get-observation-selection-examples/combat-pile-candidates.full.json)（1） |
| 牌组移除 | `event`／`deck` | [候选页](2026-11-02-get-observation-selection-examples/deck-candidates.full.json)（1）、[已选／确认页](2026-11-02-get-observation-selection-examples/deck-selected.full.json)（4） |
| 火堆升级 | `rest_site`／`deck_upgrade` | [候选页](2026-11-02-get-observation-selection-examples/smith-candidates.full.json)（2）、[查看升级](2026-11-02-get-observation-selection-examples/smith-upgrades.full.json)（5）、[已选／确认页](2026-11-02-get-observation-selection-examples/smith-selected.full.json)（9） |
| 多牌升级 | `event`／`deck_upgrade` | [候选页](2026-11-02-get-observation-selection-examples/upgrade-multi-candidates.full.json)（1）、[查看升级](2026-11-02-get-observation-selection-examples/upgrade-multi-upgrades.full.json)（4）、[已选／确认页](2026-11-02-get-observation-selection-examples/upgrade-multi-selected.full.json)（9） |
| 单牌附魔 | `event`／`deck_enchant` | [候选页](2026-11-02-get-observation-selection-examples/enchant-candidates.full.json)（2）、[已选／确认页](2026-11-02-get-observation-selection-examples/enchant-selected.full.json)（5） |
| 多牌附魔 | `ancient`／`deck_enchant` | [候选页](2026-11-02-get-observation-selection-examples/enchant-multi-candidates.full.json)（7）、[已选／确认页](2026-11-02-get-observation-selection-examples/enchant-multi-selected.full.json)（12） |
| 随机变牌 | `ancient`／`deck_transform` | [候选页](2026-11-02-get-observation-selection-examples/transform-candidates.full.json)（7）、[查看升级](2026-11-02-get-observation-selection-examples/transform-upgrades.full.json)（10）、[已选／确认页](2026-11-02-get-observation-selection-examples/transform-selected.full.json)（14） |
| 整包选择 | `ancient`／`bundle` | [候选页](2026-11-02-get-observation-selection-examples/bundle-candidates.full.json)（7）、[已选／确认页](2026-11-02-get-observation-selection-examples/bundle-selected.full.json)（10） |
| 结果确认 | `ancient`／`view_cards` | [候选页](2026-11-02-get-observation-selection-examples/view-cards-candidates.full.json)（7）、[查看升级](2026-11-02-get-observation-selection-examples/view-cards-upgrades.full.json)（10） |
| 献祭奖励 | `rewards`／`reward` | [候选页](2026-11-02-get-observation-selection-examples/paels-wing-candidates.full.json)（3） |
| 重掷奖励 | `rewards`／`reward` | [候选页](2026-11-02-get-observation-selection-examples/driftwood-candidates.full.json)（3）、[重掷后](2026-11-02-get-observation-selection-examples/driftwood-rerolled.full.json)（6） |
| 滚动网格 | `combat`／`grid` | [候选页](2026-11-02-get-observation-selection-examples/grid-scroll-candidates.full.json)（1） |

证据来源按上表场景定位：

- 前 13 项：`.tmp/2026-11-02-observation-selections-review/gui-complete/<case>/evidence.json`，case 依次为 `choose_one/hand/hand_upgrade/grid/combat_pile/deck/smith/upgrade_multi/enchant/enchant_multi/transform/bundle/view_cards`。
- 后 3 项：`.tmp/2026-11-02-observation-selections-review/gui-remaining/<case>/evidence.json`，case 为 `paels_wing/driftwood/grid_scroll`。
- 对应截图为同目录 `screenshots/<label>.png`，label 与文件名中的 `candidates/selected/upgrades/battlefield/deck-covered/map-covered/returned/rerolled` 对应。JSON 中名称保留工具原有英文，截图使用中文游戏 UI。
- 下标以原始 evidence 数组从 0 开始计数；精确文件／调用对应表另存本地 `samples-manifest.json`。

### 火堆已选一张牌的具体结构

以下仅摘录 [火堆确认页完整响应](2026-11-02-get-observation-selection-examples/smith-selected.full.json) 的 selection，其他字段保持在链接文件中：

```json
{
  "selection": {
    "type": "deck_upgrade",
    "status": "visible",
    "prompt": "Choose a card to Upgrade.",
    "min_select": 1,
    "max_select": 1,
    "selected_ids": [
      19
    ],
    "cards": [],
    "options": [
      {
        "id": "cancel_preview",
        "text": "Back",
        "enabled": true
      },
      {
        "id": "confirm",
        "text": "Confirm",
        "enabled": true
      }
    ],
    "can_view_battlefield": false,
    "can_view_upgrades": false,
    "view_upgrades": false,
    "upgrade_previews": [
      {
        "before": {
          "id": 19,
          "name": "Bash",
          "type": "Attack",
          "rarity": "basic",
          "visual_card_pool": "ironclad",
          "energy_cost": "2",
          "star_cost": null,
          "unplayable_markers": [],
          "outline": "none",
          "description": "Deal 8 damage.\nApply 2 Vulnerable."
        },
        "after": {
          "id": 19,
          "name": "Bash+",
          "type": "Attack",
          "rarity": "basic",
          "visual_card_pool": "ironclad",
          "energy_cost": "2",
          "star_cost": null,
          "unplayable_markers": [],
          "outline": "none",
          "description": "Deal 10 damage.\nApply 3 Vulnerable."
        }
      }
    ]
  }
}
```

此时 `cards:[]` 并非没有需要确认的牌，而是卡牌内容位于 `upgrade_previews`。`cancel_preview` 返回候选，`confirm` 才真正提交升级；before／after 的同一个 ID 指向被选择的原牌。

## 已确认的调整范围

实施前 get_observation.summary 只精简战斗资源、普通手牌和顶栏，selection 内的牌保持 default；本轮将各底层场景的选牌接入同一规则。

- 当前已打开、处于候选页的可浏览选择，get_observation 返回整个原生候选列表，不按视口和滚动位置截断。范围调整适用于 full/default/summary；预设决定返回精简度，不决定能否读取同一列表中的候选。
- 保留原生列表顺序、原牌 ID 与当前查看升级模式。手牌仍使用当前实际的手牌选择；确认页只读取该页展示的牌和比较，不重新带回背景网格。眼睛、地图或牌组隐藏选择时仍隐藏候选，不提前生成未出现的结果。
- get_observation.summary 在 default 基础上，统一精简 `selection.cards`、`bundles[].cards` 和全部 before／after 卡牌，格式与 inspect_hand.summary 共用；原有战斗摘要继续适用。保留选择提示、数量限制、全部已选 ID、按钮、包 ID、升级模式、附魔操作说明与随机结果标记。
- 共用卡牌摘要中，`unplayable_markers:[]` 省略；非空资源标记保留。字段名仍为复数 unplayable_markers，不新增别名。
- 原始结果没有 outline 时不生成该字段；没有描边的 `outline:"none"` 也统一省略，规则见下。

### 实施前卡牌摘要审查（e728b7e）

| 返回位置 | 当前空 unplayable_markers | 当前 outline:none | 实施范围 |
| --- | --- | --- | --- |
| inspect_hand.summary 的 hand | 保留 | 保留 | 共用 card_summary，统一调整 |
| inspect_selection.summary 的候选、包和比较 | 原始有该字段时保留 | 原始有该字段时保留 | 共用 card_summary，统一调整 |
| get_observation.summary 的 player.hand | 保留 | 保留 | 共用 card_summary，统一调整 |
| get_observation.summary 的 selection | 当时未精简，仍沿用 default 卡牌 | 保留 | 本轮接入同一规则 |
| inspect_deck／inspect_pile 的 detail_level:summary | 本来就没有该字段 | 本来就没有该字段 | 独立的浏览摘要，不冒充共用手牌规则；本轮不增加这些字段 |
| inspect_relics.summary | 不涉及 | 不涉及 | 仅包含遗物，不做卡牌规则调整 |

源码：[card_summary](../../src/sts2_mcp/output/card_summary.py)、[手牌](../../src/sts2_mcp/output/hand_presets.py)、[选牌](../../src/sts2_mcp/output/selection_presets.py)、[观察](../../src/sts2_mcp/output/observation_presets.py)、[浏览卡牌校验](../../src/sts2_mcp/output/deck_details.py)。当前行为已用小型调用检查复核，证据 `.tmp/2026-11-02-card-summary-audit/verification.json`；没有改生产代码或运行游戏。

### 已确认的附加精简规则

1. 共用卡牌摘要省略 `outline:"none"`，保留 cyan/gold/red/other；已有描边与资源不足标记各有意义，不合并成 can_play。省略无描边或空资源标记不能解释为“可打出”。默认费用颜色本来就不输出，无须再加一套删色规则。
2. inspect_hand／inspect_selection／inspect_relics 的 summary 也统一继承 default 的普通空值规则，减少目前手牌与遗物摘要仍保留的 null。比较子树、随机 after:null 和数组空槽等例外照常保留；明确的 0、false、X、? 不按空值删除。该规则与共用卡牌摘要同时实施。
3. 选牌摘要可省略尚未展开的空 `upgrade_previews/enchant_previews/transform_previews` 以及空 bundles。继续保留 cards、selected_ids、options，即便是 []，以便明确表示候选、已选集合和当前按钮；整组未展开 upgrade_preview:null 已能按 default 省略。

例如 [火堆样本](2026-11-02-get-observation-selection-examples/smith-selected.full.json) 的 Bash 比较牌在采用这些规则后可写成以下设计片段；这是候选摘要，不是实测的新返回：

```json
{
  "before": {"id": 19, "name": "Bash", "type": "Attack", "energy_cost": "2"},
  "after": {"id": 19, "name": "Bash+", "type": "Attack", "energy_cost": "2"}
}
```

建议保留选择提示、min_select／max_select、完整 selected_ids、按钮 enabled、can_view_battlefield／can_view_upgrades／view_upgrades 和导航说明；它们用于判断当前操作与展示模式，不用 available_actions 猜测参数能力。附魔的实际数量与置灰状态仍保留。非战斗房间和顶栏的进一步摘要按各自场景核验，不顺带裁剪。

### 完整候选读取的附魔缺口

基线 `SelectionInspection.Read(full:true)` 的普通网格分支调用 BrowsedCard；原先后者只生成身份、费用与可选正文／悬停帮助，不生成卡牌 enchantment。于是 inspect_selection 的网格候选即使包含已有附魔，Python 摘要也无法保留该字段；手牌、包内容和实际节点比较使用另一读取路径，不能据此推断全部选牌都缺失。

这与[选牌说明](../development/card-selection.md#mcp-输出预设)中统一保留可见附魔的预期存在差异。扩大 get_observation 候选范围时须一起修复该分支：按当前页面正常渲染会展示的卡牌身份、附魔、费用和升级模式读取，不因屏幕外没有实例化节点而丢字段，也不伪造描边／资源图标。不能直接复制原模型 Enchantment.Amount 充当 UI 显示计数，仍按实际可显示的计数／图标规则处理。

该缺口已用带已有附魔的 40 张网格 GUI 复现；本轮实现扩展普通候选读取，并验证屏幕内外候选、原牌／升级模式和未知身份。详细问题记录位于本地 `.tmp/2026-11-02-card-summary-audit-report.md`；本文件保留后续修复任务，本轮修复与最终证据见实施结果。

inspect_deck／inspect_pile 也使用 BrowsedCard，而且 Python 浏览卡牌白名单没有 enchantment；这些工具的卡面附魔另留待各自核验，不能仅修 C# 共享读取就宣称已支持。它们的 detail_level:summary 与本次共用手牌摘要仍分别维护。

## 设计阶段核验结果与边界（实施前）

- 16 个场景分别完成采样与局清理，共 177 次真实 MCP 调用；39 份入库样本逐对象等于原始返回，通过当前观察结构校验，并确认覆盖全部 12 种受支持 selection.type。工具文字 JSON 与 structuredContent 一致。样本不是手写模拟数据。
- 对照截图检查了火堆升级、单／多牌附魔、随机变牌等预览；比较保留原牌 ID，未知侧不补全。地图／牌组覆盖、眼睛隐藏候选以及返回后保留待选状态均有实测样本。
- 采样分批完成：`gui-complete` 前 13 项成功；第 14 项在已采到奖励后，直接清理未完成的原生奖励父任务超时，因此该次总报告为 failed，不作为整轮通过报告。`gui-remaining` 按现有奖励测试的正常领取／推进流程完成余下 3 项，报告 passed。两批自有游戏进程均已退出，第一轮错误尝试也已退出。
- 初次 `gui-samples` 记录了采样脚本错误尝试关闭强制地图的失败；当时 available_actions 没有 close_map，工具正确拒绝。后续调整采样顺序，未修改地图行为。失败日志与原始证据一并保留。
- 源码已核对但本轮没有对应 GUI 样本：unsupported 未知类型、变牌结果明确已知的 `after` 分支、控制器隐藏升级复选框、所有事件／卡牌名称与各种数量偏好的组合。已有样本用于结构讨论，不把“全部类型”解释为穷举全部玩法内容与状态组合。
- 设计阶段仅新增核验文档与完整 JSON 示例，不修改生产代码、参数或摘要，不构建／安装新 Mod，也未重跑与本次文档无关的单元测试。正式游戏与个人存档未改动。
- 本地汇总：`.tmp/2026-11-02-observation-selections-review/verification.json`；全部样本对应见同目录 `samples-manifest.json`。后续定稿规则与实施结果见对应章节。

## 实施结果

本轮版本为 MCP `0.50.0`、Mod `0.49.0`、schema `31`。已实现上述定稿范围，原有 39 份 full 文件保留为设计阶段的原始数据；当前行为以[观察预设](../development/observation.md#mcp-输出预设)、[选牌](../development/card-selection.md)和[手牌摘要](../development/hand-inspection.md#参数与返回范围)为准。get_observation 的其他 13 组场景仍按总目录继续核验。

原生候选读取统一采用当前列表、升级模式和等价的克隆牌面数据；已存在的可见节点仅补实际描边和资源标记，部分裁切不再丢费用或附魔。附魔使用 NCard 的 ShowAmount／DisplayAmount／Status 显示规则；不显示数字的 Clone、Spiral 不提供内部 Amount。先核对 grid 与节点的身份状态，未知／锁定牌不会被真实升级描述覆盖。确认比较和覆盖页仍按其本身的显示边界读取。

GUI 同时发现并修复原有的反向滚动问题：NCardGrid.SetScrollPosition 直接设置位置与目标，跳过拖动更新中的虚拟行分配；定位后复用原生 AllocateCardHolders，并等待目标完整可点击后发出原生点击信号。滚动期间仍验证选择实例、候选、已选集合与数量限制。

Python 使用共享 selection_summary 处理候选、包与比较，并统一调整 card_summary。只有 get_observation 之外的三个专用 summary 在包装层再执行 default 过滤，避免删除 get_observation 已格式化的 health:null。完整响应校验、筛选与动作许可处理仍先于摘要。

独立只读审阅提出两项 Important：部分裁切候选的费用丢失、升级模式未知牌描述覆盖。新增失败检查已在旧实现中复现，再以同一轮修复解决；普通、升级模式及确认比较页的未知身份和部分裁切检查已通过。无待处理的审阅 Minor。记录位于 `.tmp/2026-11-02-selection-observation-implementation/review.md`。

最终验证：

- 构建 0 警告、0 错误；C# 独立检查 60 项通过，Python 全套 456 项通过。
- 20 个 GUI 场景通过，共 407 次真实 MCP 调用；普通／升级／确认预览中的未知身份、部分裁切、原牌与 UI 不变等原生检查 38 项通过。覆盖全部 12 类已支持选择及献祭、重掷、附魔、手牌标记和遗物摘要回归。
- 最终通过分两批：gui-suite-final 前 11 项通过，在随机变牌处由验证器错误要求删除 after:null 而中止；修正该断言后，gui-suite-remaining 的余下 9 项通过，两批使用相同 DLL。此前 gui-suite-green 的 grid 场景把需选 2 张的夹具按 1 张测试，已改用真实 min_select；这些测试错误没有改变产品契约。
- 两个审阅问题的 RED 位于 gui-review-red，GREEN 在最终两个完整列表场景中；原始旧行为失败、滚动问题和测试错误的日志均保留。全部自有游戏进程已关闭，未将某个失败总报告写成整轮通过。
- 汇总及每例映射：`.tmp/2026-11-02-selection-observation-implementation/verification-summary.json`；GUI 主目录同名，完整检查日志见同目录 python-final.log、csharp-final.log、build-reviewed.log。测试 DLL SHA-256 为 `99b600f3bbfa5c96845e5c1e9233390d54453ca877363f71b2e2db1fcf307885`。
- 40 候选检查记录的 get_observation 最大端到端耗时分别约 0.63／0.38 秒，包含 stdio／IPC；不将它们当成纯游戏线程耗时或帧性能基准。
- 未验证所有自定义 Mod 页面、所有事件／数量偏好组合及控制器模式；已知目标变牌的 after 分支保留单元覆盖，本轮 GUI 使用随机变牌。不扩大牌组／牌堆工具的字段范围，已有附魔仍待它们各自核验。

当前实际 summary 样本如下，均为未筛选的 get_observation 返回，没有改写数值或省略其余对象：

| 场景 | 完整 JSON | 证据下标 |
| --- | --- | --- |
| 火堆选中后确认升级 | [smith-selected.summary.json](2026-11-02-get-observation-selection-examples/smith-selected.summary.json) | gui-suite-final/smith/verify/evidence.json 的 17 |
| 单牌附魔比较 | [enchant-selected.summary.json](2026-11-02-get-observation-selection-examples/enchant-selected.summary.json) | gui-suite-final/enchant_single/verify/evidence.json 的 17 |
| 多牌升级，原牌身份不可读 | [upgrade-multi-selected.summary.json](2026-11-02-get-observation-selection-examples/upgrade-multi-selected.summary.json) | gui-suite-remaining/multi_upgrade/verify/evidence.json 的 14 |
| 随机变牌，after:null | [transform-selected.summary.json](2026-11-02-get-observation-selection-examples/transform-selected.summary.json) | gui-suite-remaining/transform/verify/evidence.json 的 18 |
| 牌包候选 | [bundle-candidates.summary.json](2026-11-02-get-observation-selection-examples/bundle-candidates.summary.json) | gui-suite-remaining/bundle/verify/evidence.json 的 6 |
| 牌包确认 | [bundle-selected.summary.json](2026-11-02-get-observation-selection-examples/bundle-selected.summary.json) | gui-suite-remaining/bundle/verify/evidence.json 的 17 |

本轮未更新正式游戏中的 Mod，需替换 Mod 后重启游戏，并重连 MCP 才能使用完整能力。
