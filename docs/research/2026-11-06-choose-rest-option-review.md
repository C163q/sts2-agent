# choose_rest_option 核验与建议

> 当前状态：三项修复已实现、验收并通过独立审阅，功能41b7d60已合入main；[实施与验证](2026-11-06-rest-option-feedback-implementation.md)及新样本另列，原审阅样本保留修复前行为。工具清单29/44，无阻塞。

流程见[工具清单](2026-11-02-mcp-tool-review.md)。实现依据及验证边界单列在[开发核验](2026-11-06-choose-rest-option-development-notes.md)。

## 优先问题

| 问题 | 实际影响 | 建议 |
| --- | --- | --- |
| 明确点击前拒绝仍使已有操作许可失效 | 战斗中误用火堆选项后，直接end_turn会被要求先观察；在选牌页误用后，也不能直接取消选择。关闭地图、关闭牌组和只读工具自身不要求许可，仍可使用 | 点击前已经确定未执行时保留已有许可；状态过期或结果不明仍要求读取 |
| 不同拒绝原因均显示“操作不可用” | 无火堆、覆盖页面、选项不存在、已用过或置灰，公开返回无法区分 | 分别说明当前场景、需要处理的覆盖页、未知或已消失的ID、禁用选项及等待状态，并给出相应恢复方式 |
| 锻炼／填火改变了可见遗物计数，事件仍为空 | 壶铃0→1、蜡烛5→10，动作仅返回action_completed，需再观察才能看到计数变化 | 建议补充通用的可见遗物计数变化事件；具体字段待定稿，不能直接暴露内部数值 |

前两项属于已有TODO中的错误恢复／错误说明范围。参数错误发生在MCP本地时已保留许可，无需重做。第三项是此次动作反馈核验新确认的缺口，尚未加入用户TODO。

## 审阅基线的参数与返回

```json
{"option_id":"HEAL","preset":"full"}
```

option_id使用当前火堆按钮的原生字符串ID，区分大小写；preset支持default/full，默认default。没有summary或批量选择。

成功返回当前scene、screen、available_actions和transition，延续已有精简动作格式。full与default只在通用空值／事件精简规则上有差别，不附送火堆详情；后续需要查看按钮或说明时调用inspect_rest_site。

典型流程包括：

| 选项／场景 | 动作到达的边界与效果 |
| --- | --- |
| HEAL普通休息 | 恢复生命，待按钮和动画稳定后返回action_completed；[实际full](2026-11-06-choose-rest-option-examples/heal.full.json)、[default](2026-11-06-choose-rest-option-examples/heal_default.default.json) |
| SMITH锻造／多张锻造 | [打开选牌](2026-11-06-choose-rest-option-examples/smith.full.json)返回choice_required；实际升级由[后续确认](2026-11-06-choose-rest-option-examples/smith-confirm.full.json)产生。[双牌确认](2026-11-06-choose-rest-option-examples/multi-confirm.full.json)逐张记录；取消返回火堆，不消耗机会 |
| COOK烹饪 | [打开移除两张牌的选择](2026-11-06-choose-rest-option-examples/cook.full.json)；[确认](2026-11-06-choose-rest-option-examples/cook-confirm.full.json)后才移除并增加最大生命，支持取消 |
| LIFT／KINDLE | 执行[锻炼](2026-11-06-choose-rest-option-examples/lift.full.json)／[填火](2026-11-06-choose-rest-option-examples/kindle.full.json)，两者事件均为空；帐篷允许继续使用其余选项，已使用选项移除 |
| HEAL追加奖励 | 停在实际奖励页面，action_completed；[JSON](2026-11-06-choose-rest-option-examples/heal_reward.full.json)，后续用奖励工具继续 |
| DIG及嵌套奖励／变牌 | [普通挖掘](2026-11-06-choose-rest-option-examples/dig.full.json)记录取得遗物；[召唤铃铛](2026-11-06-choose-rest-option-examples/dig-nested.full.json)还记录诅咒入牌组；[星盘](2026-11-06-choose-rest-option-examples/dig-transform.full.json)停在变牌选择，[后续确认](2026-11-06-choose-rest-option-examples/transform-confirm.full.json)才记录移除／加入 |
| CLONE／HATCH | 原生复制附有相应附魔的卡牌／取得孵化遗物；仅核对源码 |
| 无火堆、覆盖、置灰、未知ID | 拒绝；[无火堆](2026-11-06-choose-rest-option-examples/no_rest.full.json)、[后续回合被拦截](2026-11-06-choose-rest-option-examples/no_rest_blocked_continuation.full.json)、[置灰锻造](2026-11-06-choose-rest-option-examples/disabled_smith.full.json)、[选牌覆盖](2026-11-06-choose-rest-option-examples/selection_covered.full.json) |

进入锻造选择时events:[]合理：此时还没有升级任何牌。休息、挖掘和后续确认应分别记录当次实际发生且玩家可见的效果，不能把整个后续选择流程提前算作完成。

## 参数与输出建议

建议保留option_id及default/full。当前动作回执已经精简，没有新增summary的必要。火堆选项可能打开选择或奖励，逐次调用并按返回边界继续，适合现有流程。

拒绝判断建议在火堆模块内共用，供选项enabled、available_actions与实际点击使用；读取仍使用独立的页面可读性判断。保留原生按钮执行和现有等待流程，小范围整理即可。

遗物计数建议由共用事件记录补齐，覆盖其他动作产生的同类可见变化。它涉及新增事件类型及字段校验，范围比前两项大，可单独一步完成；可选方案是维持现状、通过inspect_relics查看，但动作回执仍不能表达这项已发生的变化。这里建议补齐共用记录。

## 典型JSON与验证范围

[27份完整公开JSON及调用参数](2026-11-06-choose-rest-option-examples/README.md)包含26份full、一份default；后续确认使用selection_option，文件明确标明实际工具。没有附图或预读随机结果。

35项相关Python通过；12类不同GUI场景完成，173次MCP调用包含首轮测试前提错误，详细计数与边界见开发核验。恢复测试确认：需要许可的动作被拦截，关闭视图／读取仍能直接调用。成功流程的HP、永久牌组及取得遗物事件正确；锻炼／填火计数反馈是上述新缺口。

没有新增CLONE、HATCH、多人MEND、第三方选项、真实超时或中途退出的游戏实测。上述审阅基线只增加测试和文档，修复后的结果另见实施记录。

## 输出定稿

保留option_id、default/full和精简动作回执，无summary。明确点击前拒绝保留已有许可，并说明场景、覆盖页、目标不存在、已消耗／禁用、不支持及等待状态；按钮enabled、available_actions和执行共用判断。读取继续使用独立可读性入口。

新增共用relic_counter_changed事件，relic仅含英语name，before／after为实际显示的整数或null，至少一端为整数且两端不同。null表示遗物图标可见时没有计数，full/default均保留对照两端。采集真实标签刷新及观察间的公开变化，不用内部DisplayAmount补齐；同帧已显示的连续变化分别记录，重复刷新不重复。

顶栏／图标隐藏或当前页面不可读时丢弃基线，恢复显示、取得新遗物或更换显示控件只建立基线，不追溯隐藏期间的变化。动作结束后销毁记录器，其他动作复用同一入口。火堆原生执行、选择／奖励边界、超时和通用许可规则保持。
