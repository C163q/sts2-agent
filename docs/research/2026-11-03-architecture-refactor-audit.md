# 工具实现的结构审查与重构边界

本文是源码审查及候选设计，供[分阶段重构计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)使用；第 1–2 阶段已完成，见[实施记录](2026-11-04-refactor-stages-1-2.md)；下方问题表保留审查基线事实。已经确认的接口调整与仍应保持的差异分别列出，不把结构问题都当成已经复现的玩法故障。

## 结论与范围

建议暂停新增单个工具的参数设计，先收拢共用契约、输出转换、会话许可及原生请求处理。继续逐工具补分支会放大维护成本；直接重写全部工具则会丢失已经验证的 UI 与生命周期细节。推荐逐层替换实现，每阶段保持可运行并独立验证。

审查覆盖 43 个工具的公共分派及其共用链路，重点阅读 Python 参数／校验／投影／许可、原生观察／分派／响应／页面操作、事件作用域、可见性及本地化入口。不是对每种卡牌、事件或动画的完整游戏实测，也不替代后续逐工具内容核验。

核对基线：提交 `af1836d45940e4a21e4cd07baa0b2f0467b0c406`，Mod `0.53.0`、MCP `0.54.0`、观察 schema `34`，Linux 游戏 `v0.107.1`、RitsuLib `0.6.10`。程序集证据为游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。

本次只做源码与 Git 历史核对、静态依赖分析和文档编写，没有启动游戏、修改功能或安装 Mod。可复算的本机证据保留在被忽略的 `.tmp/2026-11-03-architecture-refactor/`，包括 `audit.py`、`static-audit.json` 及本次从目标程序集反编译的四个遗物／按钮类型；这些产物不纳入 Git。

## 集中问题清单

优先级表示重构顺序：P1 是正确性或职责边界风险，P2 是维护与契约一致性问题；不表示已经游戏复现。

