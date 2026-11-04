# inspect_potions 场景与参数核验

> 当前状态：现状核验完成，处于设计讨论，尚未核销。已核对调用链、游戏悬停实现、错误恢复及验证入口，整理 17 份完整公开 JSON。已确认优先处理 5 项问题、移除槽位离屏过滤、增加槽位筛选，summary 沿用基础观察的槽位格式；关联提示裁剪、结果位置映射及局部未知表示待定稿。未修改工具行为，暂无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 已确认的问题与影响 | 建议范围与状态 |
| --- | --- | --- | --- |
| POTION-01 | 中 | 原生读取拒绝使用 `Potion details are unavailable in the current screen.`，未设置 `publicMessage`，MCP 只显示 `The requested action is unavailable.`；无法区分没有暴露顶栏和某个槽位不可读 | 复用安全公开错误机制，按实际失败原因提供说明。不得公开异常堆栈。待修复 |
| POTION-02 | 中 | `DisplayedHolders` 和 `VisibleHolders` 仍以 `OnScreen` 检查槽位及图标；一个槽位离屏就使整个读取失败，基础观察也会将整个药水栏记为 `null` | 将展示图标的视口截断与隐藏、透明、实际裁剪区分。药水动作及事件记录也调用此枚举，不能直接放宽动作入口或历史记录边界。待修复 |
| POTION-03 | 中 | 详情把任意一个禁用槽位视为整栏不可读；同时只检查 `IsEnabled`，没有检查鼠标或控制器焦点入口，因而启用但两种入口均关闭时仍可读悬停正文 | 仿照遗物区分静态展示与悬停：保留可识别药水及槽位，不能悬停时缺少正文、附来源 note；使用共用 `HoverAccess`。无自然发生频率结论，输入关闭属于源码确认的边界。待设计与修复 |
| POTION-04 | 高；信息边界 | 基础观察经 `DisplayedHolders` 仅检查容器与 holder，随后直接从模型读取名字；详情则额外检查 `%Image`／`%EmptyIcon`。因此占用药水图标隐藏时，详情拒绝，基础观察仍可生成该药水名字 | 补齐共享静态展示判断；隐藏内容不能按正常已展示药水读取，未知槽位也不能伪装成已确认空槽。源码确认，尚未新增游戏内故障注入复现。待修复 |
| POTION-05 | 中；验证设施 | `verify_potions.py` 与 `verify_mcp_potions.py` 均断言结果只含 `slot_tip/potion_slots/hover_tips`，后者还固定早期 12 工具清单。当前成功结果包含 `scene/screen`，会被误判失败 | 更新专项验证及工具发现检查，保留只读、英语、位置、提示去重与前后令牌一致性验证。开发指南已标明旧入口限制；脚本待修复 |

POTION-01 对应用户 TODO 的错误准确性范围。观察前置要求已由共用层处理，未发现需要为本工具恢复旧许可再写一套规则。以上问题不表示已有自然游玩复现；POTION-02–04 的条件与结果由源码确认，实施时需补游戏内边界验证。

## 核对基线与证据

