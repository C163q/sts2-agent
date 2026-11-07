# run_result_option 核验与建议

> 当前状态：审阅完成，待确认三项修复及详情页夹具的补验范围；尚未修改产品行为。26项相关Python检查通过，已核验战斗误用、结算拒绝、原生解锁链及菜单关联边界。总进度见[工具清单](2026-11-02-mcp-tool-review.md)。

本工具点击当前结算页面提供的按钮或章节条目，一次处理一个操作。本文用于确认修复范围与参数；源码和验证限制单列在[开发核验](2026-11-08-run-result-option-development-notes.md)，典型返回见[15份实际JSON](2026-11-08-run-result-option-examples/README.md)。

## 优先处理的问题

| 问题 | 实际影响 | 建议 |
| --- | --- | --- |
| 未点击的拒绝仍要求重新观察 | 战斗中误调用后，画面没有变化，随后 end_turn 仍收到 observation_required。 | 明确没有点击、滚动或提交动作时，保留已有操作许可，允许直接纠正。 |
| 错误原因过于笼统 | 没有本局结算、选项不存在、按钮禁用或页面仍在展示等情况，公开错误都只说操作不可用。 | 给出具体原因，提示等待、改选当前启用选项或处理覆盖页面。 |
| 无法重新打开已揭晓章节 | 原版允许点击已揭晓条目重新阅读故事，工具却只提供待揭晓条目；相应的章节翻页也缺少正常到达路径。 | 将当前结算关联时间线上的已揭晓条目一并列为选项，沿用稳定 ID，区分揭晓和查看。 |

前两项属于[用户 TODO](../development/TODO.md)已有的错误恢复与原因准确性范围。参数格式错误在 MCP 本地拒绝后，已有许可可以保留；这一部分无需另加规则。

## 当前参数和成功结果

```json
{"option_id":"continue","preset":"full"}
```

`option_id` 使用 get_observation 或 inspect_run_result 当前提供且 enabled 为 true 的原值；通用 preset 支持 default/full，默认 default。

| 当前页面 | 当前支持的操作 | 下一处停留位置 |
| --- | --- | --- |
| 胜负首屏 | continue | 计分汇总 |
| 汇总 | main_menu；原生实际启用时另有 view_run、leaderboard | 主菜单，或仍属于本局的时间线／详情／榜单 |
| 时间线教程 | continue | 时间线 |
| 时间线 | epoch:N、back | 章节故事或主菜单；仍有待揭晓内容时 back 可禁用 |
| 章节故事 | continue；原生提供时的 next_chapter、previous_chapter | 解锁内容、时间线或相邻章节 |
| 解锁内容 | confirm | 后续解锁页或时间线 |
| 本局详情 | back | 汇总；当前原版入口禁用，返回操作尚不能据现有夹具验收 |

成功返回 scene、screen、available_actions 和 transition；页面正文按需另行观察。正常翻页使用 action_completed，不重复报告 run_won/run_lost。解锁新卡牌或物品是进度解锁，不能作为本局获得卡牌／遗物／药水事件返回。

例如，从章节故事进入解锁确认页：

```json
{
  "scene": "run_result",
  "screen": {"status": "visible", "view": "run_result"},
  "available_actions": ["run_result_option", "inspect_run_result"],
  "transition": {"stop_reason": "action_completed", "complete": true, "events": []}
}
```

这是[实际full返回](2026-11-08-run-result-option-examples/epoch-to-unlock.full.json)。已实测可以不再观察，直接用confirm继续。当前参数错误在本地拒绝后也可直接纠正；明确未交互的原生拒绝仍有上表中的恢复问题。首次调用、真正过期和不确定结果继续要求观察。

main_menu 按钮显示的文字可能是 Unlock；点击后会先进入时间线。只有返回 scene: "main_menu" 才确认已经回到菜单。工具保持逐步点击，不自动领取所有解锁或开启新一局。

实测已揭晓条目仍出现在时间线提示来源中，但从options消失，使用原epoch ID会被拒绝。当前未能通过该工具重新打开已揭晓章节，故上一章／下一章仅核对了原生与工具代码，未计为GUI通过。

## 参数和实现建议

建议保留 option_id 及 default/full，不增加 summary、筛选或批量点击。成功回执已足够精简，页面内容由两个查看工具提供。

小范围整理结算操作的可用性与拒绝原因，让执行入口、选项 enabled 和 available_actions 共用条件。时间线需要滚动到目标时，从开始滚动就记为已经交互；滚动后的失败继续要求读取当前状态，不能当作画面未变的拒绝。

## 本局详情的验证缺口

现有测试用普通历史页面准备了结算详情，读取通过，但点击返回时游戏崩溃。源码显示该普通页面的返回依赖菜单栈，而夹具把它直接挂在结算页下，未建立这个关联；它也不是原生结算代码所指定的详情资源。因此这次崩溃不能当作正常 View Run 流程已复现的故障。

实施时应先修正测试页面的创建方式，再验证返回动作。保持原版 View Run 按钮的实际禁用状态；不通过强制启用来提供正常入口。此次不新增 TODO 项。
