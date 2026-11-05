# inspect_rest_site 核验与参数建议

> 当前状态：现状核验完成，进入设计讨论。65项Python、七类GUI及16份完整返回已整理；工具行为尚未修改，本项未核销。待讨论具体错误原因、输出校验、读取规则和summary／筛选方案，无阻塞。

流程见[工具清单](2026-11-02-mcp-tool-review.md)。源码入口、问题编号和详细证据见[开发核验](2026-11-06-inspect-rest-site-development-notes.md)。

## 优先问题

| 问题 | 影响与建议 | 证据与状态 |
| --- | --- | --- |
| 无火堆、地图／牌组／选牌／奖励覆盖时均只报“操作不可用” | 中：模型不知道该关闭页面、完成选择还是等待。建议公开固定的具体原因，提示相应工具 | GUI已确认，待定稿修复 |
| 坏响应的覆盖状态与选项内容可以互相矛盾 | 中：MCP仍接受标着covered／hidden、却含火堆选项的响应，并生成许可。建议把scene、screen和详情一起校验 | 四种受控矛盾响应确认；当前游戏端在真实覆盖时正确拒绝，未发现实际穿透 |
| 读取仍依赖点击就绪与视口边界 | 低：工具与可用列表都要求操作就绪，所有按钮在屏幕内；详情也按视口裁剪。建议将“页面可读”与“按钮可执行”分开，取消读取的离屏筛选，保留真实隐藏／透明／裁剪边界 | 源码确认；文字淡出、离屏和不可悬停控件没有新增GUI复现，不能说正常游戏已出现漏项 |

与第三项一同核对的边界：full目前直接提供每个选项的说明，没有单独检查该按钮能否被鼠标或控制器聚焦。普通灰置选项仍能悬停，返回其说明正确；特殊的不可聚焦控件建议沿用其他详情工具的静态数据加note规则，具体格式待定。

已有许可时，明确读取拒绝会保留许可，可直接关闭地图／牌组、取消选牌、结束子奖励或执行战斗动作；首次读取失败不会生成许可。本地参数错误也保留旧许可。没有发现该工具需要再修一套“拒绝后强制观察”的问题。

## 当前参数与信息来源

仅支持`preset:default/full`，默认default，没有操作参数、summary或筛选。full返回scene、screen及rest_site；不附送顶栏或available_actions。

- `prompt`：当前显示的火堆标题，活动完成后可能为null。
- 顶层`description`：画面当前已展开的说明；没有展开时为null。
- `options`：每项id、text、enabled和完整悬停description。id为HEAL、SMITH等原生字符串，供choose_rest_option使用。
- `proceed`：当前实际按钮的text、enabled；没有时为null。

full保留普通null；default只按共用规则省略null，不省略false或空options。没有当前候选时，options:[]仍是有意义的页面状态。

说明来自同一原生选项的动态文本，包含当前恢复量、锻炼剩余次数、填火数值、烹饪要求和遗物追加奖励。挖掘只说明“挖出遗物”，没有提前返回所得遗物身份。

## 场景目录与完整返回

[16份实际JSON及参数](2026-11-06-inspect-rest-site-examples/README.md)包括15份full、一份default。

| 场景 | 当前返回与代表样本 | 核对范围 |
| --- | --- | --- |
| 普通火堆 | HEAL／SMITH；[full](2026-11-06-inspect-rest-site-examples/basic.full.json)、[default](2026-11-06-inspect-rest-site-examples/basic.default.json) | GUI |
| 灰置选项 | 不可升级、可移除卡不足，保留具体说明和enabled:false；[JSON](2026-11-06-inspect-rest-site-examples/disabled.full.json) | GUI与原生悬停源码 |
| 帐篷与多种活动 | LIFT／KINDLE／COOK等；[初始](2026-11-06-inspect-rest-site-examples/tent.full.json)、[锻炼后剩余选项](2026-11-06-inspect-rest-site-examples/tent-after-lift.full.json) | GUI |
| 休息追加奖励 | HEAL说明包含Dream Catcher追加卡牌；[JSON](2026-11-06-inspect-rest-site-examples/heal-with-reward.full.json) | GUI |
| 挖掘 | DIG说明；[JSON](2026-11-06-inspect-rest-site-examples/dig.full.json) | GUI，未选择或预读挖掘结果 |
| 活动完成 | options:[]、prompt:null、前进按钮；[JSON](2026-11-06-inspect-rest-site-examples/activity-complete.full.json) | GUI |
| 选牌取消／子奖励返回 | 恢复当前火堆；[取消后](2026-11-06-inspect-rest-site-examples/after-selection-cancel.full.json)、[奖励结束后](2026-11-06-inspect-rest-site-examples/after-reward.full.json) | GUI |
| 地图／牌组／选牌／奖励覆盖 | 详情拒绝，不返回底层选项；[地图](2026-11-06-inspect-rest-site-examples/map-covered.full.json)、[选牌](2026-11-06-inspect-rest-site-examples/selection-covered.full.json) | 四类覆盖GUI |
| 无火堆 | 首次失败要求先成功读取，有旧许可时可继续；[首次](2026-11-06-inspect-rest-site-examples/no-rest-first-read.full.json)、[已有许可](2026-11-06-inspect-rest-site-examples/no-rest-existing-permission.full.json) | 战斗场景GUI |
| CLONE／HATCH／多人MEND及第三方选项 | 返回仍经过同一选项读取；动作支持范围另行判断 | 源码，未新增实际样本 |

## 候选设计

建议先处理上述正确性与读取职责，再加以下参数；均未实施。

### summary

建议保留上下文、status、prompt、options的id/text/enabled以及proceed，省略顶层description和各选项description。相当于看有哪些按钮、哪些可用；需要说明时使用default/full。

下例是建议格式，不能作为当前可调用结果：

```json
{
  "scene": "rest_site",
  "screen": {"status": "visible"},
  "rest_site": {
    "status": "visible",
    "prompt": "What shall I do?",
    "options": [
      {"id": "HEAL", "text": "Rest", "enabled": true},
      {"id": "SMITH", "text": "Smith", "enabled": true}
    ]
  }
}
```

这与get_observation的火堆主体接近。基础观察按既有规则保留画面已展开的说明；本工具summary建议统一省略说明，full/default继续保留。该差异是待确认设计，尚未修改基础观察。

### option_ids

建议可选`option_ids:["HEAL","SMITH"]`，名称与动作的option_id对应。省略或null取全部，[]取空；重复ID去重、结果保持原生顺序，未找到的ID合并报错。筛选只应用于options，prompt和proceed仍描述当前页面。

火堆选项通常不多，筛选主要方便单独查看恢复量、某个灰置原因或遗物活动说明；可以独立于summary使用。另一种选择是只加summary、保留全部选项，参数更少，但不能单独取某一项的完整说明。

读取入口建议集中页面可读性、具体原因和悬停能力判断，工具执行及available_actions共用；choose_rest_option与proceed继续使用动作就绪判断。无需重做整个火堆流程。
