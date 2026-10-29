# 当前幕地图查看

Mod 0.12.0 的文件接口提供无参数 `inspect_map` 和 `close_map`。本轮尚未接入 MCP，MCP 仍保留已有的 10 个工具。

`inspect_map` 真实打开或复用原生地图，返回当前幕中可通过滚动浏览的整个地图，不自动滚动，也不读取其他幕。正常一局的三幕通过从 1 开始的 `act` 区分；地图行号不是顶栏的全局楼层。页面保留到显式关闭或人手动返回。

## JSON 格式

以下是缩小的结构示例，不代表任何实际对局：

```json
{
  "scene": "map",
  "screen": {"status": "visible", "view": "map"},
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

战斗中不提前开放下一节点；绘图模式返回空候选。这里只提供当前游戏界面的候选，不代表项目已实现选路工具；查看不会点击地图节点、消耗飞鞋或进入房间。

只读取当前幕原生节点、可见图标及已绘制连线。未走过的问号不揭晓；普通敌人、精英、宝箱和商人节点不附送具体敌人、物品或库存。不读取随机种子、下一幕地图、未来随机结果、悬停历史或内部任务正文。自定义绘图的笔迹不转换为路线；图例和绘图工具的悬停说明留待后续扩展。

## 页面与失败语义

地图与卡牌浏览页分别管理。`inspect_map` 在卡牌页之上调用时，使用原生顶栏地图按钮，先关闭卡牌页，再打开或露出地图。`close_map` 只在地图当前位于最上层且原生返回按钮可用时执行，不穿透上层牌组页。关闭卡牌页继续用 [`close_card_view`](deck-inspection.md)，不会顺带关闭地图。

仅支持单人进行中的对局；选牌、弹窗、其他详情、过渡和正在移动期间拒绝。允许原生奖励页在地图底下保留，这是战后正常选路流程；关闭地图会露出原有奖励页。首次打开要求原生地图入口可见且启用，战斗中还须处于可行动阶段。当前幕起点等原生禁止返回的地图不能强行关闭。错误参数在 UI 操作前返回 `invalid_request`；页面或对局在异步等待期间变化返回 `illegal_action`，不自动重开页面。超时或异常不能自动重试。

Godot 主线程发起操作，使用异步帧等待，遵循原生暂停/恢复与动画。关闭等待地图退场后才返回基础观察。工具 UI 操作使旧动作令牌失效；执行战斗动作前须重新观察。

## 调用与验证

游戏已加载新版 Mod 并配置文件通信目录后，在仓库根目录分别执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_map
```

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc close_map
```

端到端脚本为 `scripts/verify_map.py`；`--exercise-cases` 仅允许 `.tmp/roundtrip/ipc`，需启动时启用 `--check-map`。它会在一次性隔离夹具中完成敌人死亡、原生奖励页继续、飞鞋获取与耗尽、双 Boss 和跨幕等场景，不可对正式游戏启用测试标志。

Mod 0.12.0 已在正式 Steam 单人战斗中重启验证：第一幕 64 个节点、76 条连线，Boss 为 Ceremonial Beast；战斗中候选为空，重复读取一致，显式关闭后战斗观察不变。正式样本为 `.tmp/live/map/map-inspection.json`，请求证据为同目录 `map-evidence.json`。飞鞋、双 Boss、跨幕和战后候选仍以独立夹具的验证为准。实施证据见 [地图设计与实施记录](../research/2026-10-29-map-inspection.md)。
