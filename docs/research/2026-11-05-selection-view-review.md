# set_selection_view 审阅

> 当前状态：两项修复、成功输出精简及一次独立审查完成，已核销并合入 main。见[实施记录及 6 份典型新返回](2026-11-05-selection-view-results-implementation.md)。下文 8 个场景、62 项 Python 和 6 份旧 full 返回保留为审阅基线；执行见[实施计划](../superpowers/plans/2026-11-05-selection-view-results.md)。原证据及未测范围见[核验记录](2026-11-05-selection-view-development-notes.md)。

## 优先处理的问题

| 问题 | 影响 | 建议与状态 |
| --- | --- | --- |
| 未切换也会丢失已有观察许可 | 中。审阅基线中没有选择、页面被覆盖或眼睛不可用时，未点击也会阻止后续合法操作 | 已修复并验证；仅恢复已有许可，已交互、结果未知及切换期间选择改变仍须重新读取 |
| 对外错误无法区分原因 | 中。审阅基线的上述情况及切换期间选择改变均返回笼统提示 | 已提供固定公开原因并验证，不透传任意异常文字 |

## 当前用途与参数

这个工具点击当前选牌页面的原生眼睛，在候选与战场之间切换；不提交选择，不推进回合。只有原生眼睛当前可用时才可使用，包括重复请求当前视图的情况。非战斗选择和仅展示结果的页面可能没有可用的眼睛。

| 参数 | 当前行为 |
| --- | --- |
| `view` | 必填，`battlefield` 查看战场，`selection` 返回候选 |
| `preset` | 默认 `default`，另有 `full`；目前没有 `summary` |

它不要求先有观察许可：成功切换或成功读取已经处于的视图，会提供当前状态并允许随后合法操作。重复请求当前视图不会再次点击。不能把查看战场理解为结束选牌，或据此执行出牌、结束回合等普通战斗操作。

## 已核对的场景

| 场景 | 实际行为或核对重点 |
| --- | --- |
| 战斗中的弹出候选页 | 眼睛隐藏候选并显示战场；返回后仍是原选择 |
| 普通网格已有选中项 | 查看战场时不提供隐藏候选和已选列表；返回后选中项和候选保持 |
| 手牌升级已有预览 | 眼睛隐藏选择与比较；返回后仍保留同一张待升级卡及已经展开的比较 |
| 重复请求当前视图 | 返回当前观察，不重复点击或切回另一视图 |
| 牌组或地图覆盖选择 | 先拒绝切换；关闭对应覆盖页后才能返回候选 |
| 非战斗锻造、结果展示页 | 无可用原生眼睛时拒绝，`view:"selection"` 也不会绕过这个前提 |
| 没有选择、本地参数错误 | 无选择被原生拒绝；错误枚举等在本地拒绝。审阅基线前者丢失已有许可，后者保留已有许可 |

审阅基线的典型 full 返回保存在[旧样例目录](2026-11-05-selection-view-examples/README.md)。不按每种卡牌、选牌来源或相同错误重复生成样例；修复后内容见[新样例](2026-11-05-selection-view-fixed-examples/README.md)，实测与源码核对边界分别见开发记录。

| 典型 JSON | 代表范围 |
| --- | --- |
| [查看战场](2026-11-05-selection-view-examples/overlay-battlefield.full.json) | 不预先读取即可成功切换；候选隐藏，战场可见，选择仍待完成 |
| [返回候选](2026-11-05-selection-view-examples/overlay-selection.full.json) | 候选重新显示，底层房间被覆盖；可以直接继续选牌 |
| [返回手牌升级预览](2026-11-05-selection-view-examples/hand-upgrade-selection.full.json) | 已选项和升级比较保留，没有提前执行升级 |
| [没有选择](2026-11-05-selection-view-examples/no-selection.full.json) | 基线笼统错误及要求重新观察的恢复提示 |
| [牌组覆盖](2026-11-05-selection-view-examples/covered-deck.full.json) | 基线返回相同笼统错误，无法从 message 判断应先关闭覆盖页；地图覆盖为相同结构 |
| [锻造页眼睛不可用](2026-11-05-selection-view-examples/noncombat-eye-unavailable.full.json) | 基线中不能查看战场的页面也返回相同错误；结果页不重复同结构 JSON |

## 审阅基线返回

成功返回完整基础观察，包括 `scene`、`screen`、玩家、敌人、顶栏、当前选择、可用操作等；`full` 保留公共空值，`default` 按统一规则过滤。它没有 `transition`，不回放动作事件；卡牌升级或移除等效果仍在真正提交选择的调用中发生。

底层房间不因查看模式改变：战斗中仍是 `scene:"combat"`。查看战场时，`screen.status` 可以是 `visible`，同时 `selection.status` 是 `battlefield`，表明战场已显示但选择仍待完成；候选隐藏时 `cards`、`selected_ids` 等在 full 中为 null。返回候选时房间被选择页覆盖，`selection.status` 为 `visible`。这是房间和选择两个层面的状态，含义一致。

成功返回会刷新许可，所以返回候选后可以直接选牌或确认。完整画面和所需细节仍须按实际读取内容决策；许可并不保证任意参数或其他工具此刻合法。

## 设计定稿

修复上述两项错误处理，保留 `view` 的取值、不要求初始观察、重复目标不点击、选择状态保留等行为。前置诊断和原生切换流程拆成小入口，与可用操作判断保持一致；不把“战场可查看”套用为候选可点击的条件。

成功输出与 `close_card_view` 一样，使用 `get_observation.actions_only` 所含内容：

| 字段 | 内容 |
| --- | --- |
| `scene`、`screen` | 原房间和当前显示／覆盖状态 |
| `available_actions` | 当前合法操作和查看工具 |
| `selection` | 当前选择的 `type`、`status` |

继续保留 default/full，不增加 summary 或 actions_only 参数，不带 transition。完整新画面由 `get_observation` 或详情读取；底层完整解码与许可刷新不因公共结果精简而改变。只提供典型新 JSON，原 6 份样例保留为旧行为证据。
