# inspect_relics 场景与参数核验

> 当前状态：场景与现状核验完成，进入设计讨论；工具尚未核销。已确认 2 项正确性／验证问题，另有遗物可见状态的字段缺口待确定设计。现有 summary 和筛选可继续沿用；尚未修改工具行为。暂无调查阻塞。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 证据、建议及状态 |
| --- | --- | --- | --- |
| RELIC-01 | 中；错误准确性 | 顶栏或遗物栏不可读时，原生仅返回内部 `message`，未设置 `public_message`；MCP 因而只给出 `The requested action is unavailable.`，不能说明是页面未暴露顶栏，还是遗物栏隐藏／未就绪 | `RequestDispatcher` 的 inspect_relics 分支、`RelicInspection.DisplayedHolders` 与模拟拒绝均确认。建议按实际门控公开安全、具体的拒绝原因，继续隐藏异常信息；待实现 |
| RELIC-02 | 中；验证设施 | `verify_relics.py`、`verify_mcp_relics.py` 仍要求顶层只有 relics／hover_tips，条目只有 name／counter／description；当前已有 scene／screen、melted 和条件 note。stdio 脚本还固定旧的 12 工具清单，因此正确响应也会验证失败 | 已将完整真实响应与断言逐项对照。建议同步到当前契约，保留只读、英语、原下标、解释去重、两种传输一致性和状态不变检查；待实现。已有共用验证并未因此失效 |

另有一项**UI 反馈缺口，是否扩展字段尚待确认**：

| 编号 | 优先级 | 缺口及影响 | 证据与候选范围 |
| --- | --- | --- | --- |
| RELIC-03 | 中；静态字段候选 | 静态数据只有 name／counter／melted，不表达图标置灰或激活发光。full 的用尽正文有时可补充说明，但 summary 不读正文；激活发光也不一定有计数可以代替 | 目标程序集的 `NRelicInventoryHolder.RefreshStatus`、`RelicModel.UpdateTexture`。`VenerableTeaSet` 以 Active 表达已准备额外能量，没有可见计数；`LizardTail` 用后变 Disabled。建议依据实际图标着色／shader 补可见状态，并同步基础观察和详情的共享静态入口；不读取内部触发资格或隐藏旗标。尚未新增自然游戏样本 |

未发现新的观察前置要求问题：本地坏参数不清除旧许可；明确读取拒绝保留已有许可；成功的空筛选和部分成功也能授权后续合法动作。没有旧许可时，失败读取不会凭空授权。过期快照和未知结果仍须遵循共用恢复规则，不能当作明确未执行。

## 核对基线与证据

