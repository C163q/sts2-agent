# inspect_treasure 核验与参数建议

> 当前状态：现状核验完成，进入设计讨论。59 项 Python、七类 GUI、102 次 MCP 及损坏响应探针已完成，提供 14 份完整返回。待确认修复与 summary 方案；尚未修改工具行为，本项尚未核销。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。源码、问题编号与具体证据见[开发核验](2026-11-06-inspect-treasure-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 证据与状态 |
| --- | --- | --- | --- |
| 拒绝原因笼统 | 中：没有宝箱房、被地图／牌组／选择／奖励页覆盖，都只返回“操作不可用”，无法据此判断如何继续 | 区分无宝箱、覆盖页、预览及过渡等原因；保留纯读取的已有许可恢复 | 实测确认，待讨论修复 |
| 矛盾的成功响应仍被接受 | 中：宝箱内容声称可见，但 screen 同时声称被地图覆盖、隐藏、未就绪或正在浏览牌组，仍可显示遗物正文并生成操作许可 | 核对详情与画面状态一致；损坏结果返回 transport_error 并清除许可 | 合成损坏响应确认；正常游戏中的覆盖读取会被拒绝，待讨论修复 |
| 未区分“显示但不可悬停”的遗物 | 低：当前会直接读取已显示遗物的正文，未核对鼠标或控制器是否还能显示其提示；与已审阅遗物工具的处理不同 | 保留图标静态数据，悬停不可用时省略正文并给 note，沿用已有公共规则 | 源码确认缺少检查；正常就绪场景未触发，未新增人工扰动验证，待讨论修复 |

这里**没有**明确读取拒绝后被迫重新观察的问题：有许可时返回 choose_legal_action，实测可直接继续结束回合、领取额外奖励、操作当前选牌或继续；首次读取失败仍需获得有效观察。

## 当前参数与内容

当前只有 preset:default/full，默认 default。它是纯读取，可作为首次查看；成功结果可支持下一步合法操作。

成功结果由 scene、screen 和 treasure 组成。详情工具的 available_actions 由 get_observation 提供，符合既有约定。

| 字段 | 当前含义 |
| --- | --- |
| treasure.status | 当前宝箱房是否显示；详情成功为 visible |
| chest | closed、opening、open；opening 是尚未完成开箱的瞬态 |
| relic | 当前已展示的单件遗物；包含 name、enabled、description、hover_tips |
| proceed | 当前 Skip／Proceed 的文本、启用状态及是否放弃遗物 |

未开箱、已领取和空箱的 relic 为 null；default 也保留这个值。未开箱时遗物已经预生成的内部内容不会进入详情。

基础观察的 full/default/summary 均只提供遗物 name 和 enabled，正文与关键词说明由 inspect_treasure 提供。正在打开、遗物尚不能领取等状态，可用 enabled 和 chest 反映；查看本身不要求房间达到可操作状态。

## 典型完整返回

[14 份 JSON 与调用参数](2026-11-06-inspect-treasure-examples/README.md)包含 12 份 full、2 份 default，均来自真实图形实例。建议先看：

- [未开箱](2026-11-06-inspect-treasure-examples/closed.full.json)及[default 的空遗物](2026-11-06-inspect-treasure-examples/closed.default.json)。
- [已开箱的 Anchor](2026-11-06-inspect-treasure-examples/opened-anchor.full.json)、[Calling Bell](2026-11-06-inspect-treasure-examples/nested-relic.full.json)、[Astrolabe](2026-11-06-inspect-treasure-examples/transform-relic.full.json)。
- [已领取](2026-11-06-inspect-treasure-examples/collected.full.json)、[空箱](2026-11-06-inspect-treasure-examples/empty.full.json)。
- [地图覆盖](2026-11-06-inspect-treasure-examples/map-covered.full.json)、[选牌覆盖](2026-11-06-inspect-treasure-examples/selection-covered.full.json)及[保留已有许可的拒绝](2026-11-06-inspect-treasure-examples/with-permission.full.json)。

opening 未单独采集成功详情样本，按源码核对；多人、全部遗物组合与第三方宝箱不作穷举。

## 参数建议

建议新增 preset:summary，使用 get_observation 的静态宝箱格式：省略遗物 description 和整个 hover_tips，保留房间状态、遗物名称／可领取状态及前进按钮。relic:null 沿用已有保留规则。

候选示例，依据已开箱 full 整理，**尚未实现**：

```json
{
  "scene": "treasure",
  "screen": {"status": "visible"},
  "treasure": {
    "status": "visible",
    "chest": "open",
    "relic": {"name": "Anchor", "enabled": true},
    "proceed": {"text": "Skip", "enabled": true, "skips_remaining": true}
  }
}
```

当前单人页面是一件遗物和宝箱／前进状态，参数建议仅增加 summary。

小范围重构建议把遗物的显示、悬停和点击判断分开。当前读取还会按屏幕边缘截断遗物图标；建议改用已审阅遗物的显示规则，保留隐藏、透明与容器裁剪判断，点击继续检查原生位置和可操作性。这样可以接入同一静态宝箱读取格式，供基础观察和 summary 复用。
