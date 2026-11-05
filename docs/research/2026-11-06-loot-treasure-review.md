# loot_treasure 核验与参数建议

> 当前状态：现状核验完成，进入设计讨论。67 项 Python、十类 GUI、134 次 MCP 及 17 份完整返回已整理。待确认两项拒绝修复与保留现有参数的建议；尚未修改工具行为，本项尚未核销。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)；源码、问题编号与具体证据见[开发核验](2026-11-06-loot-treasure-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确未点击的拒绝仍会要求重新观察 | 中：已开箱又要求“只开箱”、空箱／已领取后再次领取、页面被覆盖等情况，在点击前被拒绝，下一次合法操作仍报 observation_required | 首次点击前明确拒绝时保留已有许可；已点击、过期、超时和未知结果仍要求观察 | 实测复现，待讨论修复 |
| 拒绝原因笼统 | 中：无宝箱房、覆盖、未就绪、已开箱、无遗物等情况，公开错误均为“操作不可用”，难以选择正确的恢复动作 | 提供具体原因；与可用工具列表共用开箱／领取判断 | 实测复现，待讨论修复 |

两项均属于已有[错误恢复与诊断待办](../development/TODO.md#当前工具审阅结束后处理)。目前未发现普通开箱重复发钱、越过选择自动领取、遗漏延迟遗物效果或空箱无法结束的问题。

## 当前参数与行为

| 参数 | 当前含义 |
| --- | --- |
| open_only | 布尔值，默认 false。true 只开一个关闭的宝箱；false 默认先开箱，再尝试领取，也可用于已开箱后的单独领取 |
| preset | default 为默认，full 保留普通空值；两者均返回精简动作回执 |

如果要先看遗物再决定拿取，使用 open_only:true，随后 inspect_treasure 查看，再选择 loot_treasure 或 proceed。已开箱再次传 true 会被拒绝。

成功结果包含 scene、screen、available_actions 和 transition；遇到选牌时另有 selection 的 type/status。宝箱和顶栏详情由对应查看工具提供，当前没有独立的 loot_result。

| 场景 | 当前返回与后续 |
| --- | --- |
| 普通默认开箱 | 先开箱，再领取遗物，返回金币和遗物事件；停留在宝箱房 |
| 只开箱 | 通常只有金币事件，遗物仍在界面上；其名称和效果通过 inspect_treasure 查看 |
| 领取已打开的宝箱遗物 | 返回遗物事件；不会再次结算开箱金币 |
| 空箱 | 正常返回 action_completed、complete:true、events:[]，可用操作包含 proceed；空事件不表示开箱失败 |
| 开箱途中出现额外奖励 | 停在奖励页。处理后游戏继续展示宝箱遗物，需要再次显式 loot_treasure；原请求不会继续执行第二次领取点击 |
| 遗物引出嵌套奖励 | 已记录获得遗物等可见变化，停在奖励页供后续处理 |
| 遗物引出变牌选择 | 返回 choice_required 与选择类型，后续使用选牌工具 |
| 遗物效果尚在进行 | 等待其效果、预览及稳定画面；人工延迟场景验证了效果打开地图后再增加金币的情形 |

complete 表示已到达 stop_reason 所述边界，奖励或选择仍可能等待输入。

## 典型完整返回

[17 份 JSON 与调用参数](2026-11-06-loot-treasure-examples/README.md)包含 16 份 full、一份 default，均来自真实图形实例。建议先看：

- [默认开箱并领取](2026-11-06-loot-treasure-examples/default-complete.full.json)、[只开箱](2026-11-06-loot-treasure-examples/open-only.full.json)、[空箱](2026-11-06-loot-treasure-examples/empty-chest.full.json)。
- [额外奖励中途返回](2026-11-06-loot-treasure-examples/extra-rewards.full.json)、[处理后显式领取](2026-11-06-loot-treasure-examples/explicit-take-after-extra.full.json)。
- [嵌套奖励](2026-11-06-loot-treasure-examples/nested-rewards.full.json)、[变牌选择](2026-11-06-loot-treasure-examples/card-choice.full.json)、[等待遗物延迟效果后返回地图](2026-11-06-loot-treasure-examples/map-after-obtain.full.json)。
- [已开箱拒绝](2026-11-06-loot-treasure-examples/already-open.full.json)与[随后合法领取被要求观察](2026-11-06-loot-treasure-examples/after-rejection.full.json)。

禁用／离屏／隐藏遗物及延迟打开地图均使用已有测试扰动；多人、教程、藏宝图与全部遗物组合未在该专项新增实测。超时及中途离开对局仅按源码和既有共用检查核对。

## 参数与小范围重构建议

建议保留 open_only、默认值及 default/full。当前回执已经精简，无需新增 summary 或筛选参数。

工具整体说明已提示后续奖励和选择另行处理；open_only 参数说明中的“false 也领取遗物”可进一步写准确：默认尝试开箱并领取，途中出现输入则返回，处理后若仍有遗物需再次调用。

小范围重构建议集中“本次点击宝箱还是遗物、为何不可用”的判断，供执行和 available_actions 共用，并与纯读取诊断分清。保留原生两次点击、同一总等待预算及中途停止规则；明确未执行保证只覆盖第一次点击之前。proceed 的独立审阅另行处理。
