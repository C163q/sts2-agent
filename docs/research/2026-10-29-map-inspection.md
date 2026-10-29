# 地图查看设计与实施记录

当前状态：已完成。共 3 项，已完成 3 项；文件接口、92 项 Python 回归、30 项独立原生检查与独立审阅均通过，Mod 0.12.0 已安装并保留编号备份。正式游戏需要重启后另行采样验证，MCP 留待格式确认后接入。

## 已确认范围

专门的 `inspect_map()` 真实打开或复用当前幕原生地图，一次返回整个可滚动浏览的地图，不逐屏滚动，不读取未来幕的地图。正常一局的三幕以 `act`（从 1 开始）区分，不把地图行号等同于全局楼层。`close_map()` 独立关闭地图；卡牌页保持使用 `close_card_view()`。

返回 `scene: map`、`screen`、`act`、`current_node`、`visited_path`、`can_travel`、`selectable_nodes` 和 `nodes`。节点包含当前幕内稳定 ID、从下到上的 `row`、从左到右的 `column`、可见 `type` 和实际有向连线 `next`。先古之民和 Boss 的外观允许转为英语 `name`。双 Boss 保留第一 Boss 到第二 Boss 的连接；教程起点按实际图标识别，不强制为先古之民。

地图结构与当前选路权限分离：`next` 不因飞鞋改写，`selectable_nodes` 取原生节点当前允许点击的集合。战斗阶段 `can_travel: false`、候选为空；房间完成后的地图允许选路时，包含原生飞鞋规则产生的未连接节点。查看不消耗飞鞋，不进入房间，不读取未来随机结果。未走过问号保持 `unknown`；走过后已揭晓图标单独保留 `revealed_type`，不读取悬停历史。

地图和卡牌页遵循原生顶栏按钮：在卡牌页上请求地图会先由游戏关闭卡牌页、再打开或露出地图，不强行同时读取被挡住的地图。关闭地图要求地图当前在最上层且原生返回按钮可用，不穿透卡牌页。过渡、其他详情/弹窗、选牌和多人拒绝；异步期间页面被人关闭或替换时返回 `illegal_action`，不自动重开。

## 已核对的本地证据

基线：2026-10-29，游戏 v0.107.1、main、59260271，Godot 4.5.1.m.12。证据程序集为游戏目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，反编译证据保留于不纳入 Git 的 `.tmp/decompiled/`。

- `MapPoint.Children`、`StandardActMap`：连线和双 Boss 串联。
- `NMapScreen.SetMap/DrawPaths/RecalculateTravelability/SetTravelEnabled`：原生 UI 节点、实际绘制路径、起点与 Boss 特殊候选处理、房间进度开关。
- `MapTravel.GetTravelablePointsFrom`、`WingedBoots.ShouldAllowFreeTravel`：原生自由移动 Hook，飞鞋耗尽后恢复连线规则。
- `NMapPoint.State/IsTravelable/RefreshState/OnRelease`：结构上的下一步与实际可点击状态不同；绘图模式不允许选路。
- `NNormalMapPoint.UpdateIcon`：已访问的问号可切换为揭晓图标；不能将未来内部房间类型作为观察。
- `NTopBarMapButton.OnRelease`：关闭卡牌层并露出地图；`NMapScreen` 是独立层。

## 实施计划

采用 writing-plans / executing-plans，在当前已获授权的项目工作区完成，保留既有文件接口先行流程；不修改全局 MCP 配置。

### 1. 文件接口与原生页面

- [x] 为 `player_result` 添加地图投影回归用例，确认旧实现丢弃地图字段的失败。
- [x] 新增 `MapView.cs` 管理页面可用性/就绪/原生返回按钮，新增 `MapInspection.cs` 读取当前幕原生节点和绘制连线、英语名称、已走路线与原生候选。
- [x] `GameAdapter` 接入无参数 `inspect_map/close_map`，异步等待并复核 run/map/page，UI 更改更新控制令牌；Mod 版本升至 0.12.0。
- [x] `roundtrip_client.py` 接入调用和投影；独立实例运行文件端到端脚本，确认整图、重复查看、关闭和玩法不变。

### 2. 原生检查

- [x] 新增严格测试模式开关 `--check-map` 和 `check_test_map`，仅独立实例可用。
- [x] 检查整图包含屏外节点、稳定 ID、单/双 Boss、未揭晓问号、地图/卡牌页切换与异步人工关闭/覆盖。
- [x] 使用隔离的真实选路阶段检查无飞鞋、有剩余次数飞鞋和耗尽飞鞋的候选，确认查看不消耗次数或 RNG，不将场景夹具暴露为正式工具。
- [x] 编译零警告/错误、完整 Python 回归；独立游戏原生检查与截图，无出牌或结束回合操作。

