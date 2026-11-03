# 工具共用契约与执行链路重构计划

> 当前状态：第 1–4 阶段完成，整体完成 4／7；第 5 阶段实施中，已验证测试分派迁移，正在处理原生快照、生产路由与响应。暂无阻塞。阶段记录见[第 1–2 阶段](../../research/2026-11-04-refactor-stages-1-2.md)、[第 3–4 阶段](../../research/2026-11-04-refactor-stages-3-4.md)与[第 5 阶段](../../research/2026-11-04-refactor-stage-5.md)。
>
> 执行方式：按阶段实施与验证，每阶段独立提交；使用 `superpowers:executing-plans`。后续发现无法确认的语义差异时先询问，不把整理结构当作改变行为的授权。

**目标：** 让一种规则只有一个负责的入口，保留已经核验的 UI 信息边界，使后续逐工具设计不再反复修补共用链路。

**结构：** Python 从纯契约、领域校验、工具登记到会话与公开投影单向依赖；原生从采样、玩法／页面分派到事件与响应组装分工。共用领域片段，不把所有工具压成相同字段集合。

**技术：** 现有 C#／Godot／Harmony、Python／AnyIO／MCP、文件 IPC；本计划不要求新增依赖或拆分程序集。

**设计依据：** [源码审查、问题清单与四项已确认接口调整](../../research/2026-11-03-architecture-refactor-audit.md)。该文档与本计划一同作为执行依据；不要求重读全部旧研究。

## 全局约束

- 实施前读 AGENTS、文档规范、Codex 环境约定、可见信息边界及本阶段涉及的持续维护接口；当前版本以 README 为唯一来源。
- 除四项已确认调整及经验证的共用错误修复外，公开字段、工具集合、工具专用预设、原生交互与停止语义保持原行为。
- 不增加所有工具统一 summary，不恢复 detail_level，不增加遗物稳定 ID，不把浏览 ID 转成出牌 ID。
- 不读取未知身份、隐藏标签或未来效果，不用模型值补 UI 空缺；完整校验先于筛选和摘要，默认 null 例外保持。
- 原生操作遵守主线程、原生动作、异步流程及跨 await 的身份复核。超时、取消、执行结果未知不自动重试。
- 调整筛选引用与新增上下文时更新公开版本及相关指南；原生协议调整时单独判断 schema 是否需升级，不能静默承诺兼容未验证版本。
- 每阶段先锁定行为断言，再替换实现，最后运行对应检查并提交。移动代码与行为变更尽量分开提交。
- 不改用户 TODO 的范围和完成数，不把架构重构计为未审阅工具完成；阶段执行结束同步本页总进度。

## 需要重点防回归的条件

1. 请求在队列中等待时，不得借用之后某次读取的新许可；取消后也不得恢复旧许可。
2. inspect_selection 的 view_upgrades、牌组排序及地图／牌堆切页有 UI 副作用，不能被读工具统一策略误判为无变化。
3. 空筛选、隐藏条目、真实空槽、部分无效 ID 与 before/after:null 均不能被通用精简规则混淆。
4. 变灰遗物仍可悬停；实际禁止悬停的显示条目保留静态数据和准确关联的 note；未知提示类型仍报错。
5. 跨房间／战斗／结算、占卜媒体失败及旧原生响应缺少执行证据时，不得错误续接动作许可或声称操作未执行。

## 阶段与依赖

| 阶段 | 可独立验收的交付 | 风险 | 依赖 |
| --- | --- | --- | --- |
| 1 | 行为基线与公开差异清单 | 低 | 无 |
| 2 | Python 契约与校验消除循环依赖，MCP／CLI 共用解码入口 | 中 | 1 |
| 3 | 工具登记、参数／preset／筛选共用入口 | 中 | 2 |
| 4 | 集中会话许可与错误恢复 | 高 | 3 |
| 5 | 原生快照、路由、测试及响应职责分离；补上下文、解耦媒体 | 高 | 2–4 |
| 6 | 展示／悬停分离及共享领域片段迁移 | 中至高 | 3、5 |
| 7 | 整体验证、兼容入口清理与文档交付 | 中 | 1–6 |

