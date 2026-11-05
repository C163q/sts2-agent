# inspect_map 开发核验依据

> 当前状态：源码核验与摘要候选记录完成，工具仍处于设计讨论。尚未实施修复或新预设，也未新增游戏采样。本记录仅对下述基线负责。

供用户讨论的表现、问题和方案见[审阅记录](2026-11-05-inspect-map-review.md)；这里记录实现位置和验证边界。

## 基线

- 项目提交 `14ebc4c`，Mod `0.67.0`、MCP `0.69.0`、schema `40`。
- Linux 游戏 `v0.107.1`、release 构建 `59260271`；RitsuLib `0.6.10`。
- 重新计算安装目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 沿用同一程序集基线的本地反编译证据：`.tmp/decompiled/NMapScreen.cs` 的 `SetMap`、`DrawPaths`、`RecalculateTravelability`、`TravelToMapCoord`；`.tmp/decompiled/NNormalMapPoint.cs` 的 `UpdateIcon`。既有来源记录见[选路核对](2026-10-31-map-travel-validation.md#目标版本与源码证据)。没有重新反编译或调用新增游戏 API。

## 当前链路

| 职责 | 当前实现 |
| --- | --- |
| 原生打开、等待、关闭监听与快照 | [GameAdapter.Views.cs](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs) 的 `InspectMap` |
| 是否提供工具 | [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs) 的 `CanInspectMap` |
| 页面可读、动画就绪与覆盖 | [MapView.cs](../../src/Sts2Agent/Observation/MapView.cs) |
| 节点、原生候选与实际绘制连线 | [MapInspection.cs](../../src/Sts2Agent/Observation/MapInspection.cs) 的 `Read`、`Choices` |
| MCP 参数、完整校验与子图／selectable 投影 | [map_details.py](../../src/sts2_mcp/output/map_details.py) |
| 对外工具及执行策略 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py) 的 `inspect_map` |
| 错误保留许可与安全原因投影 | [game_session.py](../../src/sts2_mcp/game_session.py)、[error_output.py](../../src/sts2_mcp/output/error_output.py) |
| 基础观察的地图占位 | `MapInspection.Summary`、[contracts/map.py](../../src/sts2_mcp/output/contracts/map.py)、[observation_presets.py](../../src/sts2_mcp/output/observation_presets.py) 的 `browsing_summary` |

节点、连线和原生候选使用 `VisibleUi.Shown`，未使用视口裁剪。实际点击的地图入口仍要求 `OnScreen`，这是交互前提，与批量读取地图范围不同。

当前基础观察的地图只有 `status/act/current_node/can_travel/selectable_nodes`，无节点详情和已走路线。`browsing_summary` 对地图继续复用 default；没有已经实现的整图 summary 可以直接接入。

## 已确认问题

### MAP-01：明确未交互的拒绝不能保留已有许可

优先级：中；状态：待修复，仅源码确认。

`InspectMap` 在没有对局或 `CanInspectMap` 为 false 时直接返回 `FileMailbox.Error`，没有 `ui_unchanged:true`。注册项是 `effect:view`，也没有启用 `unchanged_view_rejections`。`GameSession` 发出请求前清除旧许可，拒绝后无法依据明确未交互保证恢复。与已经审阅的 `inspect_deck`、`inspect_pile`、`set_selection_view` 不一致。

预期修复范围为入口校验、显式未交互保证和已有共用恢复策略的接入；不得把点击后的失败、超时或地图替换一并恢复。

### MAP-02：原因过于笼统，内部原因没有作为公开错误输出

优先级：中；状态：待修复，仅源码确认。

`CanInspectMap` 仅返回布尔值；`InspectMap` 入口拒绝统一写成 `Map viewing is unavailable in the current screen.`。其余按钮不可用、读取中地图变化的错误也经 `FileMailbox.Error` 返回，没有固定的 `public_message`。`error_output.error_result` 因而回落为 `The requested action is unavailable.`。

建议引入共用的地图查看不可用原因入口，分别服务 available_actions 与执行前校验；可公开原因限于固定界面判断，不透出异常、内部对象或隐藏数据。

这两项可在现有适配器与 MapView 范围内完成小范围重构。未发现需要先进行全项目重构的依据。

## 结构与边界核对

| 分支 | 已核对事实 | 新增游戏验证 |
| --- | --- | --- |
| 正常打开或复用 | 原生地图按钮；同一地图与幕就绪后返回全图；不点击节点 | 无 |
| 牌组／牌堆覆盖 | 允许原生地图按钮替换受支持卡牌页 | 无 |
| 候选页／战场查看 | 普通候选页阻止打开；允许已切至战场的受支持选择覆盖；不因存在选择就一概拒绝 | 无 |
| 战斗禁行、绘图、过渡 | `Choices` 核对原生旅行开关、绘图模式和动画；无候选不等于无连线 | 无 |
| 飞鞋 | 候选按原生 Travelable 状态，不按 `next` 重新推测 | 无 |
| 幕起点 | `current_node:null`；深度 1 取最低行，default 省略当前点空值 | 无 |
| 双 Boss | 读取两个实际 Boss 节点及绘制连线，不固定终点数量 | 无 |
| 问号与任务标记 | 仅图标已揭晓才增加 `revealed_type`，已显示任务图标才增加 `marked:true` | 无 |
| 深度边界 | 最短有向连线距离；裁剪边界的 `next:[]` 不等于原图终点；原候选和已走路径不裁剪 | 无 |
| 格式损坏 | 先校验完整原生图，再投影；裁掉的分支也不能绕过校验 | 无 |

相关既有测试入口为 `tests/python/test_map_presets.py`、`tests/python/test_mcp_map.py`、`tests/game/verifiers/verify_map_presets.py` 和 `MapInspectionChecks.cs`。历史[预设验证](2026-11-01-map-presets.md)覆盖飞鞋、正常进入战斗后禁行、幕起点与双 Boss，但其版本和 scene/screen 属历史基线，不能当作当前新采样；本阶段没有重跑这些测试。

## 路线段候选的实现约束

若采用路线段表示，仍从同一次完整地图快照投影，不新增原生状态推测。当前节点、可选节点和分叉／汇合点应作为段的端点；无分叉、无汇合的中间节点保留类型与 ID，仅连线表达改为连续序列。每条原始边必须可由相邻 ID 恢复，每个节点仍有且只有一份详情；孤立节点和原图终点也不能丢失。

先裁剪再分段时，需要明确标识裁剪边界；原生候选落在子图外、地图自定义连线或环、无边单点均需在定稿中约定，不能用通常地图形状代替校验。压缩是否有效须比较真实地图，不预先宣称 token 或阅读成本一定下降。

`full/default` 的兼容范围、summary 的确切字段与基础观察接入尚未确认。当前候选不是实施规格，不授权提前修改行为。

## 示例与检查范围

[basic.full.json](2026-11-05-inspect-map-examples/basic.full.json) 是根据当前字段和校验整理的结构样例，调用参数为 `{"preset":"full"}`。它不来自真实 MCP 调用；未提供截图或冒充完整对局地图。检查 JSON 语法、当前完整地图校验、候选投影与深度裁剪，以及文档链接；不因此核销该工具。
