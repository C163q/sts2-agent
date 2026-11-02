# get_observation 选牌界面核验

> 当前状态：现状核验已完成，进入摘要设计讨论。已收集 16 个场景的 39 份完整 full 实测样本，覆盖全部 12 类已支持选择及主要预览／覆盖变化；未知选择等源码分支的未实测范围见文末。选牌摘要尚未定稿，未修改工具行为。战斗主画面摘要已交付，其余房间摘要仍按总目录另行讨论。暂无需求阻塞。

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

调用参数统一为 `{"preset":"full"}`。以下是结构说明，完整返回样本另列；不能把 `inspect_selection` 的返回改名作为本工具示例。

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
6. **数量限制与滚动**：数量上限不等于屏幕当前可见候选总数；selected_ids 也不应随候选裁剪。本轮 40 张牌的网格中，基础观察实际只返回 15 张可见牌，inspect_selection 则读取全部 40 张。眼睛和覆盖页只改变可见信息，不能偷偷取消待处理选择。

## 完整 full 返回样本

下列文件均为本轮真实 stdio MCP 的 `get_observation({"preset":"full"})` 返回，保留整个玩法 JSON、所有原有空值、完整数组和 notes，未改名、补字段或截断。每个样本对应一张隔离游戏截图，截图及完整调用序列留在本地证据目录。这里只保存 JSON；这些选择页没有额外 MCP 图像内容。

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

## 当前 summary 与待讨论范围

当前 `get_observation.summary` 只精简战斗资源、普通手牌和顶栏，**尚不精简 selection 内的牌**；非战斗仍等同 default。因此同一类选择发生在战斗、火堆或事件时，当前外层摘要程度不同。该差异是本轮设计对象，尚未改动。

推荐候选方案：所有 `selection` 卡牌位置统一采用 inspect_hand／inspect_selection 的手牌摘要字段，并保留选择提示、数量限制、全部已选 ID、实际按钮、升级模式、包 ID、附魔操作说明和随机变牌标记。比较中的牌也使用摘要，需要正文时调用 inspect_selection full。保持现有战斗摘要；非战斗外层的房间和顶栏字段暂保留，待相应场景核验再决定。

另两种取舍：保留已展开比较的正文更接近当页阅读，但与已确认的 inspect_selection.summary 规则不一致；直接裁掉房间和顶栏只留选择会更短，但会顺带决定尚未审查的非战斗外层数据。本轮建议先统一选择内容本身。

仍待确认：是否采用上述卡牌规则，以及是否精简 `options`、升级模式布尔字段、空候选／空预览等选择上下文。它们各自描述当前 UI 状态，不能未经决定按“空即无用”删除；本轮不新增筛选或切换参数，参数需求在样本讨论后确定。

## 本轮核验结果与边界

- 16 个场景分别完成采样与局清理，共 177 次真实 MCP 调用；39 份入库样本逐对象等于原始返回，通过当前观察结构校验，并确认覆盖全部 12 种受支持 selection.type。工具文字 JSON 与 structuredContent 一致。样本不是手写模拟数据。
- 对照截图检查了火堆升级、单／多牌附魔、随机变牌等预览；比较保留原牌 ID，未知侧不补全。地图／牌组覆盖、眼睛隐藏候选以及返回后保留待选状态均有实测样本。
- 采样分批完成：`gui-complete` 前 13 项成功；第 14 项在已采到奖励后，直接清理未完成的原生奖励父任务超时，因此该次总报告为 failed，不作为整轮通过报告。`gui-remaining` 按现有奖励测试的正常领取／推进流程完成余下 3 项，报告 passed。两批自有游戏进程均已退出，第一轮错误尝试也已退出。
- 初次 `gui-samples` 记录了采样脚本错误尝试关闭强制地图的失败；当时 available_actions 没有 close_map，工具正确拒绝。后续调整采样顺序，未修改地图行为。失败日志与原始证据一并保留。
- 源码已核对但本轮没有对应 GUI 样本：unsupported 未知类型、变牌结果明确已知的 `after` 分支、控制器隐藏升级复选框、所有事件／卡牌名称与各种数量偏好的组合。已有样本用于结构讨论，不把“全部类型”解释为穷举全部玩法内容与状态组合。
- 本轮只新增核验文档与完整 JSON 示例，不修改生产代码、参数或摘要，不构建／安装新 Mod，也未重跑与本次文档无关的单元测试。正式游戏与个人存档未改动。
- 本地汇总：`.tmp/2026-11-02-observation-selections-review/verification.json`；全部样本对应见同目录 `samples-manifest.json`。下一步根据这些现状样本确认 summary 字段及可能需要的参数，再进入实现。