前 4 阶段原则上无需为验证架构改动启动游戏；原生响应字段的新增不提前用假数据宣称完成。第 5–6 阶段各自运行针对性 GUI，第 7 阶段再执行一次组合回归。

## 第 1 阶段：建立行为基线

**修改范围：** `tests/python/` 中输出、预设、许可与 CLI 检查，`tests/game/support/`；新增 `tests/data/tool_contracts/` 保存必要的脱敏输入与期望结果，新增 `tests/python/test_tool_contracts.py`。现有历史例子不改写成“新实测”。

**接口：** 基线样本记录 operation、arguments、原生输入及公开期望；显式列出本次四项允许差异，不忽略任意字段或数组顺序。控制令牌使用测试值，未知原生字段继续验证不泄露。

- [x] 提取覆盖每个玩法操作的代表性成功／拒绝样本；样本不足的原生分支明确列为第 5–6 阶段补采，不伪造游戏证据。独立断言卡牌、槽位、比较、事件、来源和媒体结构。
- [x] 对同一操作锁定 default／full 和已有专用预设的字段、null、空集合及顺序；锁定 MCP 和 CLI 已有默认值差异。
- [x] 将通用假响应与样本构造从大型 `test_mcp_server.py` 逐步移到 `tests/python/support/`，保持现有测试行为，新增所需的跨工具表驱动测试。
- [x] 运行完整 Python 测试与现有 C# 纯检查，记录当前实测基数和未覆盖分支；提交基线。后续阶段按基线对比，不只依赖测试数量增长。

建议提交：`test: capture tool contracts before architecture refactor`。

## 第 2 阶段：分离 Python 契约、校验和输出

**当前入口：** `output/game_output.py`、`inspection_details.py`、`player_output.py`、`card_format.py`、`presets.py`、各 `*_details.py`、`roundtrip_client.py`。

**建议新增：** `output/contracts/` 按 cards／combat／selection／rooms／transition 分置纯形状与枚举；`output/response_pipeline.py` 统一成功响应解码和按操作装配；`output/null_fields.py` 放独立空值过滤，`output/media.py` 放媒体承载类型及纯格式校验。只有确有共用内容才建模块，避免每个结构都单独建文件。

**接口：** `decode_success(operation, state, native_arguments=None) -> dict` 完整校验后返回该操作的公开完整内容；不改会话许可，不应用用户筛选／preset，不附媒体。`player_result` 与 `roundtrip_client.player_result` 的现有直接调用兼容入口保留，但生产 MCP／CLI 均显式传 operation 并走相同解码路径。

- [x] 加入依赖方向断言：纯 contracts 不导入 reader／preset／会话；领域 reader 不导入总输出装配；生产输出模块不存在循环依赖，包括函数内导入。
- [x] 先移动纯结构与常量，再将 selection／hand 校验移出总观察模块；让观察校验组合领域校验，详情不再向观察总装配取结构。
- [x] 将纯 null 过滤从 preset 装饰器分离，将 ImagePayload 从占卜领域校验分离；card_format 不再通过 presets 回到 player_result，通用预设也不再为媒体类型反向导入占卜 reader。
- [x] 为各操作明确完整／face／静态片段范围，逐个替换“看见 description 就猜 full”的生产装配路径。比较卡的侧别、商店外层购买 ID、悬浮剑身份保留独立职责。
- [x] 将共享说明去重与 notes 组装放在公开装配层；保持先按工具校验，再只输出该工具声明字段，不再通过全工具 GAMEPLAY 并集兜底投影。旧兼容调用只做显式兼容处理。
- [x] MCP／非 raw CLI 调用同一解码入口；raw 仍保留原始包装。对每个操作注入坏嵌套值、缺失必需字段及额外诊断字段，验证坏数据拒绝和未知字段移除。
- [x] 运行基线回放、输出边界与完整 Python 测试，复算依赖图；本阶段除更准确拒绝原本漏校验的坏响应外不改变合法公开结果。提交并同步 architecture／observation 的入口说明。

建议拆为“移动纯契约”“统一解码装配”两个提交。

## 第 3 阶段：工具登记、请求参数和筛选

**修改范围：** `mcp_catalog.py`、`game_tools.py`、`output/presets.py`、`output/available_tools.py`、各参数及 preset 模块、CLI。建议新增 `tool_registry.py` 与 `request_arguments.py`，工具特有算法留在各领域模块。

