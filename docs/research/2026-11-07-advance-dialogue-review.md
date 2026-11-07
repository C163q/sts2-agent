# advance_dialogue 核验与建议

> 当前状态：两项整改与参数已确认，进入实现与验证，尚未核销。原样例保留审阅基线。总进度见[工具清单](2026-11-02-mcp-tool-review.md)。

本工具处理常规先古之民和终章建筑师的对话。32项相关Python检查通过，五类GUI现状已核验；失败的脚本准备尝试单独保留，不计为产品修复。下文面向参数及行为决策；源码、验证与边界见[开发核验](2026-11-07-advance-dialogue-development-notes.md)，完整返回见[典型 JSON](2026-11-07-advance-dialogue-examples/README.md)。

## 优先处理的问题

| 问题 | 优先级与影响 | 建议及状态 |
| --- | --- | --- |
| 明确未点击的拒绝仍使后续操作要求重新观察 | 中：在错误房间、选牌页或对话已结束时，画面未变，改用结束回合、选牌、选馈赠或前进仍收到 observation_required。 | 明确点击前拒绝且未改 UI 时保留已有许可，允许直接处理选择、选择馈赠或前进。已按定稿实现并验收，待独立审阅。 |
| 错误原因无法指导下一步 | 中：上述情况公开返回同一句“The requested action is unavailable.”，无法判断应等待、关闭页面、选馈赠还是 proceed。 | 给出具体原因及对应工具；先古之民和建筑师两条路径一起处理。已按定稿实现并验收，待独立审阅。 |

地图／牌组覆盖同样只给出笼统错误；close_map、close_card_view本身不要求玩法许可，拒绝后已可直接关闭，不能把它们列为被许可问题阻挡的动作。

这两项属于[用户 TODO](../development/TODO.md)中已有的报错恢复与错误准确性范围，可随本工具提前处理。没有新增 TODO 项。

## 当前参数和用途

仅有通用 `preset: "default" | "full"`，默认 default；没有其他操作参数。

```json
{"preset":"full"}
```

一次调用推进当前对话一步，等下一处可操作状态就绪后返回：

| 当前场景 | 推进结果 | 后续工具 |
| --- | --- | --- |
| 先古之民对话中段 | 显示下一句，仍可继续对话 | advance_dialogue |
| 先古之民推进到最后一句 | 展开馈赠，继续按钮消失 | choose_ancient_option |
| 建筑师对话中段 | 显示下一句或回应 | advance_dialogue |
| 建筑师推进到最后一句 | 显示原生最终前进按钮 | proceed |

普通事件使用 choose_event_option；馈赠后的选牌、奖励使用相应选择或奖励工具。建筑师最终前进才会沿原生流程进入胜利结算；advance_dialogue 到达最后一句仍属于普通动作完成。

典型full包括[先古对话中段](2026-11-07-advance-dialogue-examples/ancient.full.json)、[转入馈赠选择](2026-11-07-advance-dialogue-examples/ancient-to-gifts.full.json)和[建筑师转入最终前进](2026-11-07-advance-dialogue-examples/architect-to-proceed.full.json)。这三份由原生实测响应按现行输出规则生成，来源与实际default调用分开标记。

成功回执包含 scene、screen、available_actions 和 transition，不重复返回完整台词。当前文字由 get_observation 或 inspect_ancient 按需读取。events 记录动作期间实际发生的可见变化；普通翻句没有资源或物品变化，实测为 []。

成功推进后可以继续调用下一个合法工具。首次调用仍需要观察许可；观察过期、结果不确定或已开始交互后的失败继续要求读取当前状态。

## 参数与重构建议

建议维持零操作参数及 default/full，暂不增加 summary、筛选或连续推进参数。现有成功回执已经精简；逐步推进保留每句对话和最终按钮的操作边界。

优先修复上方两项问题。小范围重构只整理两类对话各自的“当前能否推进及原因”，供执行入口、按钮 enabled 和 available_actions 共用；保留它们不同的原生流程。先古之民需覆盖尚未选择／已领取馈赠、后续选择和奖励；建筑师需明确最终按钮应使用 proceed。

工具描述目前已准确限定为推进一次先古之民或建筑师对话，并区分馈赠和最终前进；无需扩写成长篇操作说明，具体拒绝由错误返回解释。

## 输出定稿

修复明确未点击、未改UI的拒绝后丢失已有许可，以及拒绝原因不明确两项问题；同时整理两类对话各自的可用性判断，供执行、按钮enabled与available_actions共用。错误区分无对话房间、非单人、页面覆盖、等待原生流程、对话已结束和建筑师最终前进，并给出相应工具提示。

零操作参数及default/full保持；成功仍推进一次并返回精简动作回执，普通翻句events为空。首次、过期、已交互、不确定或坏响应不获得恢复许可。原生点击与最终馈赠／proceed边界不变，不新增summary、筛选或连续推进。实施依据见[计划](../superpowers/plans/2026-11-07-dialogue-advance-recovery.md)。
