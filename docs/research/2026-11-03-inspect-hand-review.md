# inspect_hand 场景与现有预设核验

> 当前状态：设计范围已确认，字段例外清单已交付，待实施。现状核验已完成 11 个隔离测试局及菜单读取，导出 26 份真实返回和 1 份控制输入示例；新增一局当前版本悬浮剑实测。已确认 face 不含正文、展开牌 full/default 补悬停解释、牌组／牌堆改用 preset；[完整接入与例外清单](2026-11-03-card-format-coverage.md)已交付。实施优先处理 Affliction 和相关小范围重构，HAND-01 尚待实际画面读取验证。尚未修改玩法行为，不核销工具；暂无调研阻塞。完整流程见[工具核验记录](2026-11-02-mcp-tool-review.md)。

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

已确认保留现有卡牌摘要及 card_ids 筛选，补充 Affliction 和附魔空值一致性。共用格式覆盖、牌组／牌堆 preset 迁移及所有非牌面字段的明确归属见[字段清点](2026-11-03-card-format-coverage.md)。本轮不修改用户维护的 TODO.md，也不提前核销其他工具。

## 共享卡牌输出与手牌资源的候选契约

本节记录本项已确认的设计规则与实施范围，**尚未实现**；上面的现状与原始样本保持不变。非牌面字段的逐项核验另见[覆盖清单](2026-11-03-card-format-coverage.md)。

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

统一为以下五种内部卡牌模式，不增加新的公开 face 预设：

| 内部模式 | 内容与职责 |
| --- | --- |
| `summary` | 现有共享卡牌摘要，加经 UI 核实的 Affliction；不返回正文／解释 |
| `face_full` | 身份、费用和可读外观，保留 null；固定不返回 description 和 hover_tips |
| `face_default` | face_full 经统一 default 空值规则处理 |
| `full` | 完整牌面及允许查看的悬停解释，保留 null |
| `default` | full 经统一 default 空值规则处理 |

基础观察的半隐藏手牌与商店商品用 face；展开候选、比较和结算牌用 full/default，并按已确认要求增加此前没有的悬停解释。summary 继续共用，不增加“有正文但无解释”的临时模式。get_observation 和 inspect_selection 均已有公开 full/default/summary；inspect_run_result 仍只有 full/default，其卡牌接入对应内部模式，不提前新增该工具参数。

游戏端共用读取与字段装配，保留实际 NCard 和原生网格上下文克隆两种采样来源；Python 共用结构、字段投影及空值入口。读取仍遵守未知、隐藏、覆盖、目标、牌堆与升级预览边界。各工具保留 ID、顺序、选择容器和提示关联；比较两侧不能因同一原牌 ID 而被错误合并。

所有标准牌面接入点及不属于牌面预设的引用／提示／元数据已完整列于[覆盖清单](2026-11-03-card-format-coverage.md#全部标准牌面入口)，包括悬浮剑和其他例外的真实 JSON。不能仅改字段白名单而漏掉原生采样、比较解释或最后投影。

### 兼容迁移与旧牌组／牌堆摘要

当前旧 detail_level:summary 只返回 id/name/type/rarity/visual_card_pool/energy_cost/star_cost；full 在此基础上增加正文与解释，两个层级都没有完整的结构化外观。现状来源仍是[浏览校验](../../src/sts2_mcp/output/deck_details.py)及此前保存的真实样本。

已确认这轮移除 inspect_deck/inspect_pile 的 detail_level，改用 preset:full/default/summary，默认 default，并直接接入共用卡牌格式；原生公开字段、CLI、schema、校验、共享提示合并、测试和文档一并清理，不再为保留旧七字段摘要维护临时格式。详细参数及行为变化见[迁移范围](2026-11-03-card-format-coverage.md#牌组牌堆参数迁移范围)。

统一入口仍保留各场景的身份与数值上下文；Affliction、新空值规则、展开牌新增解释及浏览摘要变化是明确要求的功能调整，不能再承诺所有旧输出逐字段不变。后续实施优先完成 Affliction 和直接相关的小范围重构，再统一其余卡牌输出、迁移浏览参数并接入手牌资源。

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

上述规则尚未实施；具体非牌面字段和真实示例以[覆盖清单](2026-11-03-card-format-coverage.md)为依据，不能把设计记录当作已交付行为。
