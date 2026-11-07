# choose_ancient_option 核验与建议

> 当前状态：审阅完成，四项问题待确认处理范围，尚未修改产品。11类场景已核验：10类完成现状检查，致死馈赠在两个独立实例发生运行时致命错误，根因未定。参数建议待确认。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。[16份完整实测JSON](2026-11-07-choose-ancient-option-examples/README.md)包含15份full、一份default；源码、验证细节及限制见[开发核验](2026-11-07-choose-ancient-option-development-notes.md)。

## 优先处理的问题

| 问题 | 优先级与影响 | 建议及当前状态 |
| --- | --- | --- |
| 致死馈赠无法正常返回，游戏日志出现致命错误 | 高：隔离局在最大生命为9时选择卓越斗篷，MCP最终只收到timeout，无法得到正常失败结算反馈。 | 先定位崩溃及结算流程，再验证run_lost。当前尚不能确定属于工具、Mod、原生游戏还是隔离夹具；不作为普通动画超时处理。 |
| 卡牌包馈赠漏记遗物获取事件 | 中：选择Scroll Boxes后，顶栏已有该遗物，回执却为events:[]。两个独立实例均出现。 | 核验切换选牌页时的可见性与事件记录时序，补齐玩家已能看到的获取反馈；尚未修改。 |
| 明确拒绝后丢失已有操作许可 | 中：无效ID、按钮禁用或对话未完成时没有点击、状态未变，纠正ID／推进对话／结束回合却会收到observation_required。 | 明确点击前拒绝时保留已有许可；过期观察、已交互和不确定结果继续要求读取。已复现，待修复。 |
| 拒绝原因过于笼统 | 中：无先古房间、无效ID、已领取、对话未结束及覆盖页均无法从公开错误区分。 | 返回具体原因，并提示advance_dialogue、proceed、close_map、close_card_view或相应选择／奖励工具。已复现，待修复。 |

致死问题来自受控隔离局，尚未在自然推进的对局或不加载Mod的实例中验证。实测范围和原始失败记录应保留，不能据此把所有致死选项概括为必然崩溃。

## 当前参数与返回

必填`option_id`为当前馈赠选项ID，范围0至2147483647；支持`preset:default/full`，默认default。一次选择一个馈赠。当前描述和参数规模基本合适，建议保留，不增加summary或筛选参数。

调用示例：

```json
{"option_id":0,"preset":"full"}
```

成功返回场景、页面、可用动作及transition；若出现选牌，增加精简selection和必要note。馈赠的具体效果通过events反馈；当前页面详情可按需查看。

| 典型场景 | 当前结果 |
| --- | --- |
| 普通营养牡蛎 | action_completed／complete:true；包含relic_obtained、max_hp_changed和hp_changed。[完整full](2026-11-07-choose-ancient-option-examples/normal.full.json) |
| 欧洛巴斯之触 | action_completed；依次记录馈赠获取、旧起始遗物移除及增强遗物获取。[完整full](2026-11-07-choose-ancient-option-examples/replace.full.json)、[完整default](2026-11-07-choose-ancient-option-examples/replace.default.json) |
| 变牌馈赠 | choice_required／complete:true，selection为deck_transform，后续由选牌工具处理。[完整full](2026-11-07-choose-ancient-option-examples/transform.full.json) |
| 卡牌包馈赠 | choice_required，selection为bundle；当次events为空，遗物反馈缺口单列上述问题。[完整full](2026-11-07-choose-ancient-option-examples/bundle.full.json) |
| Lost Coffer | scene:rewards、action_completed；额外奖励留给领取工具处理。[完整full](2026-11-07-choose-ancient-option-examples/nested-rewards.full.json) |
| 致死斗篷 | 返回timeout／outcome:unknown；日志有运行时致命错误。[实际错误](2026-11-07-choose-ancient-option-examples/lethal-timeout.full.json) |
| 无效选项或错误页面 | illegal_action，公开消息为统一的“The requested action is unavailable.”。[无效ID](2026-11-07-choose-ancient-option-examples/unknown-option.full.json)、[地图覆盖](2026-11-07-choose-ancient-option-examples/map-covered.full.json) |
| 观察已过期 | stale_state，后续动作要求重新观察；该行为正常。[实际返回](2026-11-07-choose-ancient-option-examples/stale.full.json) |

本地参数错误已经会保留许可；真正的问题是已送到Mod、明确未点击的拒绝。例如[无效ID被拒绝](2026-11-07-choose-ancient-option-examples/unknown-option.full.json)后，紧接着[改用正确ID](2026-11-07-choose-ancient-option-examples/correct-after-rejection.full.json)仍被要求重新观察。

成功到达可操作页面或可见选择时，已有连续操作许可正常续接。首次动作仍需要当前观察或相关详情提供许可；无需在每次成功后固定调用get_observation。

## 建议的处理范围

优先定位致死选择的运行时错误，并修复卡牌包遗物反馈遗漏；两项都需按实际UI验证。同步补齐明确拒绝恢复与具体原因。

重构限于先古页面和单项选择的共用判断，使选项enabled、available_actions及执行入口采用一致条件；事件记录只针对已经发现的切换时序缺口调查。保持原生领取、后续选牌／奖励及现有精简回执，不扩大成全项目流程重构。

参数维持option_id和default/full即可。工具提示只需说明选择当前可用馈赠、遇到后续选择或奖励时停下；具体错误由返回消息解释。
