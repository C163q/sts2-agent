# get_observation 场景核验与参数设计

> 当前状态：01–04 组战斗与全部选牌、07–15 组房间／事件／占卜／确认框／建筑师终章的约定 summary 已交付；05、06 组地图及牌组／牌堆覆盖已完成主体 default 占位和共用顶栏摘要，实际内容待对应工具核验。[剩余 16–17 组结算、解锁与菜单](2026-11-03-get-observation-result-menu.md)现状核验已交付，完整 full 样本与源码边界已记录，summary 待讨论定稿。17 组均已有对应核验记录，但仍有明确的后续范围，get_observation 整体尚未核销。

总清单与流程见[工具核验记录](2026-11-02-mcp-tool-review.md)。

## 核对基线与证据

- 初始目录基线：`09a6288`；MCP `0.48.0`、Mod `0.47.1`、原生 schema `29`。后续战斗实现更新至 MCP 0.49.0、Mod 0.48.0、schema 30，并新增游戏实测，结果见专项记录。
- 已有样本来自游戏 `v0.107.1` 的独立 GUI 测试实例，经真实 stdio MCP 调用获得。样本中的金币、能量、牌组与遗物可能经过测试夹具准备，数字不能视为角色正常开局配置，但返回内容确实来自当时 UI。
- 当前接口说明：[观察 JSON](../development/observation.md)、[公共预设](../development/mcp.md#输出预设)、[可见信息边界](../observation.md)。
- 主要实现：[GameTools.get_observation](../../src/sts2_mcp/game_tools.py)、[公共预设](../../src/sts2_mcp/output/presets.py)、[观察预设](../../src/sts2_mcp/output/observation_presets.py)、[输出结构与校验](../../src/sts2_mcp/output/game_output.py)、[玩法转换与 notes](../../src/sts2_mcp/output/player_output.py)。
- 原生观察组装：[GameAdapter.cs](../../src/Sts2Agent/Adapter/GameAdapter.cs) 的 Observe；场景可用工具与可见状态见 [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。

## 当前调用与返回范围

当前接受可选的 `preset: default/full/actions_only/summary/top_bar`，没有其他筛选参数。summary 精简战斗、当前选牌、商店卡牌、普通事件和占卜教学说明，并复用共用顶栏摘要，其余主体沿用 default；top_bar 为 actions_only 上下文加顶栏及遗物数量，完整契约见[观察预设](../development/observation.md#mcp-输出预设)。公开默认值由公共预设包装器提供，不能把内部旧版参数解析函数中的 full 默认值当作公开默认值。

```json
{"preset":"full"}
```

- `full` 是完整的基础观察：保留其原有空字段，普通手牌仍不含正文或悬停解释；不会因 full 自动切换或展开 UI。
- `default` 与 full 的内容范围一致，只按公共规则省略普通空值。
- `actions_only` 保留 `scene/screen/available_actions`，有选择时另保留 `selection.type/status`，不含占卜图片。各预设都实时读取、完整校验并刷新内部动作许可；不要求之前调用过其他观察。
- 基础观察不返回动作 `transition`，不会回放上次动作的事件。`stop_reason` 也不属于本工具返回；本轮若讨论相关需求，须区分当前静态画面与动作结果。
- 成功结果直接是玩法 JSON，没有 `ok/state/snapshot_id` 等通信包装。MCP 文字 JSON 与 `structuredContent` 内容相同；占卜的 PNG 另作为图像内容返回。

当前 full 原生快照投影的顶层字段如下；`notes` 按实际内容附加，不是固定存在的字段：

```text
scene, map, screen, turn, player, enemies, allies, top_bar, buttons,
selection, rewards, rest_site, treasure, shop, ancient, event,
divination, confirmation, epilogue, run_result, available_actions
```

`scene` 表示原生判断的底层战斗 / 房间 / 结算场景；覆盖页面另由 `screen.view`、`selection.type/status` 和对应内容块描述。例如打开地图后 scene 可以仍为 combat 或 event，而不是 map；`inspect_map` 自己返回的 `scene:"map"` 不能拿来代替本工具样本。牌组 / 牌堆浏览页也不会让本工具自动返回整页卡牌。

## 场景目录

以下是当前代码识别的分支及其组合，不承诺覆盖未知自定义 Mod 页面。编号用于选择示例；相同结构的名称与数值变化不穷举所有卡牌、怪物或事件实例。

| 编号 | 场景组 | 需要展开的分支与返回差异 | 当前样本状态 |
| --- | --- | --- | --- |
| 01 | 普通战斗与角色差异 | `scene:combat`；player、enemies、allies、turn、buttons；储君星星、故障机器人充能球、奥斯提与共享格挡、悬浮君王之剑、手牌附魔 / 费用颜色 / 标记、不同意图与生命显示。角色差异是数据变体，不是额外 scene | 本阶段完成，见[战斗字段、样本及实施结果](2026-11-02-get-observation-combat.md) |
| 02 | 普通卡牌选择 | `selection.type` 为 `hand/choose_one/grid/combat_pile/deck/reward/bundle/view_cards`；单选 / 多选、候选、已选 ID、确认 / 跳过 / 献祭 / 重掷 / 包选项，候选正文按是否实际展开决定 | 本阶段完成，见[选牌专项记录](2026-11-02-get-observation-selections.md) |
| 03 | 升级、附魔与变牌选择 | `hand_upgrade/deck_upgrade/deck_enchant/deck_transform`；候选页、查看升级、选中后的前后预览、随机变牌 `after:null`、预览取消 / 确认。full 基础观察仍不等于 inspect_selection full | 同上，含单／多牌预览与查看升级 |
| 04 | 选牌时查看战场或被覆盖 | `selection.status:battlefield/covered/unsupported`；待处理选择继续存在，隐藏候选不补出，notes 指示返回方式；unsupported 作为人工输入边界单独核对 | 同上，眼睛／地图／牌组已实测；未知类型保留源码核验边界 |
| 05 | 地图覆盖 | `screen.view:map` 与 map 摘要，包括当前节点、能否前进、可选节点；底层战斗 / 房间内容按可见规则隐藏。区分强制地图、可关闭地图、选择后查看地图及换幕过程 | 本阶段占位已实现，后续补充内容与摘要，见[地图与浏览覆盖](2026-11-02-get-observation-browsing.md) |
| 06 | 牌组与牌堆浏览覆盖 | `screen.view:deck/draw_pile/discard_pile/exhaust_pile`；本工具不附整页卡牌列表；区分从房间、战斗、地图或待处理选牌打开，以及关闭返回路径 | 同上；页面主体暂用 default、顶栏使用共用摘要，牌面和模式待对应工具核验，顶栏另见专项修复 |
| 07 | 奖励列表 | `scene:rewards` 与 rewards；奖励行、领取后、空列表、继续 / 放弃；打开卡牌奖励后与 selection 组合，不能提前返回未打开候选 | [本轮现状与 full 样本](2026-11-02-get-observation-rooms.md#07奖励列表)，summary 已交付，房间主体沿用 default |
| 08 | 火堆 | `scene:rest_site` 与 rest_site；选项、灰置、画面已展开说明、操作后继续；升级选牌另见 03 | [普通／灰置／多次操作及后续奖励](2026-11-02-get-observation-rooms.md#08火堆)，summary 已交付，房间主体沿用 default |
| 09 | 宝箱房 | `scene:treasure` 与 treasure；未开启、已开且遗物可见、领取后 / 空箱、继续；不返回未开箱内容 | [开箱／待领／空箱及额外奖励](2026-11-02-get-observation-rooms.md#09宝箱房)，summary 已交付，房间主体沿用 default |
| 10 | 商店 | `scene:shop` 与 shop；`merchant/inventory/opening/closing`，商品卡摘要、价格、售罄 / 补货、删牌选择，以及当前可见顶栏提示 | [现状与 full 样本](2026-11-03-get-observation-shop-ancient-event.md)已交付，summary 已交付 |
| 11 | 先古之民 | `scene:ancient` 与 ancient；已显示对话、推进对话、馈赠选项、后续选择与继续。区分基础选项正文和额外悬停帮助 | [现状与 full 样本](2026-11-03-get-observation-shop-ancient-event.md)已交付，summary 已交付 |
| 12 | 普通事件 | `scene:event` 与 event；事件正文、可选 / 锁定选项、致死警告、选择后正文与继续、后续奖励或战斗，再返回事件；覆盖时不附隐藏正文 | [初始／翻页／锁定／警告及后续交互](2026-11-03-get-observation-shop-ancient-event.md)已交付，summary 已交付 |
| 13 | 占卜 | 底层 scene:event，`screen.view:divination`；`playing/settling/finished`，棋盘 grid、可见次数、工具、对话、继续以及独立 PNG；被覆盖时棋盘和图片不返回 | [现状核验与 full／图片已交付，summary 已交付](2026-11-03-get-observation-divination-confirmation-epilogue.md#13占卜) |
| 14 | 确认框与人工输入 | Trial 弹窗使用 `screen.view:confirmation` 与 confirmation；未知确认来源可能为 confirmation:null 并附 notes.interaction；区分可操作确认框和其他未支持覆盖页 | [来源、取消／确认及人工边界已核验，summary 已交付](2026-11-03-get-observation-divination-confirmation-epilogue.md#14确认框与人工输入) |
| 15 | 建筑师终章 | `scene:epilogue`、`screen.view:epilogue`；已完整显示的气泡、推进 / 继续按钮、尚未准备或被地图 / 牌组覆盖。进入终章与已判定胜利并非同一条件 | [对话、覆盖与交接已核验，牌组覆盖校验已修复；summary 主体沿用 default](2026-11-03-get-observation-divination-confirmation-epilogue.md#15建筑师终章) |
| 16 | 胜负结算与解锁 | `scene:run_result`；`outcome/summary/history/leaderboard/timeline/epoch/unlock/tutorial` 八种 phase，分数、徽章、发现、已显示解锁卡牌 / 遗物 / 药水与按钮随页变化 | [现状与完整 full 已交付](2026-11-03-get-observation-result-menu.md#16胜负结算与解锁)，7 种 phase 已采样，leaderboard 仅源码核验；summary 待定稿 |
| 17 | 主菜单、加载及未识别页面 | `scene:main_menu/loading_or_noncombat`；后者是当前仍在使用的兜底分类，不等同于加载中；主菜单体系也可能包含未支持子页，不返回其正文或操作 | [启动过渡、主菜单、普通时间线与结算退出已核验](2026-11-03-get-observation-result-menu.md#17主菜单加载及未分类页面)，其余兜底分支明确源码边界；summary 待定稿 |

除上表外，各组还须检查 `screen.status` 的 `visible/covered/hidden/not_ready/not_applicable`、顶栏是否可读、动画中数值、空容器与未知值，以及 available_actions 是否对应当前真实可用工具。目录不表示所有状态都能与所有页面任意组合。

失败情况单列核对：参数非法 `invalid_request`、控制权占用 `controller_busy`、通信超时 `timeout`、响应无效或 I/O 失败 `transport_error`，以及原生返回的错误。这些失败返回 error，不是填满 null 的成功观察；不会因为 full 自动附带成功画面。

## 已有完整 JSON 示例

以下文件只保存实际返回的玩法 JSON，不加入解释字段、不删除空值、不截断数组、不改写名称和数值。不是本轮新执行的游戏测试；仅作为现状设计材料，不能替代之后对改动的验证。

| 样例 | JSON | 原始证据（仓库本地、未纳入 Git） | 调用位置 |
| --- | --- | --- | --- |
| 战斗，含蜡质与普通遗物 | [combat.full.json](2026-11-02-get-observation-examples/combat.full.json) | `.tmp/2026-11-02-default-preset/gui-green/combat/verify/evidence.json` | 数组下标 0，get_observation，preset:full |
| 故障机器人与充能球 | [orbs.full.json](2026-11-02-get-observation-examples/orbs.full.json) | `.tmp/2026-11-02-default-preset/gui-green/orbs/verify/evidence.json` | 数组下标 0，get_observation，preset:full |
| 火堆选项 | [rest-site.full.json](2026-11-02-get-observation-examples/rest-site.full.json) | `.tmp/2026-11-02-default-preset/gui-green/smith/verify/evidence.json` | 数组下标 0，get_observation，preset:full |
| 普通事件选项 | [event.full.json](2026-11-02-get-observation-examples/event.full.json) | `.tmp/2026-11-02-default-preset/gui-remaining/event/verify/evidence.json` | 数组下标 0，get_observation，preset:full |
| 占卜进行中 | [divination.full.json](2026-11-02-get-observation-examples/divination.full.json) | `.tmp/2026-11-02-default-preset/gui-green/divination/verify/evidence.json` | 数组下标 5，get_observation，preset:full，另有 1 张 PNG |

占卜 JSON 的 `grid.image` 只有图片尺寸，不含图像数据；实际 MCP 另返回 PNG 内容，JSON 文件本身不是该调用的全部多模态输出。图片及运行报告保留在原测试目录，其他预设的样本不冒充 full。

## 设计与后续核验

- 战斗主画面阶段已经完成，见[专项记录](2026-11-02-get-observation-combat.md)。全部选牌界面的约定设计已实现，见[选牌核验与实施](2026-11-02-get-observation-selections.md)。上表其他“待选择”不表示实现缺失，而是本轮尚未展开样例核验。
- 选牌包含战斗、火堆、事件及先古之民等底层场景；本轮围绕 selection 及其可见上下文核验，不自动决定这些房间自身的摘要字段。
- 奖励、火堆与宝箱的基线及完整样本见[07–09 组记录](2026-11-02-get-observation-rooms.md)，summary 已交付，定稿与验证见同页。奖励可见行限制已在[浏览范围修复](2026-11-02-browsable-content-audit.md)中取消，新增当前 full/default/summary 样本；不要将原先截断的基线文件当作当前返回。
- 商店、先古之民与普通事件的字段、分支和 82 份完整 full 样本见[10–12 组记录](2026-11-03-get-observation-shop-ancient-event.md)；summary 已实现共用商品卡牌摘要、保留先古主体、事件页面正文与 false 警告省略。商店卡牌正文由专门查看工具提供，这是已确认的职责分工，不作为 get_observation 的信息缺口。
- [16–17 组结算、解锁与菜单](2026-11-03-get-observation-result-menu.md)已保存本轮完整 full，区分正常流程、history 夹具与 leaderboard 源码边界；失败死亡原因的混合语言缺口已记录，尚未修复。当前结算主体沿用 default，后续 summary 待讨论。
- 新的设计结论、确认范围、验证结果及后续提交持续记录于对应专项文件，并在本目录同步状态。

首轮目录检查：5 份初始 JSON 与上述原始 full 调用逐对象一致，能够通过当前观察结构校验；清单名称与 43 个公开工具对应，链接与 Markdown 围栏检查通过。首轮目录整理未启动游戏；后续新增的战斗实测、完整样本及未覆盖范围见专项记录。