**接口：** `ToolSpec` 登记公开名称、原生操作、工具提示、参数 schema／解析器、支持的 preset、响应 reader 和投影。副作用类别、是否需要动作许可、是否记录／返回 transition、MCP annotations 独立登记。`normalize_request(spec, arguments) -> NormalizedRequest` 将公开 preset、原生参数、输出筛选、媒体需求与这些执行规则分开；`filter_indices(items, requested)` 返回保留的原位置及缺失位置。

- [x] 测试登记表与公开工具目录、handler、reader、公共分类一一对应；截图单独登记而不获得玩法 preset，get_observation 明确映射 get_state。先迁移登记，不引入跨语言代码生成。
- [x] 从登记表导出 catalog／handler 分派与 preset 列表，移除包装器签名推断和按工具名堆叠的错误特判。通用参数类型、范围及允许值共用定义；目标选择等跨字段约束保留明确解析器。
- [x] 独立测试这些执行维度：inspect_selection 仅在提供 view_upgrades 时按可能改 UI 处理，但不因此要求旧动作许可；set_divination_tool 改 UI、需要许可并返回动作回执；截图写文件但不刷新游戏许可。原生 RecordedActions 对照登记的事件记录要求，不从 MCP readOnlyHint 推导。
- [x] 用表驱动测试统一可选筛选：省略／null 全部、[] 为空、重复去重、原生顺序、有效与无效项并存；只改变四项已经确认的接口契约。
- [x] 遗物顶层映射仍用 relic_indices，提示中的 relic_indices 改为原位置；combatants 保持 source_indices 与原路径。药水的真实槽位 null 不压缩，卡牌身份不换成位置；不强制更名所有关联字段。
- [x] 共用筛选选择与帮助关联裁剪，匹配策略保持显式：UI 精确来源、combatants 对象／分组；关联 note 同步裁剪。summary 完全省略悬停还是仅省 description 仍按工具规定。
- [x] 将 default 空值过滤保持为最终单一入口；过渡事件、比较两侧、真实数组 null 和宝箱可见 relic:null 的例外用路径规则测试，不能在工具中另写一套删 null。
- [x] 对所有工具的未知参数、错误 preset、布尔冒充整数、范围边界、null 逐项检查 schema 与实际解析一致；运行完整 Python 测试，按接口变化更新 MCP 版本与指南后提交。

## 第 4 阶段：会话许可和错误恢复

**修改范围：** `game_tools.py`、`controller_lease.py`、`output/error_output.py`、新 `game_session.py`；保留 transport Client 独立。检查 `test_inspection_errors.py`、`test_action_observations.py`、`test_mcp_server.py` 和截图测试，新增跨工具许可策略测试。

**接口：** `GameSession.execute(request)` 统一锁／控制器／发送／响应校验／许可更新；`PermissionState` 维护令牌及调用时的许可代次。执行证据独立于公开 JSON，允许“明确没有提交且未改 UI／可能已改 UI／结果未知”，不能只从错误码推测。缺失证据按保守规则处理。

- [x] 先为登记的纯读取、页面改变和游戏动作建立错误矩阵，断言每类的本地参数错、原生明确拒绝、stale、坏响应、超时、取消、控制器冲突与成功后的许可。
- [x] 将参数拒绝、读取拒绝与未提交动作的恢复规则集中处理；没有发送的本地参数错误保留此前已有许可，不生成新许可。纯读取的明确拒绝可保留；改 UI 的请求仅凭 illegal_action 不得恢复。
- [x] 普通动作只在原生能证明“尚未提交且 UI 未改变”时保留旧许可；新增动作的证明逐处理器审查，不把 play_card 的局部保证扩展成所有动作的默认假设。
- [x] 保留“调用开始时”的许可限制，覆盖并发动作、排队后读取、取消中途、控制器抢占及异常退出；不等待后取得未来许可，不自动刷新或重试。
- [x] 固定公开错误与私有诊断分界；统一参数错误指出字段／类型／范围，部分筛选错误仍是成功结果 errors，不误作整次失败。读异常与动作未知结果按实际类别提供 recovery。
- [x] 为媒体故障加入“动作已执行／阶段未知”用例，防止 screenshot_unavailable 被全局解释为玩法未执行；先覆盖测试，原生请求选项和响应证据在第 5 阶段接入。
- [x] 运行许可、错误、stdio、截图及完整 Python 测试；同步 MCP 错误语义。用户持有的实测记录尚未对照，TODO 两项不因此自动核销。

