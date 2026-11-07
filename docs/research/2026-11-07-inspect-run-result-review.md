# inspect_run_result 核验与建议

> 当前状态：summary规则已确认；内容完整性提示及基础观察同步方案仍在讨论。尚未修改工具行为、未核销。总进度见[工具清单](2026-11-02-mcp-tool-review.md)。

已整理[19份典型实际JSON](2026-11-07-inspect-run-result-examples/README.md)：17份full、2份default。源码、原始证据及验证限制见[开发核验](2026-11-07-inspect-run-result-development-notes.md)。

## 优先处理的问题

| 问题 | 影响与依据 | 建议及状态 |
| --- | --- | --- |
| 1. 拒绝原因过于笼统 | 中：战斗中、已返回菜单、普通菜单时间线等情况均公开“The requested action is unavailable.”，无法判断是没有本局结算、页面被覆盖还是还在等待。实际调用已复现。 | 集中结算详情的可用性和原因，公开具体恢复提示；尚未修改。 |
| 2. 页面上下文及完整详情校验不足 | 中：给真实响应副本换上商店／被牌组覆盖的screen，或删除完整详情的hover_tips／提示正文，仍被接受并刷新许可。属于异常响应检查，未在正常游戏中观察到这些错配。 | 校验scene、screen与主体状态一致，并按当前协议要求检查完整详情字段；坏响应清除许可。尚未修改。 |

纯读取拒绝后的许可恢复已正常：已有观察时，误调用inspect_run_result后可直接end_turn；首次错误读取不会建立许可。本地参数错误也已有保留旧许可的规则，无须为此增加动作式恢复特例。

另有一项需要商定的读取限制：当前工具要求**整页动画、文字及按钮都已就绪，且存在可点击按钮**。基础观察可返回not_ready状态下已显示的部分内容，详情却会拒绝。源码与受控状态副本已确认这项差异，尚未做专门的动画时序GUI实测。建议把读取和动作就绪分开；显示未完成时的明确标识见下文待确认方案。若实施，应同时检查动画中悬停说明的可用性及徽章引用，避免提前给出未显示信息。

## 当前参数与页面

仅有通用`preset: "default" | "full"`，默认default；不支持summary或筛选。

```json
{"preset":"full"}
```

成功结果为`scene`、`screen`和`run_result`。它读取当前页，不翻页，也不返回transition或available_actions；当前可用动作由get_observation获得。

| phase | 页面及返回重点 | 典型full |
| --- | --- | --- |
| outcome | 胜负首屏、原生标题／语句和继续按钮；尚无分数、徽章和发现列表 | [胜利](2026-11-07-inspect-run-result-examples/victory-outcome.full.json)、[失败](2026-11-07-inspect-run-result-examples/death-outcome.full.json) |
| summary | 分数行、徽章、发现计数及其悬停解释，保留已显示解锁进度 | [胜利汇总](2026-11-07-inspect-run-result-examples/victory-summary.full.json)、[失败汇总](2026-11-07-inspect-run-result-examples/death-summary.full.json) |
| tutorial | 时间线教程与继续按钮 | [教程](2026-11-07-inspect-run-result-examples/tutorial.full.json) |
| timeline | 可揭晓条目的ID／按钮，以及可浏览时间线图标的悬停说明 | [初始](2026-11-07-inspect-run-result-examples/timeline.full.json)、[展开后的时间线](2026-11-07-inspect-run-result-examples/timeline-expanded.full.json) |
| epoch | 当前章节故事、继续或原生提供的章节按钮 | [章节](2026-11-07-inspect-run-result-examples/epoch.full.json) |
| unlock | 当前已揭示的解锁内容和确认按钮 | [普通提示](2026-11-07-inspect-run-result-examples/unlock.full.json)、[卡牌](2026-11-07-inspect-run-result-examples/unlock-cards.full.json)、[药水](2026-11-07-inspect-run-result-examples/unlock-potions.full.json)、[遗物](2026-11-07-inspect-run-result-examples/unlock-relics.full.json) |
| history | 本局详情的可滚动文字及物品；本版本View Run入口禁用，使用现有原生页面测试夹具核验 | [本局详情](2026-11-07-inspect-run-result-examples/history.full.json) |
| leaderboard | 原生提供时识别榜单页面；本轮只核对实现，没有GUI样本 | 见开发核验的未验证边界 |

内容变体不逐一复制：不同角色／故事共用同一结构；卡牌、药水和遗物解锁分别给出样例。卡牌沿用共用完整格式和逐牌解释；药水、遗物详情给出名称、效果正文和附加悬停解释。

胜利首屏仍保留“Victory...?”中的问号。发现图标的原生提示最多列十个名称，之后保留省略号。已返回主菜单后再打开的普通时间线不再作为本局结算，错误样例见[菜单](2026-11-07-inspect-run-result-examples/menu.full.json)和[无关时间线](2026-11-07-inspect-run-result-examples/unowned-timeline.full.json)。

## 已确认的summary规则

新增summary，保留当前页面、文字、分数、徽章、发现计数、按钮及物品名称；卡牌使用共用卡牌摘要，药水／遗物省略效果正文和附加解释。页面级hover_tips保留source、title，省略description，时间线条目名称因此仍可读取。已显示的章节故事正文保留。

尚未新增筛选需求，现有default/full保持。两项正确性问题仍优先于预设实现；尚未开始修改产品代码。

## 显示未完成时的提示（待确认）

现有status:not_ready表示页面未达到操作就绪条件，可能涉及动画、文字、输入阻挡或按钮状态；它不能独立表达内容是否完整。建议增加当前页的content_complete，并让inspect_run_result及get_observation的full/default/summary使用同一次读取的判断：

- false：当前页仍在展示过程中，返回值只代表已显示部分，数值／列表可能继续变化；附简短note说明。
- true：当前页的展示流程已完成，不代表后续页面或未揭示解锁也已读取。
- 该字段在三种预设均保留。文字／计分／入场展示状态与操作就绪分开判断，不能直接用Ready作为content_complete。按钮不可用也可能同时存在完整内容。

例如展示中的相关字段（示意，并非当前接口已有输出）：

```json
{
  "run_result": {
    "status": "not_ready",
    "phase": "summary",
    "content_complete": false
  }
}
```

仅保留not_ready并补note也能提示等待，但会继续混合内容展示和操作条件；优先建议独立content_complete字段。该方案尚待确认及原生展示时序核验。

## get_observation的现状及同步建议

以下只比较run_result主体；顶栏继续独立采用既有规则。

| 内容 | full | default | summary |
| --- | --- | --- | --- |
| 卡牌 | 共用完整格式及逐牌解释 | 完整格式并按default过滤 | 共用卡牌摘要 |
| 药水／遗物 | 名称 | 名称 | 名称 |
| 页面级hover_tips | 不返回 | 不返回 | 不返回 |
| 当前页文字、分数、徽章、发现和按钮 | 保留 | 按default处理 | 保留 |

因此基础观察尚未具备已确认summary中的页面级source/title；时间线可能只剩Reveal和ID。建议为基础观察同步补齐这些标题，并与inspect_run_result复用同一静态内容入口；卡牌继续沿用此前已定稿的full/default完整、summary摘要约定。此同步方案待确认，不把建议描述为现有能力。

读取及错误判断可以在现有RunResultInspection内整理，无须重构整套结算流程。run_result_option的动作拒绝恢复留待下一项审阅，不因本工具的纯读取恢复正常而推断动作工具也已完成。
