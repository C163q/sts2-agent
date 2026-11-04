# 代码结构与验证

当前版本与依赖基线见[项目 README](../../README.md#当前版本与前提)，接口目录见[开发文档索引](README.md)。游戏内 Mod、外部文件客户端与 MCP server 保持分离，不在游戏线程调用模型或等待文件请求。

## 代码职责

| 位置 | 职责与主要入口 |
| --- | --- |
| [Infrastructure/](../../src/Sts2Agent/Infrastructure/) | `BridgeMod` 初始化与主线程任务泵；`PrivateFields` 区分必需绑定与可选多类型字段；`Request/ResponseOptions` 定义文件请求，`RequestExecution` 保存正向事实；`FileMailbox` 负责原子文件协议、队列、缓存及超时 |
| [Adapter/](../../src/Sts2Agent/Adapter/) | `RequestDispatcher` 保留玩法优先分派；`GameAdapter` 组合采样与场景处理，Views／Settling 管理浏览与等待；`AvailableTools` 与调用入口共用可用性条件，`Resources` 包装游戏动作的共享记录作用域与执行事实；`ResponseBuilder` 组装上下文、transition 和协议 JSON，Responses partial 决定原生媒体 |
| [Observation/](../../src/Sts2Agent/Observation/) | `GameObservation` 管理采样、同步与代次，`ObservationSnapshot` 绑定状态、令牌和原生身份；可见数据及专项详情由领域读取器组合；`RunContext` 提供共用本局上下文，`VisibleUi`、`RunUi` 维护显示边界，`CardAppearance/CardPresentation` 共用实卡外观及完整牌面，`BrowsedCard` 保留隔离克隆上下文，`CombatResources` 读取独立 HUD；`CardView/DeckView/MapView` 管理原生浏览页面，`ViewportCapture` 读取帧后图像 |
| [Actions/](../../src/Sts2Agent/Actions/) | 原生选择、目标与界面操作辅助；`ActionSettling/CombatMotion` 等等待有限流程，`EventTaskTracker/ShopTransactions/NavigationTasks` 跟踪原生任务，不替代游戏效果 |
| [Events/](../../src/Sts2Agent/Events/) | `TransitionResult` 统一 complete 与事件附加，`ActionEventScope` 管理单动作缓冲；资源、物品、永久卡牌、战斗及充能球记录器采集公开变化，`CombatJournalScope` 管理战斗生命周期与交接 |
| [Localization/](../../src/Sts2Agent/Localization/) | 独立英语读取和格式化；`HoverTextSources` 共用悬停解释去重与规范来源顺序；事件及结算文本保留原生来源，不切换全局语言或重新生成随机文本 |
| [Testing/](../../src/Sts2Agent/Testing/) | TestRequestDispatcher 管理隔离测试分派；夹具、原生检查及测试生命周期；随 Mod 编译，仅在相应测试门控开启时调用 |
| [roundtrip_client.py](../../src/sts2_mcp/roundtrip_client.py) | 标准库文件客户端与 CLI；默认玩法输出，`--raw` 保留诊断协议 |
| [game_tools.py](../../src/sts2_mcp/game_tools.py)、[game_session.py](../../src/sts2_mcp/game_session.py)、[controller_lease.py](../../src/sts2_mcp/controller_lease.py) | 串行游戏会话、动作令牌、每个 IPC 目录的进程控制锁；文件请求在线程中等待 |
| [tool_registry.py](../../src/sts2_mcp/tool_registry.py)、[request_arguments.py](../../src/sts2_mcp/request_arguments.py)、[mcp_catalog.py](../../src/sts2_mcp/mcp_catalog.py)、[mcp_server.py](../../src/sts2_mcp/mcp_server.py) | ToolSpec 单一登记、公共参数规范化、工具描述与 schema、stdio 分派及结果封装 |
| [output/](../../src/sts2_mcp/output/) | `contracts/` 定义纯字段结构，`*_details` 校验领域数据，`inspection_details` 按原生操作分派，`response_pipeline.decode_success` 统一生产成功解码；`public_output` 整合共享解释与 notes，`game_output/player_output` 保留直接调用兼容；`error_output` 管理公开错误，`null_fields` 维护空值规则，`presets` 保留空值过滤兼容导入，`card_format` 统一牌面内容模式，`resource_summary` 共用资源摘要；`observation_presets/selection_summary/top_bar_summary` 提供容器摘要，`action_output` 精简动作回执 |
| [mcp_config.py](../../src/sts2_mcp/mcp_config.py)、[screenshot_tool.py](../../src/sts2_mcp/screenshot_tool.py) | 截图配置和独占文件保存；`output/media.py` 提供媒体承载及 PNG 格式校验，占卜另校验图像像素及棋盘一致性 |
| [scripts/](../../scripts/) | 常用 CLI、运行时准备／启动及 `_bootstrap.py` 源码路径引导 |
| [tests/python/](../../tests/python/)、[tests/csharp/](../../tests/csharp/) | 无需游戏的自动检查；C# 纯检查不依赖游戏程序集 |
| [tests/game/](../../tests/game/) | `suite.py` 编排游戏验证，`verifiers/` 为显式执行的验证器，`support/` 和 `data/` 为共享代码与场景清单 |

原生 `ObservationContext` 统一场景、遮挡与页面判断；`GameAdapter.Inspections` 将详情与其快照上下文绑定，内容读取器不另行定义 scene。

Python 内部使用完整包导入，常用入口仍为 `scripts/mcp_server.py`，无须设置 `PYTHONPATH` 或安装项目包。`roundtrip_client.player_result`、`mcp_server.GameTools/ControllerLease` 保留兼容导入。

C# 使用根 [Sts2Agent.sln](../../Sts2Agent.sln)，包含 Mod 和纯检查项目。目录按职责分组，命名空间仍为 `Sts2Agent`；文件移动不拆分程序集。结构变化须同步构建路径、启动配置和验证入口。

## 变更入口

1. 核对目标游戏 API、当前 UI 和[可见信息边界](../observation.md)，确认调用的是原生动作或实际可读内容。
2. 在对应 `Observation/Actions/Events` 实现采样、流程或记录，通过 `Adapter` 接入游戏线程、状态校验和生命周期。事件效果复用原生同步器、选牌、奖励与战斗，不逐事件重写规则。
3. 外部层补齐响应校验、字段投影、参数 schema 和公共工具分类；会话许可在 `GameSession` 处理。工具提示只保留用途和独特限制，字段契约放在对应开发指南，公共规则见[MCP 接入](mcp.md)。
4. 同步验证与文档，检查是否存在职责混杂或逻辑重复；重构需求按[协作约定](../../AGENTS.md)报告。

基础观察与详情、动作许可和最终公开投影按此顺序处理；不能靠 summary 或空值过滤掩盖坏响应。当前校验不是通用 JSON Schema 验证：基础观察要求全部顶层字段，嵌套对象按已提供字段投影和检查类型。

输出投影不能证明游戏采样符合可见信息边界。采样仍须核对实际 UI、遮挡和生命周期；未知值不能伪造为 0 或空容器。英语读取须保留原生变量与引用来源，不靠全文相等猜测身份，不重新生成选项或随机结果。

动作等待须覆盖仍会改变观察的有限原生流程，包括飞牌的前置预览、资源显示和生物退场；不能仅凭队列为空或 JSON 短暂不变判断完成。具体停止原因及事件字段统一见[结束回合与期间事件](end-turn.md)。令牌、取消、重试与控制锁统一见[MCP 调用规则](mcp.md#调用和错误语义)，底层协议见[往返指南](roundtrip.md#原型接口)。

## 无需游戏的验证

安装 [MCP 依赖](mcp.md#安装与游戏前提)后，在仓库根目录运行全部 Python 检查：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'
```

覆盖投影、参数、错误、令牌、取消／超时、控制权及真实子进程 stdio。游戏响应来自临时文件服务或固定载荷，不操作正式存档。只检查输出边界可运行：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_output_boundaries.py'
```

C# 停止条件与缓冲的纯检查：

```sh
dotnet run --project tests/csharp/Sts2Agent.Checks/Sts2Agent.Checks.csproj
```

Mod 构建需要自行安装游戏程序集，见[构建前提](roundtrip.md#前提与构建)。编译及纯检查不能替代游戏内加载、线程和页面行为验证。

## 游戏内验证

[图形测试套件](gui-testing.md)管理自有游戏进程、分局及证据；[往返指南](roundtrip.md)说明独立实例。具体工具的验证入口见对应开发指南，不将测试夹具用于正式对局。

动作稳定性检查在真实 MCP 回执后继续采样底层令牌，再用原 MCP 许可行动；诊断读取不刷新该许可。新增异步显示链路时，应覆盖前置阶段、可见字段及选择暂停边界。

游戏 API 或生命周期变化须验证加载和相关行为。只修改外部输出时，可先检查错误输入、真实 stdio 及合法游戏样本回放，但须明确是否重新运行真实游戏。历史检查数量和样本只在带日期的验证记录中维护。

战斗对象静态字段由 CombatantInspection.Read 的 Summary 级统一读取，get_observation 组合独立的生命、资源与手牌字段；Full 只在同一对象顺序上增加悬停说明。原生校验、Python 对象筛选和公共空值过滤分别负责不同阶段，见[战斗对象契约](combatant-inspection.md)。

## Python 输出依赖

生产 MCP 与非 raw 文件客户端均使用 `response_pipeline.decode_success(operation, state, native_arguments)`：先由 operation reader 完整校验并只保留声明内容，再用 `public_output.assemble_details` 整合共享解释和 notes；后续媒体附加、会话许可及筛选／preset 各自处理。领域读取器只向纯契约或更小的读取器依赖，不反向导入总装配。`tests/python/test_output_architecture.py` 检查包括函数内导入在内的循环依赖及边界。

文件客户端设置 `include_observation=True`，在原生响应确有完整观察时，保留经过观察校验的完整状态，再合并该操作的专项详情；这维护其既有动作／关闭页面输出范围。MCP 仍按专用工具范围返回，游戏动作随后投影为精简回执。`--raw` 不走公开解码。

`player_result` 及其旧导入路径仍可直接投影片段，供已有调用和验证代码兼容使用；它不替代按 operation 的完整校验。生产成功链路不再通过 GAMEPLAY 全工具字段并集猜测结果类型。卡牌格式化不推断 description 是否存在来决定生产读取范围；范围由领域契约与调用处明确选择。浏览工具的文件预设组合位于 `output/browse_output.py`。


## 工具登记与参数

`tool_registry.SPECS` 为公开名称、原生 operation、参数 schema／解析绑定、预设、reader／投影绑定与执行规则的唯一登记。目录、GameTools 方法、公开工具分类及成功解码从该表派生；reader 的模块／函数显式绑定，在解码时解析，避免领域分类反向导入总装配。截图独立登记且无玩法 preset；文件客户端的测试入口及 close_deck 别名保持私有兼容。

`request_arguments.normalize_request` 先检查公共类型、范围、枚举、必填与跨字段条件，再调用领域解析器；输出原生参数、投影参数及独立执行类别，不通过 handler 签名或 readOnlyHint 猜测行为。普通 inspect_selection 为读取，显式 view_upgrades 为页面操作；set_divination_tool 虽使用页面 annotation，仍需动作许可并记录 transition。媒体需求通过原生 response_options 接入，不作为公开工具参数。

`output/filtering.py` 共用可选筛选校验、位置选择与悬停关联裁剪；精确 UI 路径、战斗对象前缀、卡牌身份及遗物位置仍保持各自含义。公共筛选省略／null 表示全部，[] 表示空集合；遗物提示和结果映射均引用未筛选列表。完整解码先于筛选、摘要与最终 null 过滤。


## 会话与执行证据

GameTools 仅负责公开入口、参数拒绝与规范化请求；GameSession.execute 统一控制锁、串行请求、成功校验、媒体、投影和许可更新，transport Client 仍独立等待文件。PermissionState 的令牌／代次在请求开始时捕获，动作不能借用排队后产生的许可；取消撤销许可并阻止在途结果重新授权。

GameResponse 在内部保存成功、已提交、未知或“未提交且 UI 未变”的证据。登记表仅为已核实的 play_card／end_turn 前置拒绝声明后者，不从 illegal_action 或 readOnlyHint 推测。所有成功投影完成后才发布许可，错误保留／失效规则统一见[MCP 调用语义](mcp.md#调用和错误语义)。原生正向事实与显式媒体需求已经接入，缺失或 false 仍不代表未执行。

## 展示与悬停读取

`VisibleUi.OnScreen` 用于屏幕内控件和战场身体，`Displayed` 用于无需按视口截断的展示图标，`Browsable` 用于已打开的原生滚动列表。各入口仍检查自身显示边界，不能机械互换。`RelicInspection.Static` 供顶栏与详情共用静态字段；`PotionInspection.DisplayedHolders/Static` 共用槽位展示与静态字段，详情另检悬停条件；动作定位保留独立的位置及输入门控。不把灰色或禁用控件等同于隐藏。具体边界见[遗物](relic-inspection.md#读取边界)和[战斗对象](combatant-inspection.md#读取边界)。

通用反射读取由 `PrivateFields` 负责：`Read` 缺少必需字段时明确失败，字段值本身可合法为 null。`Optional` 仅用于选牌多类型界面的 prefs／已选卡／完成源、动画字段探测及结算多类型按钮的提示探测；这些调用的类型差异仍由领域代码负责。不得用 Optional 掩盖目标 API 绑定缺失。实节点与浏览克隆继续分别通过 CardPresentation／BrowsedCard 读取，共用 CardAppearance 的外观组装，保留克隆牌堆及目标上下文和比较侧别。

共用链路的验证证据与适用范围见[架构验收记录](../research/2026-11-04-refactor-stage-7.md)，四项已确认接口调整的完整实测返回见[JSON 样例](../research/2026-11-04-refactor-contract-examples/README.md)。历史样例不替代当前接口定义。