## 第 5 阶段：原生采样、分派与响应

**当前入口：** `GameAdapter.cs` 及场景 partial、`ObservationContext.cs`、`GameAdapter.Resources.cs`、`ActionEventScope.cs`、`FileMailbox.cs`、`Testing/GameAdapter.Testing.cs`。

**建议拆分：** `Observation/GameObservation.cs` 负责 Capture 与代际；`Adapter/RequestDispatcher.cs` 负责玩法路由；`Adapter/ResponseBuilder.cs` 负责上下文／transition／响应序列化；`Testing/TestRequestDispatcher.cs` 负责测试路由。沿用已有领域 reader／action，不为搬文件创建一个转发类对应一个旧方法。

**接口：** `ObservationSnapshot` 携带一次 Capture 的完整状态、scene/screen、令牌及原生身份上下文；`ResponseBuilder` 接收该快照、工具结果和明确 transition／媒体需求。没有 UI 改动的详情复用本次快照；页面操作完成后再捕获一次，不用详情内容重新发明 scene。

- [x] 先迁出测试请求，逐条件保留 testMode、suite／scenario 双重限制；测试操作不得进入 MCP catalog 或 available_actions。运行纯检查与测试分派回归后单独提交。
- [ ] 迁移同步 Capture 与代际维护，保留现有哈希输入及占卜 dialogue 特例，不在此次搬迁中重新定义令牌有效性；比较移动前后相同输入的状态与令牌行为。
- [ ] 路由显式保留 proceed／inspect_event 等按当前页面决定去向的优先级；AvailableTools 与处理器共用条件，但工具被列出不代表任意参数都可执行。单人条件移出宝箱模块放到共用运行上下文。
- [ ] hand、targets、potions、relics 全部经统一响应构造，补同次 scene/screen；地图下的详情、眼睛切回战场、建筑师背景和结算顶栏逐项对比 get_observation。
- [ ] 将重复字符串拼接 transition 改为结构化组装；共用 complete 与事件缓冲应用入口，保留场景特有 stop_reason 选择、事件预留顺序／截断与战斗间交接，不改原生事件捕获原理。
- [ ] 在内部请求包装中增加显式媒体需求，旧文件调用省略时保持原行为。MCP 动作回执及 actions_only/top_bar 不捕获占卜 PNG；需要棋盘的观察／inspect_event 仍要求同次有效图片。字段名、默认与兼容处理在本阶段协议测试中固定，不将参数公开给 LLM。
- [ ] 集中提交前拒绝与安全公开说明；每个标记“未提交且 UI 未变”的返回分支审查其前置副作用。媒体与序列化错误不得覆盖已知执行事实。
- [ ] 编译、C# 纯检查、原生检查与针对性 GUI：战斗连续动作、0 能量拒绝后 end_turn、事件／先古之民到选牌、地图／牌堆切换、占卜动作／图片故障、战斗交接与结算。记录同次构建哈希，更新对应指南及版本后提交。

本阶段可按“测试路由／快照／响应及媒体”分为多个独立提交；每个中间提交保持可构建，原生 API 改动前核对目标程序集。

## 第 6 阶段：展示、悬停与共享领域片段

**修改范围：** `VisibleUi`、`RunUi`、`CombatObservation`、`UiInspection`、`RelicInspection`、`PotionInspection`、`CardPresentation`／`CardAppearance`／`BrowsedCard` 及已有 CombatantInspection。共享字段从这些领域入口组合，不为所有东西建立同一个泛型 reader。

**接口：** 保留“展示集合”和“可读取悬停说明”两个独立结果；每条悬停缺失 note 关联未筛选来源。可见性明确区分屏幕内可点击控件、原生可浏览列表、无需位置截断的显示图标，不能全局把 OnScreen 替换为 Shown。

