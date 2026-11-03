# inspect_hand 场景与现有预设核验

> 当前状态：设计讨论中。现状核验已完成 11 个隔离测试局及菜单读取，导出 26 份真实返回和 1 份明确标注的控制输入示例。已补充 Affliction 源码与资源核对、共享卡牌模式、兼容迁移及手牌资源的候选契约；后续实施优先处理 Affliction 和小范围重构。HAND-01 的实际画面读取仍待 GUI 验证，共用入口迁移尚未实施。尚未修改玩法行为，不核销工具；暂无调研阻塞。完整清单及流程见[工具核验记录](2026-11-02-mcp-tool-review.md)。

## 优先关注的问题

| 编号 | 优先级与状态 | 影响及证据 | 建议处理范围 |
| --- | --- | --- | --- |
| HAND-01 | 中；已确认字段缺口，具体外观范围待 GUI 核验；未修复 | 游戏的 AfflictionModel 与 EnchantmentModel 是两类独立效果。NCard.ReloadOverlay 会为有资源的 Affliction 绘制覆盖外观，CardModel.GetDescriptionForPile/HoverTips 提供其文字；当前 CombatObservation.Card 和 Python CARD、共用 card_summary 都没有对应外观字段。因此 full 可从正文／悬停提示读到效果，summary 及基础手牌观察却无法表达这些牌面外观。不能因附魔已支持就认为全部特殊牌面状态已覆盖 | 先核对实际可见覆盖外观及其可识别身份，再确定是否补充共享卡牌字段；同步基础观察、手牌、选择等调用方。不直接输出模型 Amount，也不假定所有 Affliction 都有可见覆盖外观 |

没有证据表明当前参数筛选或共享提示合并存在错误。未知／锁定牌、目标预览、动作过渡等未新实测的分支属于验证边界，不据此判为缺陷。`unplayable_markers` 的名称容易引起误读，实际是可见禁用图标的位置，下面单独说明；不是已确认的错误采样。

需要关注的小范围重构：基础观察和 inspect_hand 在两个位置重复枚举 ActiveHolders 并过滤可读牌面，后续改动可能造成 ID／候选不一致。建议在需要修改采样时提取共用手牌枚举入口，保留 HandInspection 只负责附加正文及悬停提示的职责。Python 的 card_summary 已集中复用，无须为本轮新增第二套摘要实现。

## 核对基线与证据