- 核对日期：2026-11-04；代码 `e01c91e`，Mod `0.55.0`、MCP `0.57.0`、schema `36`。当前兼容表见 [README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`，release build `59260271`；RitsuLib `0.6.10` 兼容运行时。重新核对游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 原生入口：[RequestDispatcher](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[PotionInspection](../../src/Sts2Agent/Observation/PotionInspection.cs)、[RunUi.TopBarReadable](../../src/Sts2Agent/Observation/RunUi.cs)、[CombatObservation.PotionSlots](../../src/Sts2Agent/Observation/CombatObservation.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- Python：[工具登记](../../src/sts2_mcp/tool_registry.py)、[参数归一化](../../src/sts2_mcp/request_arguments.py)、[药水读取](../../src/sts2_mcp/output/potion_details.py)、[共享解释装配](../../src/sts2_mcp/output/public_output.py)、[GameSession](../../src/sts2_mcp/game_session.py)、[错误公开](../../src/sts2_mcp/output/error_output.py)。
- 游戏源码证据来自上述目标程序集的本地反编译：`.tmp/2026-11-02-top-bar-visibility/source/NPotionHolder.cs` 的 `OnFocus`；`.tmp/2026-11-03-architecture-refactor/NClickableControl.cs` 的 `AllowFocusWhileDisabled/RefreshFocus/Enable/Disable`；`.tmp/2026-10-31-events-implementation/source/PotionModel.cs` 的 `HoverTips/ExtraHoverTips`。未以一代 API 推断二代行为。
- 真实游戏响应复用[架构验收](2026-11-04-refactor-stage-7.md)的隔离实例证据，没有重新运行游戏。采样 Mod DLL SHA-256：`4a0b79dd4b7e5cb901ddf6f37f1b4f2d3b0b24972c3bc540e624c96bab98bae6`；`00f8b12..e01c91e` 的生产源码无变化。各样本保留原调用参数、来源条目和校验值，见[清单](2026-11-04-inspect-potions-examples/manifest.json)。
- 新运行的模拟恢复探针与专项测试证据：`.tmp/2026-11-04-inspect-potions-review/`。模拟、实现整理与真实响应在样本清单中分别标识；不把它们当作新的 GUI 实测。

## 当前参数与职责

```json
{"preset":"full"}
```

仅支持 `preset: default/full`，省略为 default；没有 summary 或槽位筛选。未知字段、错误类型和非法 preset 在本地拒绝，消息会列出允许字段或取值，不发送原生请求。工具提示词为：

```text
Read visible potion descriptions and hover help. potion_slots preserves belt positions, with null for empty slots.
```

工具读取药水及槽位帮助，不打开页面，不点击或移动鼠标，不触发 `OnFocus` 的动画、随机音效或药水流程；不生成技能药水等效果的未来随机选项。正文来自当前实例的原生 `HoverTip`，额外解释来自 `ExtraHoverTips`，经独立英语读取与格式转换。动态数值沿用当前原生说明；不计算实际使用结果。

`inspect_targets(potion_slot)` 负责可用性、目标、不可用原因与能否丢弃；`use_potion/discard_potion` 执行动作。不在本工具重复这些字段，也不因为药水战斗外不可使用就隐藏它的说明。

## 当前返回结构

| 字段 | 含义 |
| --- | --- |
| `scene/screen` | 同次快照的统一房间、结算和覆盖上下文；地图或牌组不会代替房间成为 scene |
| `slot_tip` | 通用槽位 `title/description`，满栏也固定返回一份；这是信息边界允许的固定帮助 |
| `potion_slots[]` | 按从左到右的原始槽位排列；占用项为 `name/description`，确认空槽为 `null` |
| `hover_tips[]` | 额外解释，按标题和正文同时相同去重，不重复每瓶药水的主体说明 |
| `hover_tips[].slot_indices` | 从 0 开始的原始槽位下标，保留空槽位置；可直接用于关联 `potion_slot` |

不返回内部模型 ID、稀有度、费用、目标、未来随机内容、available_actions 或 transition；不附带卡牌与敌人意图 notes。没有额外解释时 `hover_tips: []`。同标题但不同正文／数值仍分为两条。

full 保留已生成的普通 `null`，default 使用统一空值过滤；数组空槽在两者中始终保留。通常药水名称与正文非空，因此 full/default 的内容相同，不会在 default 删除空槽或压缩槽位。没有可读药水栏的错误与“读到全部为空”是两种情况。

## 场景目录与完整 JSON

前三份为依据当前实现及已采样说明整理的示例，未冒充游戏实测；随后十份为原游戏证据的完整公开响应。原调用省略 preset 时，样本的槽位空值也不会被 default 删除，结果与 full 相同；未将原调用记录改写成 full。

| 场景／结构分支 | 完整返回与证据类型 |
| --- | --- |
| 战斗，技能药水、空槽、格挡药水 | [混合槽位](2026-11-04-inspect-potions-examples/constructed-combat-mixed.full.json)；实现整理 |
| 战斗，满栏且两瓶格挡药水共享解释 | [重复提示](2026-11-04-inspect-potions-examples/constructed-combat-duplicate.full.json)；实现整理 |
| 战斗，整栏为空 | [全空](2026-11-04-inspect-potions-examples/constructed-combat-empty.full.json)；实现整理 |
| 战斗背景的地图与牌组浏览覆盖 | [地图](2026-11-04-inspect-potions-examples/map.full.json)、[牌组](2026-11-04-inspect-potions-examples/deck.full.json)；真实响应 |
| 事件选牌覆盖，顶栏仍暴露 | [事件选牌](2026-11-04-inspect-potions-examples/event-selection.full.json)；真实响应 |
| 商店、火堆、宝箱、奖励、先古之民 | [商店](2026-11-04-inspect-potions-examples/shop.full.json)、[火堆](2026-11-04-inspect-potions-examples/rest-site.full.json)、[宝箱](2026-11-04-inspect-potions-examples/treasure.full.json)、[奖励](2026-11-04-inspect-potions-examples/rewards.full.json)、[先古之民](2026-11-04-inspect-potions-examples/ancient.full.json)；真实响应 |
| 占卜棋盘、建筑师对话背景 | [占卜](2026-11-04-inspect-potions-examples/divination.full.json)、[建筑师](2026-11-04-inspect-potions-examples/epilogue.full.json)；真实响应 |
| 主菜单、转场、不可读顶栏；隐藏／离屏／禁用槽位等拒绝 | 当前共用[拒绝结构](2026-11-04-inspect-potions-examples/simulated-error-native_rejection.json)；模拟传输确认公开格式，各原生门控由源码核对 |
| 错误参数：未知字段、不支持的 summary、非对象参数 | [未知字段](2026-11-04-inspect-potions-examples/simulated-error-unknown_field.json)、[preset](2026-11-04-inspect-potions-examples/simulated-error-invalid_preset.json)、[类型](2026-11-04-inspect-potions-examples/simulated-error-invalid_object.json)；本地实际调用 |

其余页面条件：

- 三类战斗牌堆浏览与牌组共用 `CardView` 顶栏入口，成功时只是 `screen.view` 不同。未新增三类牌堆的药水实测样本。
- 选牌切回战场时允许独立读取顶栏；是否允许用药仍由动作门控判断。未新增该条件的药水样本。
- 胜负结果只在原生 outcome 页且顶栏暴露时可读；后续 summary、解锁等页面不因此允许读取。该分支由 `ResultTopBarVisible/RunResultInspection.Exposed` 核对，未新增结束页面的药水样本。
- 读取不要求玩家回合，也没有手牌 `InCardPlay` 的独立拒绝条件；仍须满足顶栏和各槽位门控。不能把 inspect_hand 或 inspect_combatants 的条件直接复制为药水规则。

药水种类、当前动态值、是否自动触发及槽位容量属于内容变化，不形成额外协议结构。三个槽只是样例，当前实现按 holder 实际数量枚举。

## 错误恢复核验

重新运行 `test_mcp_server.GameToolsTests` 中 9 项药水专项检查，全部通过；另运行未知字段、非法 preset、参数类型及原生拒绝的模拟探针。

| 结果 | 许可与恢复行为 |
| --- | --- |
| 成功详情 | 自身提供新许可，不要求先 get_observation；下一动作仍由游戏复核 |
| 本地参数拒绝 | 不发送请求，已有许可保持；`correct_request`，具体列出参数问题 |
| 明确原生 `illegal_action/invalid_request/expired_request`，且无已提交／已交互证据 | 有旧许可时保留，不制造新许可；拒绝后可直接选择合法动作 |
| 没有旧许可时读取被拒 | 不会由失败产生许可；仍需成功观察才可执行动作 |
| 过期状态、超时、取消、坏响应、异常或控制器冲突 | 不按明确未执行恢复许可；未知结果不自动重试 |

模拟 `get_observation → inspect_potions(明确拒绝) → end_turn` 成功，无中间补观察；公开恢复是 `choose_legal_action`。POTION-01 的通用消息也在同一探针中复现。无需重做 GameSession 的共用恢复逻辑。

专项脚本的旧结构断言已与当前完整响应对照确认，见 POTION-05；未把这些脚本算作通过的游戏检查。既有组合 GUI 仅证明表中列明的成功场景，不覆盖 POTION-02–04 的新增边界。

## 已确认范围与待定稿细节

已确认优先修复上述 5 项问题，移除药水槽位与图标的离屏过滤，并增加与遗物相同语义的槽位筛选。summary 的方向是复用 `get_observation.summary.top_bar.potion_slots` 的静态格式；该格式通常只有 name／空槽，特定条件还含 `usable_here`、`bouncing`，不能只复制名称而丢失已有的可见状态。没有授权读取真正隐藏内容。

建议在 `PotionInspection` 内将静态槽位识别、悬停读取和动作定位分开，共用语言与提示装配保持现有入口。`PotionActions.Find`、`PotionJournal` 和 `RunInventoryJournal` 也依赖现有枚举，迁移时分别保留点击合法性及事件可见性边界。

筛选与摘要的具体契约建议如下，尚未完成定稿：

- `slot_indices`：对应 `potion_slot` 的 0 起始槽位；省略／null 全部，[] 不取条目，去重后按原生顺序返回。允许查看已确认空槽，越界下标合并报错；不得把越界当空槽。
- 筛选结果压缩 `potion_slots` 时，顶层另给 `slot_indices` 数组，逐项映射到原槽位；例如 `slot_indices:[2]` 与 `potion_slots:[{"name":"Block Potion"}]` 表示返回的唯一药水来自原槽位 2，而不是槽位 0。未筛选时位置由原数组直接表示，不额外增加映射。
- 共享提示和不可悬停 note **同时参与筛选**：去掉未选择的来源，某条提示无剩余来源时删除整条提示；某类 note 无来源时删除该 note。保留下来的来源始终使用未筛选的原槽位编号，不按压缩结果重编号，沿用遗物的 `linked_help` 与来源裁剪规则。
- 例如原槽位为 `[Block Potion, null]`，只选 `[1]`：`potion_slots:[null]`、映射 `slot_indices:[1]`，full/default 的 `hover_tips:[]`，不会返回 Block 提示或槽位 0 的不可悬停 note。full/default 的 `slot_tip` 是独立通用槽位帮助，保留一份；它不是格挡解释。summary 则不含 slot_tip 或 hover_tips。
- 两瓶格挡药水原本位于 0、2 且共享 Block 提示时，只选 `[2]`，该提示保留但关联裁剪为 `slot_indices:[2]`；只选一个空槽则不保留该提示。
- `summary`：保留 scene/screen 及共用静态药水槽位数据，不返回 `slot_tip`、主体 description、hover_tips；筛选时保留位置映射与参数错误。内部走静态读取，不能先生成全部悬停说明再删除。
- full/default 无法悬停但图标已展示时，可沿用遗物的 `description:null` 与 `notes.hover_tips_unavailable`；default 省略普通空正文，summary 不提示缺少它本来就不请求的说明。
- 未筛选时保留现有固定槽位数组；全空与未知仍须区分。真正隐藏图标的表示方式需先定稿，不能直接照搬“遗物列表删项”而导致槽位重编号。

以上区分已确认范围与具体建议，尚未构成完整公开契约。剩余讨论包括提示裁剪与位置映射的具体返回，以及局部未知槽位采用整次拒绝还是显式未知表示，再形成修复与参数定稿。
