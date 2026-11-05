# close_map 核验与返回格式建议

> 当前状态：设计已确认，实施中。完整校验、最小成功结果、具体拒绝与未交互恢复已接入；约定验证已完成，等待独立审查及合入，尚未核销。[实施记录](2026-11-05-close-map-results-implementation.md)跟踪结果。下方现状与样本保留审阅基线，不能当作修复后输出。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)，源码、测试和版本证据见[开发核验](2026-11-05-close-map-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 点击前明确拒绝仍丢失已有许可 | 中：地图本来没开、被牌组覆盖或强制地图不能返回时，模型连其他合法操作也需要先重新观察 | 未交互且已有许可时保留；状态变化、已点击或结果不明仍须观察 | 已修复并完成约定验证 |
| 错误没有给出具体原因 | 中：没有地图、地图被覆盖、返回按钮禁用、动画未完成都只显示“请求的操作不可用” | 提供固定、具体的原因；可用操作列表与执行前检查使用同一入口 | 已修复并完成约定验证 |
| 成功结果不是完整基础观察，且校验存在缺口 | 中：普通页面省略房间内容和选牌状态；有损坏的房间内容时也可能被当作有效成功 | 先完整校验原生观察，再按约定返回精简上下文，保留选择 type/status | 已修复并完成约定验证 |
| 旧独立验证器已过时 | 低：仍固定 42 个玩法工具，还要求关闭返回等同于完整基础观察，不能直接验证当前版本 | 随定稿同步修正旧断言，保留其验证目标 | 已更新并在真实 GUI 运行 |

第三项包含两个实际表现：关闭地图后，选牌仍在等待，但返回里没有 selection.type/status；回到选牌界面的文字 note 仍存在；普通房间的缺失／损坏内容也没有经过基础观察的完整校验。它们来自同一旧返回投影，建议一起处理。

## 审阅基线的参数与关闭规则

- 只接受通用 `preset:default/full`，默认 default；无 summary、force 或其他关闭参数。
- 只能关闭最上层、已就绪且原生返回按钮可见并启用的地图。
- 上层牌组存在时不能穿透关闭地图，应先 close_card_view。原生 MapRoom 的换幕起点等强制地图不能关闭。
- 原生返回按钮负责关闭、退场动画和恢复战斗。成功刷新已有操作所用的当前状态，不要求首次先调用 get_observation；不执行旅行，不记录 transition。
- 本地参数错误保留已有许可；当前原生拒绝会丢失许可，不能将这个现状写成修复后规则。

## 已确认返回契约

与 close_card_view、set_selection_view 一样，成功只返回 actions_only 的内容，仍保留 default/full 两个参数值，不新增 summary 或 actions_only 参数：

```json
{
  "scene": "combat",
  "screen": {
    "status": "visible"
  },
  "available_actions": [
    "inspect_hand",
    "inspect_ui",
    "inspect_combatants",
    "inspect_potions",
    "inspect_relics",
    "inspect_deck",
    "inspect_pile",
    "inspect_map",
    "set_selection_view"
  ],
  "selection": {
    "type": "combat_pile",
    "status": "battlefield"
  }
}
```

这是从同场景真实基础观察整理的候选输出，不是当前 close_map 返回。没有待处理选择时省略 selection。需要战斗、房间内容或占卜图像时，再使用 get_observation 或相应详情工具。

其余可选做法是保留现在的普通／特殊页面差异，或改为所有页面完整基础观察。前者延续遗漏和额外判断，后者会让关闭操作附送大量主体内容；目前其他关闭／切换页面工具已有精简输出，因此共用现有最小返回。

无论选择哪一种，原生完整响应都必须先校验成功；不能通过少返回字段来跳过格式损坏。底层文件接口仍可保留完整状态。

## 修复后典型 JSON

[9 份真实完整返回](2026-11-05-close-map-fixed-examples/README.md)包含普通／占卜／待选牌成功、default/full 及无初始许可／可恢复／覆盖／强制地图拒绝。实现与验证范围见[实施记录](2026-11-05-close-map-results-implementation.md)。

## 审阅基线的典型 JSON

全部示例统一调用 `close_map({"preset":"full"})`，保持当前完整 JSON 与 null，另有一份同场景显式 get_observation 的对照；[样例目录及来源](2026-11-05-close-map-examples/README.md)。

| 场景 | 当前返回 | 完整 JSON |
| --- | --- | --- |
| 普通战斗地图关闭 | scene/screen、战斗与顶栏、操作列表，未带完整基础观察的其他字段 | [combat.full.json](2026-11-05-close-map-examples/combat.full.json) |
| 事件地图关闭 | scene:event，但没有 event 主体 | [event.full.json](2026-11-05-close-map-examples/event.full.json) |
| 待选牌战场的地图关闭 | 仍有 notes.selection，没有 selection.type/status；原生选择没有被取消 | [selection.full.json](2026-11-05-close-map-examples/selection.full.json)、[随后基础观察](2026-11-05-close-map-examples/selection-observation.full.json) |
| 占卜地图关闭 | 完整观察、divination 与说明，另有 1 个 PNG 图像块 | [divination.full.json](2026-11-05-close-map-examples/divination.full.json) |
| 地图未打开／被牌组覆盖／换幕强制地图 | 对外错误 JSON 相同，均没有具体原因，并要求重新观察 | [rejected.full.json](2026-11-05-close-map-examples/rejected.full.json) |

六类实测包括：未打开地图、正常战斗、事件、待选牌地图叠加牌组、第一幕 Boss 后第二幕入口、占卜。前三类在首批完成，后三类在补跑完成；不是单次套件无失败通过。占卜 PNG 不属于 JSON，本阶段仅在证据中记录内容块计数。

## 本阶段边界

未修改正式安装，不新增 TODO，也不提前核销。多人、第三方地图、任意并发人工切页与所有房间组合不作穷举；中途地图变化和重开另核对源码分支。实施按已确认契约推进，修复后样本另行保存。
