# inspect_map 核验与摘要候选

> 当前状态：定稿已确认，实施中。inspect_map.summary 已确定采用节点类型分组，仅列节点 ID，省略连接关系及节点详情，max_steps 继续生效；get_observation 的 full/default/summary 均采用这一地图表达，并注明连接关系已省略、详情使用 inspect_map。具体字段与边界采用下文约定；两项修复、摘要和基础观察接入已完成约定验证，等待终审与合入，验证结果见[实施记录](2026-11-05-map-summary-implementation.md)。本项未核销。暂无阻塞。

总流程见[工具核验清单](2026-11-02-mcp-tool-review.md)，实现证据与未验证范围见[开发核验](2026-11-05-inspect-map-development-notes.md)。

## 优先处理的问题

以下两项已修复并完成拒绝直接续接及相关回归，详见[实施记录](2026-11-05-map-summary-implementation.md)。它们独立于 summary 的表达方案。

| 问题 | 影响 | 建议 |
| --- | --- | --- |
| 查看地图被拒绝后，需要再次观察才能操作 | 即使在点击前就确认地图不可打开，原有操作许可仍会丢失 | 沿用已审阅查看工具的规则：明确保证未操作界面的拒绝保留已有许可；已经点击、结果不明或状态变化时重新观察 |
| 错误没有说明具体原因 | MCP 只返回通用的“请求的操作不可用”，无法区分没有对局、页面覆盖、入口禁用或正在过渡等原因 | 核对各分支后返回固定、具体的原因和恢复建议；界面是否提供该工具与实际拒绝使用同一判断入口 |

## 审阅基线能力与典型返回

本节保留审阅基线 `14ebc4c` 的现状；现行接口见[地图指南](../development/map-inspection.md)。

- `preset` 支持 `default`、`full`、`selectable`；默认 `default`。`summary` 尚不存在。
- 默认返回当前幕可滚动浏览的整个地图。节点和连线读取没有按当前视口裁剪；真正隐藏、透明或未绘制的内容仍不读取。
- `max_steps: N` 沿实际连线裁剪当前点之后最多 N 步的子图，`0` 不裁剪；`selectable` 优先于该参数，只返回当前候选的详情。
- `selectable_nodes` 是原生界面当前允许前往的节点，`next` 是地图连线。飞鞋可能让二者不同，不能互相替代。
- 节点保留类型、可识别的先古之民／Boss 名称、问号已经显示的揭晓类型，以及任务图标标记；不提供未揭晓问号的内容或未来房间详情。
- 打开地图会保留页面；从牌组／牌堆调用时，原生地图按钮会替换卡牌浏览页。成功后可以直接选择当前合法节点。

调用 `inspect_map({"preset":"full"})` 的[完整结构示例](2026-11-05-inspect-map-examples/basic.full.json)依据当前实现整理，采用五个节点表示起点、分叉和汇合。它不是实际对局采样，也不表示真实地图只有五个节点。其他已识别分支及既有实测的适用边界见开发核验。

## summary 已确认方向

- 按节点类型分组，每组只返回节点 ID；不表达连接关系。
- 不返回 Boss／先古之民名称、问号已揭晓类型和任务标记，不增加额外详情对照；这些信息按需使用 default/full 查看。
- `max_steps` 继续生效，保留其原有范围含义，不以省略连接信息为由改成按行数截取。

## 输出定稿

使用 `nodes_by_type` 容纳分类，保留 `scene`、`screen`、`act`、`current_node`、`can_travel`、`selectable_nodes`；省略 `visited_path`、逐节点坐标、`next` 及所有节点详情。`current_node` 的空值沿用 default 过滤规则。

以下是基于同一个五节点 full 结构整理的摘要草案，参数为 `{"preset":"summary","max_steps":1}`。不是实际调用结果，实施后的真实样本另见交付记录：

```json
{
  "scene": "rewards",
  "screen": {"status": "covered", "view": "map"},
  "act": 1,
  "current_node": "map:1:1:2",
  "can_travel": true,
  "selectable_nodes": ["map:1:2:1", "map:1:2:3"],
  "max_steps": 1,
  "nodes_by_type": {
    "monster": ["map:1:1:2"],
    "unknown": ["map:1:2:1"],
    "rest_site": ["map:1:2:3"]
  }
}
```

