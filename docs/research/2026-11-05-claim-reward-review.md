# claim_reward 核验与设计建议

> 当前状态：三项修复、718 项 Python、124 项 C#、十一类 GUI 与三类回归已通过，待独立审查和交付。本项尚未核销。结果见[实施记录](2026-11-05-claim-reward-recovery-implementation.md)；下方问题及原返回保留审阅基线。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。源码、问题编号与验证证据见[开发核验](2026-11-05-claim-reward-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确未操作的拒绝也会要求重新观察 | 中：重复领取已消失的奖励，或在地图、牌组、选牌覆盖时领取，被拒绝后下一次合法动作会报 observation_required | 在滚动或点击开始前明确拒绝时保留已有操作许可；滚动开始后的失败仍要求观察 | 已修复，约定验证通过 |
| 拒绝原因过于笼统 | 中：无奖励页、页面被覆盖、奖励 ID 已不存在等情况，公开错误均为“操作不可用”，LLM 无法据此决定下一步 | 给出具体原因和可执行的恢复提示 | 已修复，约定验证通过 |
| 回执里的奖励 ID 未与请求核对 | 中：损坏成功响应把结果写成另一个奖励 ID，仍会被接受并续接操作许可 | 要求 reward_result.reward_id 等于本次请求的 reward_id；矛盾响应按连接数据错误处理 | 合成损坏响应确认；正常游戏尚未观察到错报；已修复，约定验证通过 |

前两项属于已记录的[错误恢复与诊断待办](../development/TODO.md#当前工具审阅结束后处理)。普通领取、满药水槽、卡牌选择与嵌套奖励的正常结果另列如下，避免把这些预期行为算作故障。

## 当前参数与行为

| 参数 | 当前含义 |
| --- | --- |
| reward_id | 必填 0–2147483647 整数，取当前 get_observation 或 inspect_rewards 的 rewards.items[].id |
| preset | default 为默认；full 保留普通 null。两者均返回动作回执 |

奖励 ID 标识奖励对象，领取其他条目后保持稳定。点击一行后，由原生流程处理取得物品、打开选牌、弹出后续奖励等行为。画面外的奖励会先滚动到可点击位置。

结果包含 scene、screen、available_actions、transition 和 reward_result；遇到选牌时还包含 selection 的 type/status。具体候选通过 inspect_selection 查看，其他页面内容通过对应查看工具获取。

reward_result.status 的含义：

| 值 | 含义 |
| --- | --- |
| claimed | 原生流程确认该奖励领取结束 |
| not_claimed | 原生流程拒绝领取，例如药水槽已满，奖励行仍保留 |
| not_obtained | 药水奖励行被消耗，但药水获取被阻止，例如添水的效果 |
| pending | 领取仍等待后续处理，例如卡牌选择，或遗物引出的另一张奖励页 |

transition.complete 表示已到达 stop_reason 所述边界。因此 pending 可以与 choice_required 同时出现；遗物打开新奖励页时，也可以与 action_completed 同时出现。模型应继续处理当前页面。

## 典型场景

| 场景 | 当前处理 |
| --- | --- |
| 金币、药水、普通遗物、指定卡牌 | 返回领取结果及可见变化事件；卡牌加入牌组的事件带 pile:deck |
| 普通卡牌奖励 | 停在 choice_required，reward_result 为 pending；后续选牌通过选择工具完成 |
| 卡牌奖励点击 Skip | 返回奖励列表，通常保留该入口，可以再次打开；Skip 的回执由 selection_option 返回 |
| 药水槽满 | 返回 not_claimed；可直接丢弃已有药水，再领取同一奖励 |
| 互斥奖励 | 领取一项后，其余同组奖励由原生界面移除 |
| 遗物引出嵌套奖励或变牌 | 返回新奖励页或选牌边界，等待继续处理 |
| 追回被偷的卡牌 | 沿指定卡牌奖励流程加入牌组并记录事件 |
| 地图、牌组、当前选择覆盖奖励页 | 拒绝领取；当前错误原因和恢复行为有上表缺口 |

## 已确认方案

保留 reward_id 和 default/full，以及现有精简动作回执。它已经提供领取结果、可见变化和下一步操作，新增 summary 的精简收益很小。

小范围重构可集中处理“当前能否领取及原因”，供实际执行和 available_actions 复用；领取前的滚动与点击明确划定交互开始位置。返回 ID 的核对放在响应校验入口。修复覆盖三项问题及这部分小范围重构。

## 修复后样本

[18 份完整新返回](2026-11-05-claim-reward-fixed-examples/README.md)展示具体拒绝、直接续接及滚动后必须观察，并保留正常领取结构。

## 审阅基线 JSON 与验证范围

[15 份完整返回及调用参数](2026-11-05-claim-reward-examples/README.md)来自真实 GUI，包含 14 份 full 和 1 份 default。建议先看：

- [金币与互斥奖励](2026-11-05-claim-reward-examples/gold-linked.full.json)、[取得药水](2026-11-05-claim-reward-examples/potion.full.json)、[取得遗物并升级卡牌](2026-11-05-claim-reward-examples/relic.full.json)。
- [打开卡牌选择](2026-11-05-claim-reward-examples/card-choice.full.json)、[满药水槽](2026-11-05-claim-reward-examples/full-belt.full.json)、[打开嵌套奖励](2026-11-05-claim-reward-examples/nested-rewards.full.json)。
- [重复领取被拒绝](2026-11-05-claim-reward-examples/already-claimed.full.json)及[随后合法领取仍被要求观察](2026-11-05-claim-reward-examples/after-rejection.full.json)。

not_obtained 已核对目标版本的原生分支及现有 Python 回执检查，尚未在该专项中新增添水实际领取样本。移除卡牌奖励、未知第三方奖励、多人及所有遗物组合不作穷举。
