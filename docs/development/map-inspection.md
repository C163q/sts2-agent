# 当前幕地图查看

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。scene/screen 遵循[统一上下文](observation.md#场景上下文)，展开地图时仅 screen.view 为 map，scene 保留当前房间或战斗场景；原生房间为 MapRoom 时使用 scene:map（如换幕入口），不是根据地图是否展开来改名。

文件接口仍提供无参数 `inspect_map` 和 `close_map`；MCP 的 `inspect_map` 支持以下参数；`close_map` 只接受通用 preset。当前工具目录见 [MCP 指南](mcp.md)。

`inspect_map` 真实打开或复用原生地图，默认返回当前幕中可通过滚动浏览的整个地图，不自动滚动，也不读取其他幕。正常一局的三幕通过从 1 开始的 `act` 区分；地图行号不是顶栏的全局楼层。页面保留到显式关闭或人手动返回。

## 返回范围参数

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `"default"` | `default` 保留全图内容并省略普通空值；`full` 保留原有空值；`summary` 按类型仅列节点 ID；`selectable` 只返回当前可选节点及其详情 |
| `max_steps` | `0` | 非负整数，最大 `2147483647`；`0` 不裁剪，正数 N 返回沿实际有向连线最多走 N 步可达的子图 |

两个参数只影响返回数据，地图仍正常打开并保留。显式传入 `{"preset":"full","max_steps":0}` 与原有全图格式一致；省略参数使用[default](mcp.md#输出预设)，例如无当前节点时省略 current_node。只在 Python MCP 层裁剪，底层仍完整读取并校验当前地图，动作使用完整原生状态的令牌。

`preset: "summary"` 返回 `scene/screen/act/current_node/can_travel/selectable_nodes` 与 `nodes_by_type`；后者按原 `type` 将 ID 分组，每组从下到上、同行从左到右，空分类省略。无正文、名称、揭晓类型、任务标记、坐标、连线或 visited_path。问号仍归 unknown，细节使用 default/full。普通空值沿用 default 过滤。

summary 先按相同的 `max_steps` 规则裁剪再分类；当前节点为第 0 步，尚未进入节点时最低行是第 1 步。省略或 0 表示整幕，含过去节点和其他支路。正数增加 max_steps 标识；原生 selectable_nodes 不裁剪，因此飞鞋候选可能没有出现在分组中。分类不能说明节点能否依次经过。

`preset: "selectable"` 优先于 `max_steps`：保留 `scene`、`screen`、`act`、`current_node`、`can_travel`、`selectable_nodes`，增加 `preset: "selectable"`；`nodes` 只包含候选节点的 ID、坐标、图标类型及已显示的名称、揭晓类型或标记，不含 `next`，也不返回 `visited_path`。没有候选时 `can_travel: false` 且两个列表均为空，不附送不可选择的路线。即使深度被忽略，参数本身也必须合法。

`preset: "default"` 或 `"full"` 且 `max_steps > 0` 时：

- 当前节点算第 0 步，并保留所有最短连线路径长度不超过 N 的节点，涵盖分叉与汇合；按原地图顺序输出。
- 本幕尚未进入任何节点时，最低行的起点节点算第 1 步；不假定起点一定是先古之民。当前不能旅行时也可查看连线前瞻。
- `nodes[].next` 只保留子图内部连线，结果增加 `max_steps` 标识。边界的空 `next` 可能来自裁剪，不代表原图没有后续路线。
- `current_node`、完整 `visited_path` 及原生 `selectable_nodes` 保留全图上下文，这些 ID 可以位于子图之外。飞鞋提供的无连线候选不会被自动并入子图；需要比较它们时使用 `selectable`。不预测后续房间的特殊选路效果。

例如分别调用：

```json
{"preset":"selectable"}
```

```json
{"max_steps":3}
```

```json
{"preset":"selectable","max_steps":3}
```

最后一种调用与只传 `preset: "selectable"` 的结果一致。成功结果均可直接支持 `travel_to_node`；裁剪不授予额外可选节点，也不改变原生合法性检查。

## JSON 格式

以下是显式 `full` 的缩小结构示例，不代表任何实际对局：

```json
{
  "scene": "combat",
  "screen": {"status": "covered", "view": "map"},
  "act": 1,
  "current_node": "map:1:1:2",
  "visited_path": ["map:1:0:3", "map:1:1:2"],
  "can_travel": false,
  "selectable_nodes": [],
  "nodes": [
    {"id": "map:1:0:3", "row": 0, "column": 3, "type": "ancient", "name": "Neow", "next": ["map:1:1:2"]},
    {"id": "map:1:1:2", "row": 1, "column": 2, "type": "monster", "next": ["map:1:2:1", "map:1:2:3"]},
    {"id": "map:1:2:1", "row": 2, "column": 1, "type": "unknown", "next": ["map:1:3:3"]},
    {"id": "map:1:2:3", "row": 2, "column": 3, "type": "rest_site", "next": ["map:1:3:3"]},
    {"id": "map:1:3:3", "row": 3, "column": 3, "type": "boss", "next": []}
  ]
}
```

| 字段 | 含义 |
| --- | --- |
| `current_node` | 当前节点；尚未进入节点时为 `null` |
| `visited_path` | 当前幕已走路线的节点 ID，按进入顺序排列 |
| `can_travel` | 当前原生界面是否存在可以选择的节点 |
| `selectable_nodes` | 当前真正允许选择的节点 ID；战斗未结束时为空 |
| `nodes[].id` | 当前对局、当前幕内按地图坐标稳定的定位 ID；不能跨对局使用 |
| `row/column` | 从 0 开始，分别从下到上、从左到右；不输出随机像素抖动 |
| `type` | 按图标提供 `ancient/boss/monster/elite/shop/treasure/rest_site/unknown`，无法识别为 `unrecognized` |
| `next` | 此节点实际绘制的有向连线终点 ID；不表示现在可点击 |
| `name` | 可按外观识别的先古之民或 Boss 英语名称；普通敌人节点不附送具体敌人 |
| `revealed_type` | 仅原生问号图标已揭晓为具体房间类型时提供，保留 `type: unknown` 表示问号来源 |
| `marked` | 仅原生节点显示额外任务标记时提供 `true`，不读取内部任务正文 |

同一层的节点和 `next` 按从左到右排列，整体按从下到上排列。双 Boss 使用两个 Boss 节点及第一 Boss 到第二 Boss 的实际连线，不固定 Boss 数量；教程起点按实际图标处理，不强制为先古之民。

## 选路与信息边界

候选读取原生地图当前的选路开关、节点状态和启用状态，遵循原生遗物 Hook。飞鞋（`WingedBoots`）有剩余次数时，`selectable_nodes` 可以包含不在当前节点 `next` 中的下一排节点；`next` 保持原地图连线。次数耗尽后按原生规则回归。起点、Boss 和第二 Boss 的特殊处理也沿用原生界面。

战斗中不提前开放下一节点；绘图模式返回空候选。候选可供 `travel_to_node` 使用；查看本身不会点击地图节点、消耗飞鞋或进入房间。

只读取当前幕原生节点、可见图标及已绘制连线。未走过的问号不揭晓；普通敌人、精英、宝箱和商人节点不附送具体敌人、物品或库存。不读取随机种子、下一幕地图、未来随机结果、悬停历史或内部任务正文。自定义绘图的笔迹不转换为路线；图例和绘图工具的悬停说明留待后续扩展。

## 地图选路

`travel_to_node({"node_id":"map:1:2:3"})` 只接受当前已展开地图允许的节点。旅行真实离开当前房间，放弃未领取奖励；工具不会自动领取奖励、挑选路径或决定后续输入。飞鞋的合法路线与次数由原生 Hook 决定，不能只按 `next` 判断合法性。

基础观察在地图已就绪、暴露时返回整幕分类。get_observation 的 full/default/summary 共用这一地图表达；full 保留普通 null，default/summary 省略。基础观察不接受 max_steps，也不继承上次详情的筛选；只有 inspect_map.default/full 返回连接关系与节点详情。

以下为基础观察的地图及 note 片段，不是完整对局样本：

```json
{
  "map": {
    "status":"visible","act":1,"current_node":"map:1:1:2",
    "can_travel":true,"selectable_nodes":["map:1:2:1","map:1:2:3"],
    "nodes_by_type":{"monster":["map:1:1:2"],"unknown":["map:1:2:1"],"rest_site":["map:1:2:3"]}
  },
  "notes":{"map":"Map connections omitted; use inspect_map for details."}
}
```

外层 `scene` 保留房间类型，`screen:{status:covered,view:map}` 表示下层被覆盖。地图关闭、被牌组等更高层覆盖或尚不可读时，map 为 null，按通用预设处理，且没有 notes.map；actions_only/top_bar 不返回地图或这条 note。顶栏独立遵循原有规则。旧原生 schema 的五字段地图仍可兼容读取，不虚构缺失的分类。

`inspect_map` 成功后可直接按 `selectable_nodes` 调用 `travel_to_node`，无需额外基础观察。普通房间 `proceed` 的成功回执列出旅行工具时，按需使用 `get_observation` 或 `inspect_map` 读取节点。`travel_to_node` 返回[精简动作回执](mcp.md#动作返回格式)：下一房间普通操作通常为 action_completed，战斗为 player_ready，入场选牌为 choice_required，未知界面为 manual_input_required。父入场任务等待玩家选择时不会死等；卡牌选择仍使用原有工具。失败或不完整结果须重新观察，不自动重试。

节点 ID 只能用于当前对局、当前幕的当前地图；动作令牌还校验地图身份、候选和页面状态。错误 ID 格式在 UI 操作前拒绝，旧令牌返回 stale_state，非候选、关闭/被覆盖的地图等返回 illegal_action。目标被滚动到屏幕外时，工具先通过原生滚动露出目标再点击；不直接调用进入房间 API。

### Boss 与跨幕

`proceed` 保留原生奖励页行为：普通战后打开地图；双 Boss 的第一个 Boss 战后打开只有第二个 Boss 可选的地图；每幕最后一个 Boss 战后直接进入下一幕地图。跨幕等待原生任务与地图动画完成，再提供新幕候选，不把尚在入场的地图误判为未知页面。第三幕后进入建筑师时返回已就绪的当前对话，后续用[终章与结算工具](run-ending.md)推进至主菜单。

## 页面与失败语义

地图与卡牌浏览页分别管理。`inspect_map` 在卡牌页之上调用时，使用原生顶栏地图按钮，先关闭卡牌页，再打开或露出地图。`close_map` 只在地图当前位于最上层且原生返回按钮可用时执行，不穿透上层牌组页。关闭卡牌页继续用 [`close_card_view`](deck-inspection.md)，不会顺带关闭地图。

仅支持单人进行中的对局；候选选择页、弹窗、其他详情、过渡和正在移动期间拒绝。受支持选择先切至战场后允许打开地图。允许原生奖励页在地图底下保留，这是战后正常选路流程；关闭地图会露出原有奖励页。也支持[占卜棋盘](divination.md)在地图底下保留，覆盖时不返回棋盘内容与图像，关闭后可重新观察并继续。首次打开要求原生地图入口可见且启用，战斗中还须处于可行动阶段。当前幕起点等原生禁止返回的地图不能强行关闭。错误参数在 UI 操作前返回 `invalid_request`；页面或对局在异步等待期间变化返回 `illegal_action`，不自动重开页面。超时或异常不能自动重试。

Godot 主线程发起操作，使用异步帧等待，遵循原生暂停/恢复与动画。底层文件接口关闭后保留完整基础观察。MCP 的 close_map 在完整校验后仅返回 actions_only 内容：scene/screen、available_actions，以及适用的 selection.type/status；仍只接受 default/full，不新增 summary，不返回 transition 或占卜 PNG。需要当前战斗、房间或棋盘图像时按需使用 get_observation 或相应详情工具。工具 UI 操作使旧动作令牌失效；MCP 使用成功结果的新令牌继续操作，仍校验当前页面与动作合法性。

MCP 在 IPC 前校验查看参数；`close_map` 除通用 preset 外拒绝全部额外参数，查看工具也拒绝未知字段。参数错误保留此前有效权限。合法查看与关闭请求在发送前清除旧令牌，成功后保存返回状态的新令牌。inspect_map／close_map 的点击前明确拒绝带有未交互保证时恢复已有令牌，允许直接改用合法操作；没有初始令牌不会创建许可。点击后变化、超时、异常或矛盾执行证据不恢复。关闭原因区分无对局、地图未打开、被卡牌页覆盖、过渡／动画未就绪、原生返回按钮禁用或不可见；available_actions 与执行校验使用同一判定入口。地图投影校验当前幕节点 ID、坐标、唯一引用、已走路径与候选布尔状态，逐层过滤附加字段；不会要求可选节点必须在 `next` 中。格式错误返回 `transport_error`。关闭结果若仍指向浏览页，同样拒绝。

## 调用与验证

游戏已加载新版 Mod 并配置文件通信目录后，在仓库根目录分别执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_map
```

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc close_map
```

端到端脚本为 `tests/game/verifiers/verify_map.py`；`--exercise-cases` 仅允许 `.tmp/roundtrip/ipc`，需启动时启用 `--check-map`。它会在一次性隔离夹具中完成敌人死亡、原生奖励页继续、飞鞋获取与耗尽、双 Boss 和跨幕等场景，不可对正式游戏启用测试标志。

正式游戏的只读地图采样及原生 API 依据见[地图设计与实施记录](../research/2026-10-29-map-inspection.md)；真实 stdio 历史验证见[地图 MCP 记录](../research/2026-10-29-mcp-map-inspection.md)。在已就绪且可关闭地图的单人战斗中，可以执行只查看／关闭、不选路或结束回合的检查：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_mcp_map --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-map
```

输出目录使用新路径；脚本会真实打开和关闭地图。隔离测试使用 [close_map 套件](../../tests/game/data/gui_suite_close_map_review.json)，其中 combat 先准备真实可关闭地图的战斗，再串行运行独立验证器。当前关闭契约、样本及验证边界见[关闭结果交付](../research/2026-11-05-close-map-results-implementation.md)。

选路与跨幕的目标版本源码证据、图形验证及未验证范围见[选路验证记录](../research/2026-10-31-map-travel-validation.md)。

返回预设与子图的边界用例和隔离图形证据见[地图预设验证记录](../research/2026-11-01-map-presets.md)。

地图分类、基础观察与明确拒绝恢复的实现及验证见[地图摘要交付](../research/2026-11-05-map-summary-implementation.md)。