| 编号 | 级别／性质 | 已核实的现状与影响 | 主要证据入口 | 计划归属 |
| --- | --- | --- | --- | --- |
| RF-01 | P1，职责混杂 | `GameAdapter.cs` 共 963 行，观察与代际维护、玩法路由、测试分派、浏览操作、等待、序列化混在一起。增加一个入口容易改动多个无关区域 | [GameAdapter](../../src/Sts2Agent/Adapter/GameAdapter.cs) 的 Observe／ExecuteCore／InspectMap／Success | 第 5 阶段 |
| RF-02 | P1，输出依赖 | Python 静态导入图包含一组 22 模块的强连通分量，包括函数内导入；详情模块向 `game_output` 取结构，后者再调用详情模块，投影又反向依赖预设／公开结果。不是“当前启动必然报循环导入”，但依赖方向已经不清楚 | [game_output](../../src/sts2_mcp/output/game_output.py)、[inspection_details](../../src/sts2_mcp/output/inspection_details.py)、[card_format](../../src/sts2_mcp/output/card_format.py)、[presets](../../src/sts2_mcp/output/presets.py) | 第 2 阶段 |
| RF-03 | P1，规则多处维护 | 工具 schema、专用 preset、工具分类、详情 reader、GameTools 方法及原生动作记录名单各自维护；包装器还用函数签名和工具名特判决定参数错误的处理 | [catalog](../../src/sts2_mcp/mcp_catalog.py)、[presets](../../src/sts2_mcp/output/presets.py)、[available_tools](../../src/sts2_mcp/output/available_tools.py)、[Resources](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs) | 第 3、5 阶段 |
| RF-04 | P1，恢复语义分散 | 已审阅的五个读取保留明确拒绝前的许可，其他读取仍清除；本地参数错误的具体说明和许可处理也不同。不能简单把所有 inspect 名称都当成纯读取：inspect_selection 可切换升级预览，地图与牌组查看也会改变 UI | [GameTools](../../src/sts2_mcp/game_tools.py) 的 PURE_READS／_inspect／_action／_change_view，及 [SelectionRequest](../../src/Sts2Agent/Adapter/GameAdapter.Selection.cs) | 第 3、4 阶段 |
| RF-05 | P1，媒体与执行结果耦合 | 原生 Success 遇到可见占卜会附加 PNG；MCP `_request` 校验图像后，动作才用 action_result 丢弃它。原生图片生成失败可返回 screenshot_unavailable，即使前面的按钮操作已经执行；这是已确认的控制流风险，尚未注入故障复现 | [Success](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[DivinationRequest](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)、[图像校验](../../src/sts2_mcp/output/divination_details.py)、[动作投影](../../src/sts2_mcp/output/action_output.py) | 第 4、5 阶段 |
| RF-06 | P2，重复转换 | 详情先校验／投影，再经大范围 GAMEPLAY 投影和 format_game_cards；部分位置根据 description／hover_tips 是否出现推断读取模式。字段是否保留同时受多个白名单影响 | [gameplay_fields](../../src/sts2_mcp/output/game_output.py)、[player_result](../../src/sts2_mcp/output/player_output.py)、[format_game_cards](../../src/sts2_mcp/output/card_format.py) | 第 2 阶段 |
| RF-07 | P2，成功上下文缺口 | hand／targets／potions／relics 的原生详情与公开结果缺少 scene/screen，其余主要详情已通过统一上下文入口生成 | [原生详情分支](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[CardPlayRequest](../../src/Sts2Agent/Adapter/GameAdapter.CardPlay.cs)、[PotionRequest](../../src/Sts2Agent/Adapter/GameAdapter.Potions.cs)、[inspection_details](../../src/sts2_mcp/output/inspection_details.py) | 第 5 阶段 |
| RF-08 | P2，历史引用规则不同 | 遗物筛选后的顶层 relic_indices 引用原列表，但提示里的同名字段引用本次压缩列表；combatants 来源始终引用未筛选列表。该遗物规则从提交 d24b1cd 引入，代码与文档相符，不能只认定为代码错误 | [relic_presets](../../src/sts2_mcp/output/relic_presets.py)、[combatant_presets](../../src/sts2_mcp/output/combatant_presets.py)、[遗物契约](../development/relic-inspection.md) | 第 3 阶段 |
| RF-09 | P2，可选筛选语义不同 | combatants.sources 接受 null；UI 的 sources、手牌／选牌的 card_ids、relic_indices 则拒绝显式 null。它们的省略与 [] 已分别表示全部和空集合 | 各 `*_presets.py` 的参数解析与 schema | 第 3 阶段 |
| RF-10 | P2，展示与悬停混用 | 遗物基础观察取 DisplayedHolders；inspect_relics 则取过滤 IsEnabled／MouseFilter 后的 VisibleHolders，summary 也继承该范围。整项消失还会改变后续下标。仅确认防御分支，未确认自然游玩触发 | [RelicInspection](../../src/Sts2Agent/Observation/RelicInspection.cs)、[原生检查](../../src/Sts2Agent/Testing/Checks/RelicInspectionChecks.cs) | 第 6 阶段 |
| RF-11 | P2，位置策略不完整 | 遗物列表已不按视口截断，但它的计数与 melted 仍调用带视口限制的 Number／OnScreen。战斗对象已有 Displayed 入口，其他区域仍有各自的位置、裁剪与悬停判断 | [RelicInspection](../../src/Sts2Agent/Observation/RelicInspection.cs)、[VisibleUi](../../src/Sts2Agent/Observation/VisibleUi.cs)、[UiInspection](../../src/Sts2Agent/Observation/UiInspection.cs)、[CombatObservation](../../src/Sts2Agent/Observation/CombatObservation.cs) | 第 6 阶段 |
| RF-12 | P2，事件／停止组装分散 | 各场景多次拼接 transition JSON，有的先写空 events 再由 ActionEventScope 替换；complete 与停止原因的构造散落。共享事件缓冲已存在，不应重写游戏事件追踪来解决组装重复 | [ActionEventScope](../../src/Sts2Agent/Events/ActionEventScope.cs)、[CombatJournalScope](../../src/Sts2Agent/Events/CombatJournalScope.cs)、各 GameAdapter 场景 partial | 第 5 阶段 |
| RF-13 | P2，客户端路径不一致 | MCP 总是先走 operation reader；文件 CLI 仅部分入口复用完整校验与 preset，其他入口直接 player_result。默认预设差异部分有明确历史契约，不能整体改成同一默认 | [roundtrip_client](../../src/sts2_mcp/roundtrip_client.py)、[GameTools._request](../../src/sts2_mcp/game_tools.py)、[边界测试](../../tests/python/test_output_boundaries.py) | 第 2、3 阶段 |
| RF-14 | P2，可用性与页面判定重复 | 已有 ObservationContext 与共用 Can* 谓词，但过渡遮挡、部分工具限制、场景动作判断仍重复；非战斗多处借用 TreasureInspection.Singleplayer，语义并不属于宝箱模块 | [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[CardSelection](../../src/Sts2Agent/Actions/CardSelection.cs)、[RunUi](../../src/Sts2Agent/Observation/RunUi.cs)、[ObservationContext](../../src/Sts2Agent/Observation/ObservationContext.cs) | 第 5、6 阶段 |

## 已向用户确认的契约调整

以下四项可纳入后续实现；其他重构默认保留外部行为。

1. **筛选引用**：统一指向当前未筛选列表；返回数组压缩时提供位置映射。遗物提示不再重编号成返回数组下标。既有 card_ids 仍用卡牌身份，药水仍用真实槽位，不为统一而改成位置身份。
2. **可选筛选**：省略或显式 null 表示全部，[] 表示不选任何条目；适用于上述 sources／card_ids／relic_indices，不扩展到必填参数、preset 或其他字段的 null。
3. **成功上下文**：所有玩法 JSON 工具成功结果均有同次快照的 scene/screen。详情不因此增加 available_actions；截图与原始诊断协议按各自职责保留。
4. **遗物不可悬停**：显示的静态条目保留；无法取得原生悬停说明时不生成说明，full/default 用 note 标明关联条目。summary 与 combatants 相同，只取静态信息，不尝试悬停。真正隐藏、透明、未揭示的内容继续排除。

第 4 项的“不可悬停”指 UI 控件状态，**不是 RelicStatus.Disabled**。本次从目标程序集核对：NRelicInventoryHolder.RefreshStatus 的 Disabled 仅置灰；OnFocus 仍生成原生说明。NClickableControl.RefreshFocus 根据控件是否启用、AllowFocusWhileDisabled 及鼠标／控制器焦点判定是否进入 OnFocus。项目测试主动禁用控件，不等于已经证明正常对局中存在这个时间窗口。note 不应把它解释为遗物失效、熔化、死亡或已知持续时间。

## 不能误当成历史错误的差异

| 差异 | 保留理由 |
| --- | --- |
| 工具的 full 与基础观察 full 内容不同 | full 是该工具的信息范围；基础手牌与商店概览不展开正文。卡牌 face 模式已有明确要求 |
| inspect_ui.summary 仍有 title/sources；combatants.summary 完全没有 hover_tips | 前者用于发现可查询帮助来源；后者表达未悬停的静态战斗数据，都是已经确认的设计 |
| UI sources 精确匹配；combatants sources 选择对象／分组 | 筛选的对象不同；只共用合法路径、去重、匹配、关联裁剪等基础设施，不能把 UI 参数偷偷改成任意对象选择 |
| 手牌整数 ID、deck:N／pile:N／card:N、商品外层 ID | 生命周期与操作权限不同；浏览身份不能被误用为出牌身份 |
| 基础观察包含生命／格挡／能量／手牌，combatants 不包含这些信息 | 公共读取器仅统一有相同可见语义的 powers／intents／orbs／blades 等片段 |
| selection.enchantment 用 title/description；卡面 enchantment 用 name/amount/dimmed | 前者是本次待施加效果说明，后者是牌面现有外观，不是同一个对象 |
| 卡牌悬停文字、剑的身份与 transition.card 不是完整牌面 | 只公开当前 UI 提供的身份或文本，不能补出费用、堆信息或隐藏属性 |
| 槽位 null、未知变牌结果 after:null、事件 before/after:null | 有结构或信息语义，继续使用共用 null 保留规则；不能全局删除空数组或 null |
| 操作按钮的可点击边界与可浏览内容的完整读取 | 读取全体可滚动候选不等于点击任意离屏控件。仍需原生滚动／入口、遮挡及生命周期核对 |

## 推荐结构

保留现有 Mod／文件传输／MCP 三层。只为已经重复的职责设共用入口，不增加服务、协议生成器、通用 JSONPath 或一套覆盖所有游戏模型的 DTO 框架。

- **纯数据契约**：类型、枚举、字段投影形状、引用与 null 规则，不导入会话、媒体附加或工具分派。领域校验器向下依赖这些契约，不反向导入总装配模块。
- **工具登记与请求规范化**：每个公开工具集中登记原生操作、参数规则、预设、读取器和输出投影。副作用、动作许可要求、transition 记录及 MCP annotations 分别表达，不能从单个“读／写”标志推导全部规则。展示 schema、服务分派和公共分类由登记读取；原生仍独立验证输入，以跨层测试防止漂移。
- **会话与错误恢复**：只处理串行化、控制器、调用开始时的许可、原生执行证据与后续许可；不负责裁剪卡牌或根据输出字段猜测请求类别。
- **输出流水线**：完整领域校验 → 按工具明确装配／去重帮助／生成 notes → 筛选／summary → 共用 default。许可只依赖未裁剪的、校验完成的执行结果；坏数据不能被空筛选隐藏。
- **原生快照与分派**：同步采样、场景／页面上下文、代际与令牌属于观察入口；游戏动作、页面操作、测试分派分别有入口。效果后等待和事件作用域保持现有生命周期。
- **共享 UI 片段**：同一区域先取得展示集合，再按需要读取悬停；手牌、顶栏、遗物、药水与战斗对象分别组合领域结果。可见性辅助只提供明确能力，不替领域决定未知内容是否可揭示。

媒体需求是请求的内部选项，不是 LLM 可见玩法字段；没有请求的图片不捕获／解码。需要图片的观察仍对同次媒体完整校验，不能以优化为由返回没有图像的“完整占卜观察”。

## 方案比较与实施边界

| 方案 | 取舍 |
| --- | --- |
| **推荐：分层迁移，共用契约先行** | 先消除循环依赖和规则分散，再迁移原生编排；同一阶段可对比新旧公开结果，单阶段可回退 |
| 继续逐工具小修 | 单次范围小，但错误、投影与上下文的重复不会消失，下一工具仍需再处理 |
| 一次性重写并全面统一字段 | 可直接清空历史形态，但高风险，且会混淆有意信息差异与历史遗留，不建议 |

重构不新增其他工具的 summary，不提前实现 TODO 中的地图／牌堆主体、占卜文字、商店上下文或知识库。公共错误机制属于本次重构范围，但用户保存的错误实测记录仍需日后对照，不能据此核销整项 TODO。原工具核验清单保留其已完成状态；结构重构也不等于剩余工具内容审阅完成。

本次未发现需要更换文件 IPC、异步事件跟踪原理或整个本地化来源捕获方案的依据。保留这些机制，仅在迁移中隔离入口与依赖；没有运行证据前不缩短等待、合并动态上下文或扩大缓存生命周期。
