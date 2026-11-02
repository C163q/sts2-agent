# get_observation 地图与牌组／牌堆浏览覆盖核验

> 当前状态：现状采样与源码核验已完成，进入设计讨论。对应总目录 05、06 组；5 类场景的 24 份完整 full 示例已保存，摘要及新增字段尚未定稿，生产行为未修改。战斗及选牌约定范围已交付，其余 11 组尚未展开，get_observation 整体未核销。

总流程见[工具核验记录](2026-11-02-mcp-tool-review.md)，分组见[观察场景目录](2026-11-02-get-observation-review.md)。本轮查看的是 get_observation，不核销 inspect_map、inspect_deck 或 inspect_pile；后者仅用于打开原生页面和核对数据来源。

## 基线与证据

- 核对日期：2026-11-02，项目基线 `61c84cb`，MCP `0.50.0`、Mod `0.49.0`、schema `31`。
- 游戏 Linux `v0.107.1`、release `59260271`，RitsuLib `0.6.10`；游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 隔离运行时与构建产物 DLL 均为 `99b600f3bbfa5c96845e5c1e9233390d54453ca877363f71b2e2db1fcf307885`。没有重新构建或安装正式游戏 Mod。
- 原生组装：[GameAdapter.Observe](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[CardView](../../src/Sts2Agent/Observation/CardView.cs)、[MapView](../../src/Sts2Agent/Observation/MapView.cs)、[MapInspection](../../src/Sts2Agent/Observation/MapInspection.cs)、[CombatObservation](../../src/Sts2Agent/Observation/CombatObservation.cs)、[RunUi](../../src/Sts2Agent/Observation/RunUi.cs)。MCP 投影见 [observation_presets.py](../../src/sts2_mcp/output/observation_presets.py)、[game_output.py](../../src/sts2_mcp/output/game_output.py)、[player_output.py](../../src/sts2_mcp/output/player_output.py)。
- 核对目标程序集的 `NMapScreen.Open/Close`、`NCapstoneContainer.Open/CloseInternal` 和 `NDeckViewScreen`；本地反编译证据为 `.tmp/decompiled/NMapScreen.cs`、`.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Screens.Capstones.NCapstoneContainer.cs`、`.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Screens.NDeckViewScreen.cs`，不纳入 Git。
- 本轮证据目录：`.tmp/2026-11-02-observation-browsing-review/`。样本经真实 stdio MCP 获取，截图来自相邻的 capture_screenshot 调用；不是同一帧的原子采样。测试局的卡牌、能力、楼层和房间由现有夹具准备，不代表正常开局配置。

## 已核实的现状

### 页面与底层场景分别表达

scene 保留战斗或房间类型。覆盖页由 screen.view 表示，不会自动把 scene 改成 map 或 deck。

| 当前最上层页面 | screen | 当前页面内容 | 底层内容 |
| --- | --- | --- | --- |
| 地图 | `status:visible, view:map` | map 摘要 | 战斗对象隐藏；房间对象可能保留 status:covered，正文隐藏 |
| 永久牌组 | `view:deck`；通常 status:covered，换幕尚无房间时为 not_applicable | 只有页面标识，没有卡牌列表、升级模式、排序或底部说明 | 底层战斗／房间按遮挡规则处理 |
| 抽牌堆 | `status:covered, view:draw_pile` | 只有页面标识，没有卡牌列表和底部说明 | 同上 |
| 弃牌堆 | `status:covered, view:discard_pile` | 同上 | 同上 |
| 消耗堆 | `status:covered, view:exhaust_pile` | 同上 | 同上 |

这里的 covered 表示基础战斗／房间内容受到覆盖，不表示牌组页面本身不可操作；以 available_actions 判断当前可用工具。换幕起点没有当前战斗／房间，scene:loading_or_noncombat；此时地图仍可操作，叠加牌组后则 screen.status:not_applicable、view:deck。不能只凭 scene 名称推断处于加载，也不能仅凭 status 判断牌组是否显示。screen 还没有表示完整页面栈的字段。

### 地图摘要

get_observation.full 的 map 仅含：status、act、current_node、can_travel、selectable_nodes。没有 nodes、next、visited_path、节点类型或名称。即使 full，仍须用 inspect_map 查看地图详情。

- 战斗中按正常关闭选路开关的状态，can_travel:false，selectable_nodes:[]。
- 房间结束后的地图可以给出实际可选节点；换幕起点 current_node:null，不代表地图不可选。
- 是否可关闭取决于原生返回按钮；available_actions 中是否有 close_map，与 can_travel 是不同条件。
- 牌组叠在地图之上时，screen.view:deck，map:null；不返回被挡住的地图摘要。关闭牌组后才重新返回 map。
- full 保留 map:null 与 current_node:null；default 依公共规则省略这些普通空值。地图尚在过渡时不应拿稳定地图样本替代。

### 卡牌浏览及返回路径

get_observation 不使用上一次 inspect_deck／inspect_pile 的结果缓存，也不会因当前已打开这些页面而附送卡牌。现有专用工具各自可返回完整可浏览列表；detail_level 和 get_observation 的 preset 是独立概念。

- 单一卡牌浏览层：牌组和三类牌堆相互替换，不累积独立的关闭步骤。
- 地图是另一层。地图上打开牌组，close_card_view 返回地图；不能透过上层牌组调用 close_map。
- 从卡牌页调用 inspect_map，复用原生顶栏地图按钮，关闭卡牌页后打开／露出地图。
- 从待处理选择先查看战场，再打开地图／牌组时，selection.status:covered；候选、数量和已选内容隐藏，notes.selection 提醒返回。关闭当前浏览后回到 battlefield，还需 set_selection_view 返回选择，不能直接选隐藏候选。
- 空牌堆、入口隐藏或禁用时，inspect_pile 可能没有打开新页面；get_observation 应按实际停留页面返回，不能仅凭之前请求的 pile 声称正在浏览。现行语义见[牌堆接口](../development/pile-inspection.md)。

### 可用操作与顶栏

地图展开时，available_actions 不包括下层房间／战斗动作；牌组／牌堆打开时也不会提供 end_turn 或 play_card。inspect_pile 是否出现表示至少一个入口可用，不保证任意 pile 都可查看。close_card_view 仅关闭当前受支持且可关闭的卡牌页。

当前实现对顶栏读取有场景差异：本轮所有牌组／牌堆浏览页均为 top_bar:null；地图覆盖战斗时也是 null，而地图覆盖事件／奖励时仍返回顶栏。相应遗物和药水查看也有差异。RunUi.TopBarReadable 复用战斗／房间是否被覆盖作为条件，而这些页面的顶栏实际仍可能显示。须结合本轮截图记录缺口，不能将场景差异当作 UI 必然差异。

## full 示例

所有示例统一调用 `get_observation({"preset":"full"})`。文件仅保存实际返回对象，保留全部原有 null、空数组、notes 和操作列表；不拿 inspect_* 响应代替基础观察。证据列的数字是对应 evidence.json 中从 0 开始的数组下标。

| 场景／步骤 | 完整 JSON | 本地证据位置／下标 |
| --- | --- | --- |
| 战斗中查看地图 | [combat-map.full.json](2026-11-02-get-observation-browsing-examples/combat-map.full.json) | gui/combat：3 |
| 战斗地图上叠加牌组 | [combat-deck-over-map.full.json](2026-11-02-get-observation-browsing-examples/combat-deck-over-map.full.json) | gui/combat：6 |
| 关闭牌组返回战斗地图 | [combat-returned-map.full.json](2026-11-02-get-observation-browsing-examples/combat-returned-map.full.json) | gui/combat：10 |
| 战斗牌组：查看升级、费用降序 | [combat-deck-upgrades.full.json](2026-11-02-get-observation-browsing-examples/combat-deck-upgrades.full.json) | gui/combat：14 |
| 查看抽牌堆 | [combat-draw-pile.full.json](2026-11-02-get-observation-browsing-examples/combat-draw-pile.full.json) | gui/combat：18 |
| 从牌堆切换至牌组 | [combat-deck-replacing-pile.full.json](2026-11-02-get-observation-browsing-examples/combat-deck-replacing-pile.full.json) | gui/combat：22 |
| 从牌组打开地图 | [combat-map-replacing-deck.full.json](2026-11-02-get-observation-browsing-examples/combat-map-replacing-deck.full.json) | gui/combat：25 |
| 查看弃牌堆 | [combat-discard-pile.full.json](2026-11-02-get-observation-browsing-examples/combat-discard-pile.full.json) | gui/combat：31 |
| 关闭浏览返回战斗 | [combat-returned-combat.full.json](2026-11-02-get-observation-browsing-examples/combat-returned-combat.full.json) | gui/combat：34 |
| 选牌覆盖的原始候选页 | [selection-candidates.full.json](2026-11-02-get-observation-browsing-examples/selection-candidates.full.json) | gui/selection：3 |
| 待选牌时查看战场并打开牌组 | [selection-deck-covering-selection.full.json](2026-11-02-get-observation-browsing-examples/selection-deck-covering-selection.full.json) | gui/selection：7 |
| 待选牌时以地图覆盖 | [selection-map-covering-selection.full.json](2026-11-02-get-observation-browsing-examples/selection-map-covering-selection.full.json) | gui/selection：10 |
| 关闭地图返回战场，选择仍待处理 | [selection-returned-battlefield.full.json](2026-11-02-get-observation-browsing-examples/selection-returned-battlefield.full.json) | gui/selection：13 |
| 完成选择后查看消耗堆 | [selection-exhaust-pile.full.json](2026-11-02-get-observation-browsing-examples/selection-exhaust-pile.full.json) | gui/selection：19 |
| 事件中查看牌组 | [event-deck.full.json](2026-11-02-get-observation-browsing-examples/event-deck.full.json) | gui/event：3 |
| 事件中查看地图 | [event-map.full.json](2026-11-02-get-observation-browsing-examples/event-map.full.json) | gui/event：6 |
| 关闭地图返回事件 | [event-returned-event.full.json](2026-11-02-get-observation-browsing-examples/event-returned-event.full.json) | gui/event：9 |
| 战后地图，可选择下一节点 | [rewards-map.full.json](2026-11-02-get-observation-browsing-examples/rewards-map.full.json) | gui-remaining/rewards：3 |
| 战后地图上叠加牌组 | [rewards-deck-over-map.full.json](2026-11-02-get-observation-browsing-examples/rewards-deck-over-map.full.json) | gui-remaining/rewards：6 |
| 关闭牌组返回战后地图 | [rewards-returned-map.full.json](2026-11-02-get-observation-browsing-examples/rewards-returned-map.full.json) | gui-remaining/rewards：9 |
| 关闭地图返回奖励页 | [rewards-returned-rewards.full.json](2026-11-02-get-observation-browsing-examples/rewards-returned-rewards.full.json) | gui-remaining/rewards：12 |
| 换幕强制地图，尚未进入节点 | [act-entry-map.full.json](2026-11-02-get-observation-browsing-examples/act-entry-map.full.json) | gui-remaining/act_entry：3 |
| 换幕强制地图上查看牌组 | [act-entry-deck-over-map.full.json](2026-11-02-get-observation-browsing-examples/act-entry-deck-over-map.full.json) | gui-remaining/act_entry：7 |
| 关闭牌组返回换幕地图 | [act-entry-returned-map.full.json](2026-11-02-get-observation-browsing-examples/act-entry-returned-map.full.json) | gui-remaining/act_entry：10 |

证据根目录为 `.tmp/2026-11-02-observation-browsing-review/`，列出的批次／场景下均有 evidence.json 与 screenshots/<步骤>.png。逐文件映射另存 samples-manifest.json。combat 的 returned-map 表示关闭上层牌组后露出的地图；map-replacing-deck 表示从牌组入口重新打开地图。

例如，战斗中已开启查看升级并按费用降序的牌组页，当前基础 full 的完整返回仍只有页面上下文：

```json
{
  "scene": "combat",
  "map": null,
  "screen": {
    "status": "covered",
    "view": "deck"
  },
  "turn": null,
  "player": null,
  "enemies": null,
  "allies": null,
  "top_bar": null,
  "buttons": null,
  "selection": null,
  "rewards": null,
  "rest_site": null,
  "treasure": null,
  "shop": null,
  "ancient": null,
  "event": null,
  "divination": null,
  "confirmation": null,
  "epilogue": null,
  "run_result": null,
  "available_actions": [
    "inspect_deck",
    "inspect_pile",
    "close_card_view",
    "inspect_map"
  ]
}
```

## 待讨论的设计范围

以下是候选，尚未确认或实现：

1. **维持轻量页面上下文**：get_observation 继续只标识浏览页，详情由 inspect_* 提供。响应短，但已展开牌面及浏览状态仍缺失。
2. **推荐：补全当前已打开页面的观察**：地图提供可选节点的可辨识类型／名称；牌组／牌堆提供完整可浏览列表，summary 复用手牌卡牌摘要。另保留当前升级模式、排序及原生页面说明；不自动打开其他页面。需先决定这些内容在 full/default 中的范围，再确定 summary，不能只在 summary 突然增加 full 没有的信息。

若选择补全当前页面，还需约定容器名称、卡牌 ID（现有 deck:／pile: 与战斗整数 ID 不同）、未知／锁定牌、升级预览、附魔、费用颜色及默认牌序。抽牌堆必须沿用原生浏览排序，不能输出真实抽取顺序。牌组与牌堆的卡牌附魔目前有已知缺口，不能直接复用其现有响应后便声称数据完整；前一阶段仅修复了选牌候选，见[选牌实施边界](2026-11-02-get-observation-selections.md#实施结果)。

顶栏应按实际可见控件判定，与是否允许操作下层战斗分离。涉及药水／遗物查看是否可用时，必须单独核对原生交互状态，不能仅因为能读到顶栏就开放操作。整体修复范围待本轮设计确认。

## 核验结果与边界

- 5 类场景采样及正常局清理完成，共 113 次真实 MCP 调用；24 份完整 full JSON 逐对象等于原始 structuredContent，通过当前观察校验。文字 JSON 与 structuredContent 也在每次采样时核对一致。
- 地图覆盖战斗／事件／奖励、换幕强制地图、地图叠牌组、牌组／地图互换、三类非空牌堆、选择被覆盖及返回均有样本和截图。地图被牌组盖住、卡牌页中 end_turn、强制地图 close_map 的非法请求均被拒绝。
- 完成证据分两批：gui 的 combat／selection／event 采样及清理通过；gui-remaining 的 rewards／act_entry 完成采样及清理，报告 passed。第一批总报告在奖励采完后的测试清理超时而 failed，不能写成整批通过。补跑时按现有奖励验证流程正常领取并推进，再结束局；两批使用相同 DLL，所有自有游戏进程已关闭。
- 更早根目录的失败记录来自脚本误把第 0 层调试入战当作正常地图可关闭状态。后续改用现有夹具的正确楼层和选路开关；未修改生产工具以迁就测试。
- 顶栏缺口与两次采样问题记录在本地[问题报告](../../.tmp/2026-11-02-observation-browsing-review-report.md)。本轮同时修正选牌专项记录开头残留的“实施中”，使其与已交付结果一致，未改历史样本。
- 本轮没有穷举所有房间组合、双 Boss、飞鞋耗尽、绘图模式、所有瞬态／模态遮挡、自定义 Mod 页面。空堆／隐藏入口未新采 get_observation 样本，仅核对当前源码及现行接口语义；不把专用工具结果冒充基础观察。
- 仅修改调研文档与实际样本，未改生产参数、摘要或运行时行为，未构建或安装新 Mod；没有重跑与本轮文档无关的单元测试。JSON、来源、截图存在性、Markdown 围栏、链接及 git diff 检查见本地 verification.json。