- 核对日期：2026-11-04；代码 `e62a1bc`，Mod `0.56.0`、MCP `0.58.0`、schema `37`。现行兼容表见 [README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`，release build `59260271`，RitsuLib `0.6.10` 兼容运行时。重新校验游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 原生实现：[RelicInspection](../../src/Sts2Agent/Observation/RelicInspection.cs)、[RunUi](../../src/Sts2Agent/Observation/RunUi.cs)、[请求入口](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[英语遗物格式](../../src/Sts2Agent/Localization/EnglishRelicText.cs)。
- Python：[参数与投影](../../src/sts2_mcp/output/relic_presets.py)、[响应校验](../../src/sts2_mcp/output/relic_details.py)、[共用装配](../../src/sts2_mcp/output/public_output.py)、[请求归一化](../../src/sts2_mcp/request_arguments.py)、[GameSession](../../src/sts2_mcp/game_session.py)、[错误公开](../../src/sts2_mcp/output/error_output.py)。
- 重新从上述目标程序集反编译的证据：`.tmp/2026-11-04-inspect-relics-review/source/` 中的 `NRelicInventoryHolder`、`RelicModel`、`PenNib`、`VenerableTeaSet`、`LizardTail`。对照成员包括 RefreshAmount／RefreshStatus／OnFocus、HoverTip／HoverTips／UpdateTexture、UpdateDisplay、GainEnergyInNextCombat 和 WasUsed。反编译文件不纳入 Git。
- 完整真实返回复用[药水变更后的共用 GUI 回归](2026-11-04-potion-inspection-implementation.md)和[架构验收](2026-11-04-refactor-stage-7.md)，没有为这份审阅重新启动游戏。两批证据分别为 schema 37 和 36，采样 Mod DLL 的校验值及每份样本来源见[清单](2026-11-04-inspect-relics-examples/manifest.json)。遗物读取、英语格式、悬停判断、响应校验及遗物投影在这两个代码基线间没有变化。
- 新执行的 19 项 Python 专项测试及 11 组模拟／本地探针见 `.tmp/2026-11-04-inspect-relics-review/python.log`、`probes.json`。模拟传输不代表新的 GUI 实测。

## 现有参数与职责

```json
{"preset":"full","relic_indices":[2]}
```

| 参数 | 现有语义 |
| --- | --- |
| preset | default／full／summary，省略为 default；default 为完整详情加普通空值过滤 |
| relic_indices | 当前**未筛选且已显示的遗物列表**从 0 开始的位置；省略／null 全部，[] 为空；去重、按原生顺序输出 |

遗物下标不是模型 ID，也不是筛选后的相对位置。它与同次稳定画面的 `get_observation.full/default.top_bar.relics` 顺序一致；summary 顶栏只给 relic_count，没有遗物列表。遗物增减、重排或显示集合变化后不能复用旧位置。

显式非 null 数组会生成顶层 relic_indices，与结果 relics 一一对应；共享解释及不可悬停 note 同步筛选，保留**原位置**。例如只取原位置 2 的 Lantern，结果中它位于数组 0，但映射和 Energy 提示仍指向 2。省略或 null 筛选均不增加位置映射。重复或越界下标不改变这一规则。

筛选仅影响 Python 输出；summary 另向原生发送私有 `level:"summary"`，跳过悬停正文。原生文件协议允许 level: full／summary，省略为 full；现有 CLI 不提供遗物 preset 或筛选选项。CLI 普通读取保留完整空值。公开 MCP 参数不能原样转发给文件协议。

当前工具提示词：

```text
Read displayed owned relics. Unavailable hover help is noted; summary keeps basic fields. relic_indices filters by positions in the current unfiltered inspection.
```

职责与内容相符，长度可接受。若沿用现有参数，不需要为改提示词而改提示词；可将 basic fields 明确为 name／counter／melted，若接受 RELIC-03 再统一命名。遗物栏静态数据和悬停能力已有独立入口，没有发现需要再次进行大范围结构重构的依据。

## 现有字段与信息边界

| 字段 | full | default | summary |
| --- | --- | --- | --- |
| scene／screen | 同次快照的房间及覆盖状态 | 同 full | 同 full |
| relics[].name | 图标对应的英语名字 | 普通 null 省略 | 同 default |
| counter | 已显示的整数；未显示／不可解析为 null；0 保留 | 普通 null 省略 | 同 default |
| melted | 蜡质遗物 false／true；非蜡质 null | 普通 null 省略 | 同 default |
| description | 原生英语正文，含动态值、用尽／熔化包装；不可悬停为 null | 普通 null 省略 | 不生成 |
| hover_tips | 附带解释；按 title 和 description 同时去重 | 同 full | 不返回 |
| notes.hover_tips_unavailable | 对应当前不能悬停的已显示条目，引用 relics.N | 同 full | 不生成 |
| relic_indices／errors | 仅在相应筛选或越界时出现 | 同 full | 同 full |

描述中的卡牌或其他遗物引用仍来自原生悬停帮助，作为 title／description 输出，不另造手牌结构。未提供风味文本、稀有度、获取楼层、内部计数、概率推演或未来触发结果。

读取来自实际遗物栏 holder，静态字段与基础观察共用 `RelicInspection.Static`。隐藏、透明、实际裁剪、无纹理、零缩放或待删除条目排除；**条目、计数和熔化表现均不按视口截断**。整个顶栏不可读或遗物栏隐藏时拒绝；可读集合为空则返回 relics: []，两者不同。relic_count 是独立的持有总数，不能用它推断未显示条目的身份。

可悬停判断采用共用 HoverAccess；模型 RelicStatus.Disabled 的置灰不等于控件被 Disable。看得见但当前无法悬停时保留静态条目，仅缺说明并附 note。读取不调用 OnFocus、不缩放图标、不切换语言、不打开遗物检查页；临时英语格式和 EnergyVar 前缀在 finally 恢复。未知提示类型报错，不静默删除。

## 场景目录与完整 full 示例

以下链接均为**完整公开 JSON**。真实 stdio 返回、原生记录重新投影、既有返回重新筛选和实现整理分别标识；没有将 default 请求改写成实际发生过的 full 调用。

| 场景／结构分支 | 完整示例及证据类型 |
| --- | --- |
| 战斗主画面：普通遗物、0 计数、Block／Energy 解释 | [combat.full.json](2026-11-04-inspect-relics-examples/combat.full.json)，真实 MCP |
| 战斗背景的地图、牌组覆盖 | [地图](2026-11-04-inspect-relics-examples/map.full.json)、[牌组](2026-11-04-inspect-relics-examples/deck.full.json)，真实原生响应经当前 full 投影；原公开调用为 default |
| 事件的卡牌选择覆盖 | [事件选牌](2026-11-04-inspect-relics-examples/event-selection.full.json)，真实 MCP |
| 先古之民、火堆、宝箱、奖励、商店 | [先古之民](2026-11-04-inspect-relics-examples/ancient.full.json)、[火堆](2026-11-04-inspect-relics-examples/rest-site.full.json)、[宝箱](2026-11-04-inspect-relics-examples/treasure.full.json)、[奖励](2026-11-04-inspect-relics-examples/rewards.full.json)、[商店](2026-11-04-inspect-relics-examples/shop.full.json)，真实 MCP |
| 占卜覆盖、建筑师对话背景 | [占卜](2026-11-04-inspect-relics-examples/divination.full.json)、[建筑师](2026-11-04-inspect-relics-examples/epilogue.full.json)，真实 MCP |
| 蜡质遗物尚未熔化、已经熔化 | [熔化前](2026-11-04-inspect-relics-examples/wax-before.full.json)、[熔化后](2026-11-04-inspect-relics-examples/wax-after.full.json)，真实 MCP；正文包装与 melted 同时变化 |
| 可读栏没有已显示条目 | [空集合](2026-11-04-inspect-relics-examples/constructed-empty.full.json)，实现整理；不冒充自然游戏实例 |
| 已显示但不能悬停 | [全部](2026-11-04-inspect-relics-examples/hover-unavailable.full.json)、[带筛选及 note](2026-11-04-inspect-relics-examples/hover-unavailable-filtered.full.json)，真实 MCP；输入入口关闭由测试夹具注入 |
| 筛选单项、[]、有效与越界混合 | [单项](2026-11-04-inspect-relics-examples/filtered.full.json)、[空筛选](2026-11-04-inspect-relics-examples/filter-empty.full.json)，真实 MCP；[混合筛选](2026-11-04-inspect-relics-examples/filtered-partial.full.json)为真实完整返回的当前投影回放 |
| 顶栏不可读、主菜单、转场、整个遗物栏隐藏／未就绪 | [共用拒绝](2026-11-04-inspect-relics-examples/simulated-error-native_illegal_action.json)，模拟传输确认当前公开格式；各原生门控由源码核对，尚未新增各拒绝场景 GUI 样本 |
| 未知字段、非法 preset、非法下标 | [字段](2026-11-04-inspect-relics-examples/simulated-error-unknown_field.json)、[preset](2026-11-04-inspect-relics-examples/simulated-error-invalid_preset.json)、[下标](2026-11-04-inspect-relics-examples/simulated-error-invalid_index.json)，实际本地校验，未向游戏发送 |

其余条件共用上述结构，尚未新增独立游戏样本：

- 抽牌堆、弃牌堆、消耗堆与牌组共用 CardView 顶栏门控，仅 screen.view 不同。
- 原生 outcome 结算页须仍暴露顶栏；后续结算详情／解锁页不因此开放读取。依据 RunUi.ResultTopBarVisible／RunResultInspection.Exposed。
- 普通事件正文、其余选牌类型和战场视图沿用 TopBarReadable 条件；不能由事件选牌样本推出所有界面都允许。
- 没有独立的玩家回合、牌费或目标限制；动画期间仍受顶栏及当前控件状态限制。不同遗物内容和动态计数是条目变体，不另造协议。
- 全部遗物、第三方悬停、多人与任意图层遮挡未穷举；没有利用内部状态补齐这些验证缺口。

## 错误恢复与验证结果

- 新运行 `tests.python.test_relic_presets`、`tests.python.test_relic_display`，共 **19 项通过**：包含真实 stdio 配合模拟游戏传输、参数校验、摘要、原下标、共享解释、note 裁剪及全量响应校验。
- 新运行 **11 组探针**：本地非法参数保留旧许可且不发读取；illegal_action／invalid_request／expired_request 明确拒绝后可直接 end_turn；没有旧许可时拒绝不授权；空筛选／部分成功／null 筛选成功后可直接行动。探针用模拟客户端，没有执行真实游戏动作。
- 本地坏参数返回 correct_request；明确拒绝且保留旧许可时，illegal_action／expired_request 返回 choose_legal_action。原生未 opt-in 的内部消息被替换成通用消息，RELIC-01 因此成立。
- RELIC-02 通过当前完整真实返回与旧字段断言对照确认；未将这两份过时脚本当作通过的 GUI 验证。较新的 verify_display_readers／verify_relic_presets 仍覆盖已列明的有效路径。
- 没有改生产代码、运行构建或新增游戏内行为验证。已导出样本的来源、内容及文件校验值分别核对。

## 设计候选与下一步

既有参数和摘要已经符合约定，建议继续保留：summary 使用共用静态字段，省略所有悬停正文、解释和对应缺失 note；筛选不重编号来源；不增加 available_actions 或 transition。

可选范围：

1. **修复 RELIC-01／02，补可见状态（建议）**：原生错误补具体原因，修正过时验证；在 RelicInspection.Static 内根据真实图标表现读取置灰／激活状态，基础观察和各详情预设一起复用。需要先确定字段名、普通状态是否保留、熔化与状态是否可同时表达。
2. **仅修复 RELIC-01／02**：维持所有条目字段；实现较小，但 RELIC-03 的静态 UI 信息缺口保留在本审阅，不能算作已修复。

若增加状态，优先考虑描述外观的 `grayed_out`／`pulsing` 条件字段，或一个明确描述图标表现的枚举。前者允许熔化着色、置灰和发光独立表达；后者更紧凑，但须核对能否互斥。不能直接将模型 Status、IsUsedUp、触发准备旗标当作当前已显示状态，也不调用 UpdateTexture 刷新画面。字段定稿后再修改工具，暂无实施授权。

文档核对另发现两处旧说明：遗物指南称底层文件调用无参数，实际已支持 level；MCP 概述仍把整个遗物集合限定为可悬停，实际已保留不能悬停的静态条目。说明已同步当前实现；专项验证入口标明 RELIC-02 的实际限制，未通过改文档宣告代码问题解决。