- [ ] 建立调用点清单，标明每个 OnScreen／Displayed／Browsable 的用途。图标移到视口外不应导致其静态字段单独消失；实际隐藏、透明、裁剪、零缩放、未揭示及节点删除继续按领域规则处理。
- [ ] 遗物 full/default/summary 与基础观察共用展示顺序，禁用悬停不再删除静态条目；统一计数、melted 的位置策略。full 中不可读 description 为 null，hover_tips 不生成说明，notes.hover_tips_unavailable 关联原 relic_indices；default 过滤普通 null，summary 不读取说明也不附悬停 note。
- [ ] 核对实际原生悬停条件，包括 AllowFocusWhileDisabled 与鼠标／控制器入口；note 只表示当前无可读说明，不把 RelicStatus.Disabled、普通无额外提示或未知提示异常误判为无法悬停。
- [ ] 对遗物 note 的 sources 使用工具内规范地址 `relics.N`，并将源条目下标与第 3 阶段的 relic_indices 关联裁剪；不新增接受任意路径的遗物筛选参数。
- [ ] 顶栏与药水静态槽位枚举、卡牌实节点／浏览克隆的格式化、UI 与战斗对象提示去重，只提取已经相同的片段；保留克隆上下文、动态预览、未揭示牌面与 before/after 侧别。
- [ ] 将通用反射取字段辅助从 CardSelection 的领域类中迁出；私有 API 绑定仍各领域负责并验证，关键绑定缺失显式拒绝，不能统一静默返回 null。
- [ ] 原生测试覆盖变灰仍可悬停、控件禁用但仍显示、实际隐藏／裁剪、计数 0、无计数、离屏图标、共享提示／note 筛选；GUI 验证基础观察、详情、summary 的共同静态数据和当前 UI。注入控件禁用的证据明确标为测试夹具，不冒充自然游玩案例。
- [ ] 同步遗物／可见性／手牌等涉及的持续维护文档，运行相关 Python／C#／GUI 检查后提交。

## 第 7 阶段：组合回归与收尾

**修改范围：** 剩余兼容入口、`tests/game/data/` 的组合套件及支持代码、README、architecture、各已变更工具指南与原核验清单。历史证据保持原始含义；不维护第二份当前版本表。

- [ ] 运行全量 Python、C# 纯检查、Mod 编译与依赖／登记一致性检查；确认不再依赖旧的大范围投影和分散 preset／许可名单。仅保留确有使用者的兼容入口。
- [ ] 组合 GUI 覆盖战斗、附魔／Affliction、充能球／奥斯提／君王之剑、选牌比较、地图／牌堆、遗物、药水、奖励／火堆／宝箱／商店／事件／先古之民、占卜、战斗交接和结算。复用现有 verifiers，受进程限制的结算场景另开隔离实例。
- [ ] 为四项对外调整提供当前真实完整 JSON：筛选遗物及来源、null／[] 参数、补齐上下文、不可悬停 note。附测试条件、构建哈希和未验证范围；不只展示人工摘录。
- [ ] 逐 RF-01–RF-14 记录处理与验证位置，不能以文件变小或测试数量增加替代行为验证；未解决项保留在本任务记录，未经要求不搬到用户 TODO。
- [ ] 原工具清单恢复逐工具内容审阅，仍只核销真正完成的范围；交付当前版本、提交和文档，安装 Mod 另按用户请求执行。

## 执行和验收命令

以下沿用现有项目入口；运行前使用 [architecture](../../development/architecture.md) 和 [GUI 指南](../../development/gui-testing.md) 核对环境与有限超时。套件文件随阶段选取，不提前创建空套件。

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'
```

```sh
dotnet build Sts2Agent.sln -m:1 -p:Sts2Dir="$Sts2Dir" -p:RitsuLibDir="$RitsuLibDir" --no-restore
```

```sh
dotnet run --project tests/csharp/Sts2Agent.Checks/Sts2Agent.Checks.csproj --no-restore --no-build
```

游戏运行统一用 `scripts/gui_suite.py` 及现有 GameSession 管理自有进程、独立 IPC 和存档；不替换正在运行的 DLL，不用反复读取报告代替等待验证命令结束。每次阶段交付注明实际检查结果，不能引用前次通过数充当本次结果。