### 3. 交付

- [x] 更新地图指南、观察边界、README、文件协议及安装版本，写清未验证范围和样本位置。
- [x] 按 requesting-code-review 进行一次独立审阅，修正问题并按需重验。
- [x] 安装备份新版 Mod；交付时独立 Git add/commit，并请用户重启后采集正式对局 JSON。

## 审阅重点

- 飞鞋节点无连线但原生可选，且查看不会消耗次数。
- 未来幕、未揭晓问号、内部 Quests 和图形之外的数据不泄露；只将可见标记归一化。
- 地图初开动画或卡牌覆盖时不读到混合帧，人与工具交错操作不重开页面。
- 绘图模式、转场、结束房间及起点/Boss 的特殊可点击规则遵循原生界面。
- 当前幕变更时，节点 ID 和读取对象不跨幕串用。

## 实现依据与验证约束

- 选路候选读取已显示的原生节点状态与启用状态，不另行调用遗物 Hook 推导一份可能不同于 UI 的集合。飞鞋在地图重新打开时由原生 `RecalculateTravelability` 更新；连线始终来自原生已绘制路径。
- 战后点击奖励页“继续”会打开地图，底层奖励页仍在 `NOverlayStack` 中。`HideOverlays/ShowOverlays` 只隐藏/恢复页面，不弹出。地图允许单一原生奖励页存在，其他选择页或弹窗仍拒绝；关闭时核对原有底层页实例。
- 原生地图关闭动画约 350ms，早于动画结束返回的“观察稳定 250ms”不足以确认关闭。当前先等待地图隐藏，再等待观察稳定；在全部异步区间监听重开，并在返回前复核 run、map、act 和页面。
- 地图在非战斗房间也能使用，覆盖卡牌页的识别不能依赖战斗专用观察判断。当前单独核对原生受支持卡牌 capstone，再由原生地图按钮切换。
- 测试入口使用独立用户数据与 IPC。调试入战绕过正常入场步骤，因此仅在 `--check-map` 夹具中补齐起点、地图标记、幕内层数和禁用选路开关。战后用 `CreatureCmd.Kill`、显式 `CheckWinCondition` 与原生奖励页继续完成结算，不通过出牌或结束回合触发。
- 第一局教程的房间集合有意没有先古之民。双 Boss/先古之民与第二幕的隔离夹具先使用独立 RNG 生成普通房间并预载资源；这些样本是可控原生场景，不是正式对局的未来地图。
- 独立审阅发现的非战斗卡牌覆盖、已揭晓问号验证和关闭最终等待窗口问题已修正；差异复核未发现剩余 Critical/Important/Minor。

## 验证结果与样本

最终构建零警告、零错误；Python 完整回归 92 项通过（18.315s），其中新增地图投影用例已观察到旧实现丢字段的失败，再修正通过。中文图形独立实例运行 `verify_map.py --exercise-cases`，30 项原生检查全通过；最终 `.tmp/roundtrip/stdout.log` 没有 `ERROR` 或异常条目。普通打开/重复/关闭前后玩法观察一致；扩展夹具会自行结束隔离战斗、取得遗物并切换幕，不应将夹具进度描述为完全不变。正式 Steam 对局未操作。

证据保留于不纳入 Git 的 `.tmp/roundtrip/map-checks.json`、`.tmp/roundtrip/map/map-evidence.json`。地图 JSON 位于 `.tmp/roundtrip/map/`：

- `map-inspection.json`、`map-combat.json`：整张战斗地图，候选为空。
- `map-connected.json`、`map-winged-boots.json`、`map-boots-exhausted.json`：原生连线候选、飞鞋额外候选及耗尽回归。
- `map-revealed-question.json`：已走问号的原生揭晓图标。
- `map-from-noncombat-deck.json`：非战斗牌组页切回地图。
- `map-double-boss.json`：普通先古之民起点及两个串联 Boss。
- `map-act-2.json`：切换第二幕后仅返回第二幕节点和 ID。

截图为 `.tmp/roundtrip/map-{combat,winged-boots,double-boss}.png`。本轮未接入地图 MCP、未实现选路动作、未验证正式游戏重启；其他版本、社区 Mod 自定义节点和全部先古之民组合不在本次验证范围。

已安装文件与本次最终构建一致，SHA-256：DLL 为 `582501f6618613a2b7579c011169a1a33197fba25fa85faf592dbc4aad1d6477`，清单为 `b2a7f79cf3e8b10f7a0c673978195fd50769360c7e9b52c5ac863b03d994e1a2`。独立测试窗口已停止，正式对局尚未重启。