分类列表用于寻找关心的节点；节点是否可以立即前往仍由 `selectable_nodes` 表示。没有连接关系，因此不能仅凭分类列表确定这些节点能否依次经过。

采用以下边界：

- 先按现有 max_steps 裁剪，再分组。当前节点算第 0 步，因此仍会出现在分类中；正数 N 包含 0 至 N 步内节点。本幕未进入节点时，最低行算第 1 步；`0` 保留整幕节点，包括过去节点和其他支路。
- 每组沿用原来的从下到上、同行从左到右顺序；空分类省略。没有任何分类条目时返回 `nodes_by_type:{}`。
- 按现有 `type` 分组，保留 `unknown`、`unrecognized`，不推断问号内容。已有 `type:unknown, revealed_type:monster` 的节点仍列入 unknown；省略的揭晓详情通过 default/full 查看。
- `selectable_nodes` 保留原生候选，即使飞鞋候选不在 max_steps 连线子图中，也不删掉或擅自加入分类范围；它仍可以用于合法旅行。需要候选详情时使用 selectable。
- `max_steps>0` 时保留现有输出中的 max_steps，`0` 时不增加该字段。`full/default/selectable` 保持原有含义。

## 基础观察的地图契约

已确认：地图展开时，`get_observation` 的 full/default/summary 在 `map` 内均采用 inspect_map.summary 的类型分组策略，不返回连接关系或节点详情，并附带 note 指向 inspect_map。

具体装配规则如下：

- `map` 保留 `status/act/current_node/can_travel/selectable_nodes`，增加 `nodes_by_type`，不重复放入外层的 scene/screen。三种预设的分类内容相同，普通空值仍遵循各自通用规则。
- 基础观察不新增 max_steps 参数，使用不裁剪的整幕范围，即 inspect_map 的 max_steps:0。之前的 inspect_map 调用所用预设、深度不会影响下一次基础观察。
- note 放在外层 `notes.map`，文字为 `Map connections omitted; use inspect_map for details.`，仅在实际返回地图内容时加入，并与其他适用 notes 合并。
- `actions_only/top_bar` 沿用现有用途，不增加地图主体或这条 note。
- 基础观察只读取已展开且未被更高层覆盖的地图，不主动打开地图。地图关闭、被牌组等页面盖住或无法读取时，沿用现有 map 空值和通用过滤规则，也不附这条 note。
- 顶栏、场景、可用操作和其他主体继续遵循各自预设，统一仅针对地图部分。

以下为同一五节点示例在基础观察中的地图及 note 片段，不是完整 get_observation 返回，也不是实际采样：

```json
{
  "map": {
    "status": "visible",
    "act": 1,
    "current_node": "map:1:1:2",
    "can_travel": true,
    "selectable_nodes": ["map:1:2:1", "map:1:2:3"],
    "nodes_by_type": {
      "ancient": ["map:1:0:3"],
      "monster": ["map:1:1:2"],
      "unknown": ["map:1:2:1"],
      "rest_site": ["map:1:2:3"],
      "boss": ["map:1:3:3"]
    }
  },
  "notes": {
    "map": "Map connections omitted; use inspect_map for details."
  }
}
```

## 跨幕场景补充

第一幕 Boss 后 proceed 紧接观察的 unrecognized 已复现并定位为原生 MapRoom 未识别，已确认补 scene:map；普通房间的地图覆盖仍保持原 scene。修复及最终验证见[专题记录](2026-11-05-act-entry-scene.md)。

## 定稿与实施边界

- inspect_map 及基础观察的字段、上下文与分组边界以上文为准。
- 地图分类与基础观察复用读取和分类入口；不以调用会打开页面的 inspect_map 来实现基础观察。两项正确性修复与预设接入的验证见实施记录，终审和合入后核销。
- 暂不增加自动推荐路线、隐藏问号预测或自动选路。

## 本阶段验证

仅进行代码、目标程序集哈希与文档／JSON 检查，未运行游戏、编译 Mod 或修改正式安装。没有据此声称所有地图分支已经游戏验证；后续实测随定稿范围安排。本阶段不修改 TODO、不增加工具核销数。