- 核验日期：2026-11-03；代码提交 `0a4fd89`，Mod `0.50.0`、MCP `0.51.0`、原生 schema `33`。本记录保留这次基线，当前版本统一见[项目 README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`、release、build `59260271`；RitsuLib `0.6.10` 的该游戏兼容包。程序集为游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 当前构建与隔离运行时 DLL 相同，SHA-256 为 `eedee2ff5b7ba98325f8b42bf03fe19767094ba8fa0b807864820ee59ca80e30`。使用中文 UI、独立测试存档与 IPC；场景夹具可准备特殊手牌、20 点能量或铁甲战士耗星等状态，样本不是正常开局配置。
- 原生入口：[GameAdapter](../../src/Sts2Agent/Adapter/GameAdapter.cs) 的 inspect_hand 分支、[CanInspectHand 与 available_actions](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[HandInspection.Card](../../src/Sts2Agent/Observation/HandInspection.cs)、[CombatObservation.Card/CardVisible/VisibleEnchantment](../../src/Sts2Agent/Observation/CombatObservation.cs)、[HoverTipText](../../src/Sts2Agent/Localization/HoverTipText.cs)、[VisibleUi](../../src/Sts2Agent/Observation/VisibleUi.cs)。
- MCP：[工具注册](../../src/sts2_mcp/mcp_catalog.py)、[工具派发](../../src/sts2_mcp/game_tools.py)、[完整手牌校验](../../src/sts2_mcp/output/game_output.py)、[提示合并](../../src/sts2_mcp/output/player_output.py)、[手牌预设与筛选](../../src/sts2_mcp/output/hand_presets.py)、[共享卡牌摘要](../../src/sts2_mcp/output/card_summary.py)、[公共预设包装](../../src/sts2_mcp/output/presets.py)。现行契约见[手牌接口](../development/hand-inspection.md)。
- 本次从目标程序集重新反编译：NPlayerHand.ActiveHolders/InCardPlay/RefreshLayout、NCard.UpdateVisuals/UpdateEnergyCostVisuals/UpdateStarCostVisuals/ReloadOverlay、CardModel.GetDescriptionForPile/HoverTips、CardPile.MaxCardsInHand、HandPosHelper、CardCostHelper、AfflictionModel 及内置 Affliction。证据保存在 `.tmp/2026-11-03-inspect-hand-review/`，不纳入 Git。

## 当前参数与返回结构

```json
{"preset":"full"}
```

| 参数 | 当前行为 |
| --- | --- |
| `preset` | 可选，默认 default；支持 default/full/summary。default 是完整内容按公共规则省略普通 null，full 保留已有 null，summary 使用共用卡牌摘要 |
| `card_ids` | 可选的非负整数数组，范围 0–2147483647；不是位置或牌组／牌堆 ID。省略表示全部当前可读手牌，空数组返回空结果；去重并保留原生手牌顺序 |

参数由 MCP 处理，原生文件 inspect_hand 无参数；所有预设与空筛选先读取并校验完整手牌，不修改界面，也不跳过未命中卡牌的格式校验。非法参数整次 `invalid_request`；不在当前手牌或不可读的 ID 合并到 `errors:[{code:"cards_not_in_hand",card_ids:[...]}]`，仍返回有效卡牌且 MCP isError 为 false。普通底层失败仍为顶层 error，不能当作空手牌。

成功的 full 主体是 `hand`、`hover_tips`，手牌非空时增加 `notes.card_values`。每张牌包含实际存在的基础身份、费用、颜色、标记、描边、可见附魔及正文；悬停提示提到顶层，按标题和正文同时相同合并，并记录关联 card_ids。筛选同步裁剪提示关联，不能附送被筛出卡牌的独有解释。

本工具此前没有 scene，本次场景统一没有给它新增 scene/screen；也不返回 available_actions、敌人、资源总量或 transition。当前可用动作通过 get_observation 查看。成功读取可直接用于下一步动作许可，不要求固定先调用 get_observation。

### full 中哪些字段也可能不存在

- 无附魔时，**即使 full 也没有 enchantment 字段**：游戏端只在实际显示且可识别时添加它，没有先生成 `enchantment:null`。这是字段生成规则，不是 null 过滤。
- 普通费用颜色不额外返回，只有实际存在的特殊颜色才有 energy_cost_color/star_cost_color。
- 附魔图标不显示计数时没有 amount；不从模型内部 Amount 补齐。dimmed 记录实际置灰表现，false 也保留。
- full 的 star_cost 可以为 null；default 和 summary 在无显示耗星时省略。空数组、outline:none 等只按已定义的 summary 规则省略，不因 default 自动删除。

### 当前 summary

共用 card_summary 保留 `id/name/type/energy_cost`、实际显示的 star_cost、特殊费用颜色、非空 unplayable_markers、有颜色的 outline、可见 enchantment。随后按 default 规则省略普通 null。

它省略正文、稀有度、外观卡池、共享悬停提示和 notes.card_values；不补 can_play 或任何效果预测。切回战场仍待选牌时，notes.selection 保留；hand 为空也不能删掉该导航说明。详细字段不在本报告另作新定义，以[当前手牌接口](../development/hand-inspection.md#参数与返回范围)为准。

## 可用场景与读取边界

本工具的原生门控是：战斗画面实际可见、手牌容器存在且显示、当前不在拖动／打出卡牌流程中。**没有额外要求当前必须是玩家回合**；但读取成功不代表允许出牌，动作仍单独校验。本轮不把战斗背景强行解释为 scene:combat。

| 状态 | 当前行为与原因 |
| --- | --- |
| 无覆盖的手牌、满手十张、费用不足、条件不可打出、附魔／升级／特殊费用 | 都使用同一成功结构，只改变实际牌面内容 |
| 正常可读的空手牌 | 成功，full 为 hand:[] 和 hover_tips:[]；无卡牌数值 note |
| 卡牌选择页在前景 | 拒绝，候选应使用 inspect_selection |
| 通过眼睛切回战场 | 可读取此时仍显示的手牌；增加 notes.selection，已离手的牌不再命中 |
| 地图、牌组、牌堆或模态弹窗覆盖战斗 | 拒绝；不穿透页面读取手牌，也不自动关闭覆盖 |
| 菜单、事件等没有可读手牌的房间 | 拒绝；不是成功空手牌 |
| 容器未就绪／隐藏、加载过渡或正在拖动／打牌 | 拒绝；本轮不承诺所有动画瞬间可读取 |
| 未知／锁定牌 | 防御性分支不补真实类型、稀有度、卡池、正文和解释；不是正常手牌的已复现场景。目标 NCard 源码注明对局内通常都是 Visible |

手牌不是原生滚动列表。目标版本 MaxCardsInHand 为 10，HandPosHelper 为 1–10 张提供扇形布局；当前仍按可见节点、视口和裁剪读取。本轮十张实测全部返回，没有观察到正常上限手牌被截断；也不能把当前容器中隐藏的候选当作手牌补出，或按此前“完整可浏览列表”的规则穿透覆盖。

### 标记、费用与数值

- energy_cost/star_cost 是 UI 字符串，不是待消费的整数，允许 X、问号以及不可读时的 null。隐藏费用图标不从模型补零。
- `unplayable_markers:["energy"]` 表示能量图标上的禁用标记，**不表示已判定能量不足**。原生 NCard 只在不可打出原因不含资源原因时显示这类标记；资源不足通常体现为费用红色。不能由空标记或 cyan 描边推导合法出牌。
- 正文使用当前卡牌已有动态预览及实际目标上下文；不为每个敌人重算，不模拟伤害，也不直接调用 UpdateVisuals 刷新 UI。悬停解释复用原生 HoverTips；附魔和 Affliction 的文字可随此返回。
- 升级显示由实际名称后缀保留；不额外泄露隐藏升级层数。可见附魔的计数来自标签，置灰来自图标材质，而非直接转发模型状态。

## 各分支完整返回示例

除参数错误、筛选示例及明确标注的控制输入外，以下均为实际 `inspect_hand({"preset":"full"})` 的完整返回，没有删字段或省略号。调用参数、真实／控制输入来源、MCP isError 和原始证据数组下标见 [manifest.json](2026-11-03-inspect-hand-examples/manifest.json)。常见房间没有不同的成功手牌结构，因此按内容变体及门控分支列出，不人为复制每个非战斗房间的相同错误。

| 场景或状态 | 完整 full 返回 | 要点 |
| --- | --- | --- |
| 普通手牌 | [basic](2026-11-03-inspect-hand-examples/basic.full.json) | 两张不同 ID 的 Strike 不合并；Block 解释只关联 Defend |
| 显示耗星但星星不足 | [stars](2026-11-03-inspect-hand-examples/stars.full.json) | 第一张 star_cost 为字符串 2，star_cost_color:red，标记数组仍为空 |
| X 费用 | [x-cost](2026-11-03-inspect-hand-examples/x-cost.full.json) | Whirlwind 保留 X 和完整正文 |
| 升级牌与普通牌混合 | [upgraded](2026-11-03-inspect-hand-examples/upgraded.full.json) | 升级名称和动态正文、解释正常显示 |
| 多种附魔、置灰与不显示计数 | [enchantments](2026-11-03-inspect-hand-examples/enchantments.full.json) | Sharp:3、Swift:2 且置灰；Clone、Spiral 没有 amount；第六张为 Defend+ 与 Spiral |
| 能量为零 | [energy](2026-11-03-inspect-hand-examples/energy.full.json) | 费用为红色，unplayable_markers:[]；不能按空标记判为可打出 |
| 无能量图标的不可打出牌 | [unplayable](2026-11-03-inspect-hand-examples/unplayable.full.json) | Dazed 的 energy_cost:null，正文仍有 Unplayable/Ethereal 及对应悬停解释 |
| 因牌自身条件不能打出 | [card-condition](2026-11-03-inspect-hand-examples/card-condition.full.json) | Grand Finale 费用 0，有 energy 位置禁用标记；不是能量不足 |
| 正常最大十张手牌 | [ten-cards](2026-11-03-inspect-hand-examples/ten-cards.full.json) | 十张均返回；重复 Block 提示合并关联到多张牌，Shiv 卡牌预览转成标题和正文 |
| 即将进入选择的免费武装 | [selection](2026-11-03-inspect-hand-examples/selection.full.json) | 当前仍是普通手牌，费用为 0 且有特殊颜色 |
| 选择期间切回战场 | [selection-battlefield](2026-11-03-inspect-hand-examples/selection-battlefield.full.json) | 已打出的 Armaments 不在手牌；同时有选择导航与数值预览 notes |
| 正常可读的空手牌 | [empty-hand](2026-11-03-inspect-hand-examples/empty-hand.full.json) | 真正逐张打完三张基本牌取得；不是通过空筛选冒充 |
| 有效、重复和无效 ID 混合 | [mixed-filter](2026-11-03-inspect-hand-examples/mixed-filter.full.json) | 参数为 card_ids:[7,5,5,2147483647]，结果按手牌顺序返回 5、7，保留合并错误；无关 Block 提示不附送 |
| ID 全无效／空筛选 | [all-missing](2026-11-03-inspect-hand-examples/all-missing.full.json)、[empty-filter](2026-11-03-inspect-hand-examples/empty-filter.full.json) | 都是成功空结果，前者有 errors，后者无错误；都不是底层拒绝 |
| 选择页尚在前景 | [selection-blocked](2026-11-03-inspect-hand-examples/selection-blocked.full.json) | 顶层 illegal_action，不返回候选或手牌 |
| 地图／牌组／弃牌堆覆盖 | [map-blocked](2026-11-03-inspect-hand-examples/map-blocked.full.json)、[deck-blocked](2026-11-03-inspect-hand-examples/deck-blocked.full.json)、[pile-blocked](2026-11-03-inspect-hand-examples/pile-blocked.full.json) | 都没有广告 inspect_hand，调用也拒绝 |
| 主菜单／事件房间 | [main-menu](2026-11-03-inspect-hand-examples/main-menu.full.json)、[event](2026-11-03-inspect-hand-examples/event.full.json) | 同样是拒绝，不将没有手牌的房间伪装成成功空数组 |
| 非法 ID 参数 | [invalid-ids](2026-11-03-inspect-hand-examples/invalid-ids.full.json) | card_ids:[true] 在 MCP 层拒绝，整次 invalid_request |
| 未识别牌的控制输入 | [unidentified.constructed](2026-11-03-inspect-hand-examples/unidentified.constructed.full.json) | **非 GUI 样本**；从现有 Python 测试输入投影，展示 nullable 身份、正文及空提示分支，不声称正常手牌会进入该状态 |

供对照的现有预设也保留完整真实输出：[普通 default](2026-11-03-inspect-hand-examples/basic.default.json)、[普通 summary](2026-11-03-inspect-hand-examples/basic.summary.json)、[附魔 summary](2026-11-03-inspect-hand-examples/enchantments.summary.json)、[切回战场 summary](2026-11-03-inspect-hand-examples/selection-battlefield.summary.json)。这些是当前行为，不是本次提出的新摘要。

## 验证结果与未覆盖范围

- 单个自有游戏进程执行 11 个不同测试局，全部完成读取及原生测试局清理；另在开局前读取菜单。共 100 次真实 stdio MCP 返回，其中 56 次 inspect_hand；游戏进程 PID 26237 已关闭。
- 对十个成功手牌内容变体检查 full 重复读取一致、default 等于 full 的公共空值投影、summary 等于共享卡牌投影、ID 和顺序与基础观察一致。十组读前／后原生状态完整相等，原始证据中保留两份状态；选择期间切回战场的读取也另做相等断言。
- 正常最大十张实际全部返回，人工查看十张扇形布局截图；另查看附魔、零能量和条件不可打出的截图，核对费用颜色、禁用图标与可见附魔外观。
- 现有 `tests.python.test_hand_presets` 的 12 项全部通过，包括参数、筛选、合并错误、权限、损坏响应和真实 stdio；日志在 `.tmp/2026-11-03-inspect-hand-review/python-hand.log`。本轮没有修改 C# 或运行时，不重复编译或宣称新增机制已验证。
- 样本与统计在 `.tmp/2026-11-03-inspect-hand-review/sampling-complete/` 和 `coverage.json`。导出时核对每份真实 JSON 与所指证据下标完全一致；控制输入示例单独标记。
- 首次采样 `sampling/` 在预期非法读取后没有重新取得动作许可便关闭地图，第二次 `sampling-final/` 又假定测试局的强制首张地图可以关闭，均在采样脚本断言中止。原始证据与失败目录保留；最终脚本将强制地图读取放到该局最后，按原生规则重开局采样，没有修改玩法代码或重试被拒绝的关闭动作。
- Affliction 的实际覆盖资源、隐藏／透明变体、未知／锁定牌的原生手牌、所有耗星／问号组合、瞄准某个敌人及敌人回合瞬时窗口没有在本轮 GUI 逐一复现。已有源码或控制输入的覆盖不能替代这些实测，不将其写成已修复或完整覆盖。

## 设计讨论入口

现有 summary 已与基础观察及其他卡牌摘要复用，现有 card_ids 也已满足按当前 ID 聚焦。建议以保持这些参数和结构为起点；没有必要为完成核验重复新增同类预设或筛选。

优先讨论 HAND-01 的实际 UI 范围和共享字段，再决定是否需要调整摘要。可选方向有：维持现状并在需要时读取 full；在共享摘要中补充经 UI 核实的 Affliction 身份；或为手牌另做更细分的输出参数。建议第二种，能让其他共用卡牌摘要同时受益，避免多套字段逐渐分歧。是否显示计数、没有专用外观时如何处理，仍须逐类核对，不在本轮直接定稿。

本轮不修改用户维护的 TODO.md；本项未修复问题在本报告跟进。

## 共享卡牌输出与手牌资源的候选契约

本节记录后续设计讨论，**尚未实现或整体定稿**；上面的现状与原始样本保持不变。

### Affliction 与附魔空值

源码与资源已确认：`ChainsOfBindingPower`（魂缚锁链）施加 `Bound`（魂缚），`SmoggyPower`（烟雾弥漫）施加 `Smog`（烟雾）。`CardModel.Affliction` 是单个可空对象，独立于同样可空的 Enchantment。七种内置 Affliction 都有对应覆盖场景，场景节点中没有 Label 或 RichTextLabel 计数；不能直接转发模型 Amount。

本轮补充证据在 `.tmp/2026-11-03-card-presentation-design/`：目标程序集的两个 Power 反编译、资源只读探针 `resources.gd` 与输出 `resources.json`。资源来自 `res://localization/{zhs,eng}/{powers,afflictions}.json` 的对应 title 条目，以及 `res://scenes/cards/overlays/afflictions/{bound,entangled,galvanized,hexed,ringing,smog,tainted}.tscn`。探针在隔离数据目录的无界面进程中读取并实例化场景，没有进入对局；它确认资源及节点结构，不能替代实际手牌外观采样验证。无界面音频和 Sentry 初始化日志未影响资源输出，不据此宣称实战 UI 已验证。

候选规则：

- 统一使用单数 `affliction`，full 的无可读效果值为 null，不使用空数组。有实际可识别覆盖外观时为 `{"name":"Bound"}`；summary 只保留其身份，效果文字仍由 full 的正文／悬停解释提供。
- full 与 face_full 的卡牌均显式生成 `enchantment:null` 和 `affliction:null`；未知牌或不可识别效果不补真实身份。default、face_default 和 summary 的普通卡牌省略空值。这两项是已提出的行为调整，与保持其他既有字段不变的重构分开验证。
- 不新增 Affliction 的 amount 或 dimmed：当前资源没有对应计数，Affliction 也没有附魔式 Disabled 显示契约。Enchantment 继续保留原有可见计数与置灰规则。
- 附魔与 Affliction 可同时存在，分别返回；不能二选一覆盖。
- 比较预览和 transition 中的 null 仍遵循既有特殊规则：例如去掉附着效果时，before/after 的差异不能被普通卡牌压缩丢失。共用格式化应保留上下文，再由统一空值入口决定例外，不能在单牌函数中提前递归删 null。

### 共用模式及分层

建议使用五种**内部卡牌模式**，不为每个工具新增 face_full 等公开 preset 参数。工具的 preset 与内部卡牌模式分开映射，场景继续决定允许取得哪些事实。模式由 summary／face／详情三种内容范围和保留／过滤 null 两种策略组合；不要求每种来源生成字段齐全且完全相同的对象。

| 内部模式 | 内容与职责 |
| --- | --- |
| `summary` | 现有共享摘要字段，加经 UI 核实的 affliction；省略普通 null、空禁用标记和无描边。既有比较例外在外层统一处理 |
| `full` | 允许专门查看的完整卡面身份、外观、正文和悬停解释，保留 null；实际费用和正文仍使用当前页面与目标上下文 |
| `face_full` | 来源已提供的卡牌身份、外观及允许提供的正文，保留 null；半隐藏手牌无正文，展开的选牌及结算卡可有正文，不附送悬停解释。模式本身不决定正文是否可读 |
| `default` | full 内容经统一 default 空值规则处理 |
| `face_default` | face_full 内容经同一 default 空值规则处理 |

游戏端共用可见牌面读取入口，保留实际 NCard 与可滚动网格的上下文克隆两种数据来源；MCP 端共用卡牌结构和字段投影入口。卡牌格式化不能自己决定某张牌是否已揭示、打开新页面、刷新持有卡牌数值，或把手牌费用应用到牌组／升级预览。summary 同样只压缩已允许提供的内容。

需要合并的重复逻辑包括 CombatObservation.Card、HandInspection.Card、SelectionInspection.Card、BrowsedCard.Read 的牌面字段及正文处理，以及 Python 的 CARD/HAND_CARD/BROWSED_CARD/SHOP_CARD 和 card_summary。已有的手牌枚举重复也纳入同一局部重构；不把工具动作、候选排序、地图或页面合法性搬进卡牌格式化。

### 接入场景及需保留的区别

| 调用位置 | 五种模式的适配与额外上下文 |
| --- | --- |
| inspect_hand | 直接使用 full/default/summary；ID 为当前手牌整数，保持原顺序 |
| get_observation、动作回执中的手牌 | 使用 face_full/face_default/summary，保持半隐藏手牌信息边界 |
| get_observation 中的候选、卡包、升级／附魔／变牌比较、结算卡 | 也可共用入口；当前已展开的正文在 face 模式中保留。before/after、random、bundle ID、选中状态等由选择容器处理 |
| inspect_selection、inspect_run_result 中的完整牌面 | 使用 full/default，已有 summary 的位置使用共享 summary；不因共用入口给 inspect_run_result 自动新增公开 summary |
| inspect_deck、inspect_pile | 有独立 detail_level，其现有 summary 保留稀有度／卡池，且缺少共享摘要的若干外观字段，与这里的 summary 不同。可复用基础读取，但公开 detail_level 的最终映射留待对应工具核验，不能悄悄替换已有语义 |
| 商店卡牌 | 卡面可复用，购买 ID 位于外层商品项，不能为 card 内造手牌 ID；价格、折扣、可买状态留在商品容器。基础观察继续按已确认约定不附正文，inspect_shop 的专门查看可有正文 |
| 事件、先古之民、奖励的选牌 | 已打开的真实候选走上述选择模式；尚未展开的选项提及或奖励名称只作为引用，不自动扩成牌面 |

以下内容不属于五种完整牌面类别，保留轻量表示：

- inspect_targets 的 card、transition 事件中的 card、基础观察的悬浮君王之剑等 `id/name` 引用。共用身份提取即可，不能借改造附送费用或正文。
- CardHoverTip 已转成的 `title/description` 文本预览：没有本次可操作卡牌 ID，也不是候选，不改成完整牌面对象。
- 顶层共享 hover_tips、notes、错误、排序、筛选与选择元数据。各工具保留现有容器结构及关联方式；手牌的共享 card_ids 可以是整数，浏览卡牌是字符串 ID，商店则保留自己的商品关联，不能强行混用。

### 兼容迁移与旧牌组／牌堆摘要

就当前标准牌面字段而言，上述模式可以无损覆盖现有情况；条件是统一允许的字段及投影逻辑，同时保留来源已采集的字段集合与上下文。**五种模式不是五套必须补齐字段的固定对象**。格式化只处理传入的已允许事实，不新增正文、不把缺失外观补成无效果、不改写 ID 类型、不重新计算当前牌值；已明确提出的 Affliction 新增和附魔 null 规范化作为功能变化单独处理。

当前各路径可作如下兼容映射：

| 现有卡牌路径 | 内部模式 | 必须保留的现状 |
| --- | --- | --- |
| 基础观察中的手牌 | face_full／face_default | 不生成正文；保留当前费用与外观 |
| 基础观察中的选牌、比较、结算牌 | face_full／face_default | 已采集的正文继续存在；缺失或 null 正文保留各自含义 |
| 专门手牌、选牌、结算卡详情 | full／default | 保留已允许的正文、悬停解释与各自关联方式 |
| 商店基础卡牌／详情 | face_full／face_default 或 full／default | 沿用原有六个基础字段及详情正文／提示，不增加卡内 ID；不附送原本被排除的外观 |
| 牌组／牌堆旧 detail_level:summary | face_full／face_default | 保留旧七字段，既不删除稀有度／卡池，也不借重构新增外观 |
| 牌组／牌堆旧 detail_level:full | full／default | 保留旧七字段加正文和解释；不借重构给它们新增独立 summary 预设 |
| 现有真正使用共用卡牌摘要的路径 | summary | 保留既有摘要白名单与空标记／无描边省略规则 |

牌组／牌堆的公开 `detail_level` 与通用 `preset` 是两个独立参数。源码的 `browsed_cards` 在 summary 下严格保留：

```text
id, name, type, rarity, visual_card_pool, energy_cost, star_cost
```

以下是当前基线实际 `inspect_deck({"preset":"full"})` 返回中，一张牌的完整对象；detail_level 省略时为 summary：

```json
{
  "id": "deck:0",
  "name": "Strike",
  "type": "Attack",
  "rarity": "basic",
  "visual_card_pool": "ironclad",
  "energy_cost": "1",
  "star_cost": null
}
```

样本依据为 `.tmp/2026-11-03-ui-context-implementation/gui-final/combat/verify/evidence.json` 下标 25；该次原生 DLL 与本次代码基线相同，当前源码再次核对一致，不表示本轮重新启动了游戏。preset:default 仅使这个对象省略 star_cost:null，detail_level:full 则另增 description 和悬停解释。牌堆使用同样的七字段规则，ID 前缀为 pile:。

与 inspect_hand.summary 的差别不是只差正文：旧浏览 summary 保留 rarity 和 visual_card_pool，而手牌 summary 会省略；旧浏览 summary 还没有独立的 enchantment、费用颜色、禁用标记和描边。当前浏览 full 也只在旧七字段上增加正文／解释，附魔效果可存在于文字中，并不因此拥有结构化 enchantment。不能把旧 detail_level:summary 直接改成 card_summary，否则会同时删旧字段和增新字段。

迁移难点主要在采样，字段投影相对容易：Python 已有 CARD/HAND_CARD 的字段复用和集中 card_summary；原生侧却分别读取屏幕节点的现成动态值，以及按原生浏览规则格式化的隔离克隆。保留两种来源与牌堆／升级／目标上下文，让它们共用字段装配即可，不强行合并成重算所有卡牌的单一路径。

后续实施顺序已明确为：

1. 优先补 Affliction 的实际外观读取、空值语义和完整／摘要输出；结合已提出的附魔 null 规则验证。先完成相关真实 UI 和隐藏／未知边界验证。
2. 同阶段做直接相关的小范围重构：共用手牌枚举，以及卡牌附魔／Affliction 外观读取和字段装配。标准是复用读取规则，不扩大其他工具的信息范围。
3. 再逐步迁移其余卡牌输出与 inspect_hand 资源字段；每次用现有完整返回对照，除已明确批准的功能差异外保留字段、缺失／null、ID、正文、提示和容器语义。牌组／牌堆公开摘要的重新设计仍在对应工具核验时进行。

### inspect_hand 的资源信息

建议采用额外的顶层 energy、max_energy、stars，与 hand 筛选独立：即使 card_ids 为空或全部无效，成功读取仍返回当前可读资源。参数错误或底层非法读取继续只返回 error。

full 中 energy/max_energy 为可空整数，stars 为可空整数。default 仅省略不可读空值；summary 与 get_observation.summary 一致，将成对可读能量合为字符串 energy，例如 `3/3`，并省略 max_energy；stars 可见时保留整数，包括 0。部分能量不可读时沿用现行 summary 行为省略能量，不从模型补值。

游戏端提取共用战斗资源采样，MCP 端提取共用资源摘要逻辑，避免两处分别读取／拼接。资源来自当前显示的能量计和星星计，不依赖整个 player 对象或角色身体是否可读，也不因职业身份推断星星为 0。

建议的成功结果骨架如下；这是设计示例，不是实测返回：

```json
{
  "energy": 3,
  "max_energy": 3,
  "stars": null,
  "hand": [],
  "hover_tips": []
}
```

对应 summary：

```json
{
  "energy": "3/3",
  "hand": []
}
```

以上共享入口、特殊调用位置的适配范围及资源字段仍待本项定稿；本节记录不构成已经执行的迁移。
