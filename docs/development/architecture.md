# 代码结构与验证

当前仍是针对 Linux 游戏 `v0.107.1` 的原型。游戏内 Mod、外部文件客户端与 MCP server 保持分离，不在游戏线程调用模型或等待文件请求。

## 代码职责

| 位置 | 职责 |
| --- | --- |
| `spikes/roundtrip/BridgeMod.cs` | Mod 初始化、后台文件服务和 Godot 主线程任务泵 |
| `spikes/roundtrip/FileMailbox.cs` | 原子文件协议、请求队列、响应缓存和等待超时 |
| `spikes/roundtrip/GameAdapter.AvailableTools.cs` | 当前交互上下文的工具列表及与调用入口共享的可用性条件 |
| `spikes/roundtrip/GameAdapter.cs` | 主线程观察、令牌与合法性检查、动作分派和页面生命周期；测试场景准备以测试模式隔离 |
| `spikes/roundtrip/VisibleUi.cs` | 可见控件与几何读取、共享绘制完成计数，供充能球和战场首次展示判断使用 |
| `spikes/roundtrip/*Observation.cs`、`*Inspection.cs`、`*View.cs` | 可见数据采样、按需详情、原生页面操作 |
| `spikes/roundtrip/GameAdapter.Navigation.cs`、`NavigationTasks.cs` | 原生节点点击、旅行边界和跨幕任务等待；地图摘要与身份并入基础观察 |
| `spikes/roundtrip/English*.cs`、`HoverTipText.cs` | 英语资源读取与受控格式化，不切换全局语言 |
| `scripts/roundtrip_client.py` | 标准库文件客户端和 CLI；默认玩法输出，`--raw` 保留诊断协议 |
| `scripts/game_output.py` | 已知玩法字段的递归投影与类型检查、基础观察与手牌结构校验 |
| `scripts/player_output.py` | 去除控制包装、共享悬停解释、条件数值说明和错误恢复文案 |
| `spikes/roundtrip/TurnJournal.cs`、`TurnCapture.cs`、`CombatResourceJournal.cs`、`VisibleResourceChange.cs` | RitsuLib 与原生事件记录、伤害补录及来源追踪；能量／星星通知与真实数字显示对齐，最大能量按实际分母变化采样 |
| `spikes/roundtrip/ActionEventScope.cs`、`GameAdapter.Resources.cs`、`RunResourceJournal.cs`、`RunInventoryJournal.cs` | 单次游戏动作的共享事件缓冲、响应附加及可见玩家资源、物品、永久牌组订阅；延后发布尚未展示的身份，与战斗和药水日志共用顺序及上限 |
| `spikes/roundtrip/PermanentCardCapture.cs` | 主线程原生基础变量／能量费用／附魔数量修改采集；仅永久成员有效，嵌套升级与附魔重算抑制低层重复 |
| `spikes/roundtrip/TurnBoundary.cs`、`TurnEventBuffer.cs` | 无游戏依赖的结束条件与有界事件缓冲 |
| `spikes/roundtrip/OrbCapture.cs`、`OrbJournal.cs` | 原生充能球 UI 更新与激发入口采集，共用动作缓冲；入场延后发布、隐藏取消及槽位端点合并 |
| `spikes/roundtrip/OrbInspection.cs` | 实际充能球 UI 队列、图像和数字过滤；基础观察、占用球详情及空槽帮助共用槽位对应关系 |
| `spikes/roundtrip/EventInspection.cs`、`GameAdapter.Event.cs` | 通用事件的可见页面、稳定选项 ID 和原生按钮执行 |
| `spikes/roundtrip/EventTaskTracker.cs`、`CombatJournalScope.cs` | 事件初始化/选择/Resume 任务跟踪；每次动作的初始战斗及后续入战日志所有权、原生重置前释放、房间任务等待与战斗间交接 |
| `spikes/roundtrip/DivinationInspection.cs`、`DivinationTasks.cs`、`GameAdapter.Divination.cs` | 占卜可见状态与原生点击、遮罩等待、棋盘裁剪边界和临时对白来源 |
| `spikes/roundtrip/EventConfirmation.cs`、`GameAdapter.Confirmation.cs` | 当前事件确认框的来源与可见内容、原生按钮操作和失败结算 |
| `scripts/divination_details.py` | 占卜参数与投影、PNG 有界像素校验和独立图像载体；MCP server 封装 ImageContent |
| `spikes/roundtrip/ActionSettling.cs`、`GameAdapter.ActionObservation.cs`、`CombatMotion.cs` | 统一动作停止原因复核、牌堆飞行、资源显示、生物死亡及有限 UI 过渡等待与观察稳定；页面查看单独处理 |
| `scripts/transition_details.py` | 结束回合事件的结构校验与递归过滤 |
| `scripts/inspection_details.py`、`*_details.py` | 按操作校验并投影响应；牌组、牌堆与地图等具体结构各自维护 |
| `scripts/observation_presets.py`、`available_tools.py` | 观察预设参数与精简投影、公开工具名称和动作分类 |
| `scripts/game_tools.py` | 串行游戏会话、动作令牌、检查控制权及在线程中执行文件请求 |
| `scripts/action_output.py` | 完整校验及许可处理之后的公开动作回执投影，保留事件与必要交互提示 |
| `scripts/controller_lease.py` | 每个 IPC 目录的 MCP 进程控制锁 |
| `scripts/mcp_catalog.py` | 工具名称、参数 schema、行为注解及面向模型的说明 |
| `scripts/mcp_config.py`、`screenshot_tool.py` | 启动配置校验、PNG 校验和独占保存；配置决定截图工具是否注册 |
| `spikes/roundtrip/ViewportCapture.cs` | 帧后游戏视口及指定矩形读取，不接收用户文件路径或写用户文件 |
| `scripts/mcp_server.py` | stdio 启动、MCP 分派和结果封装；保留既有脚本入口 |
| `scripts/test_*.py` | 无需游戏的单元与真实 stdio/临时文件 IPC 测试 |
| `scripts/verify_*.py`、`spikes/roundtrip/*Checks.cs` | 显式运行的真实游戏验证及原型内检查，依赖各自指定的场景 |

`roundtrip_client.player_result` 仍可导入；`mcp_server.GameTools` 和 `mcp_server.ControllerLease` 继续保留原有导入方式。标准库客户端不导入 MCP SDK。

不为统一目录而批量迁移现有脚本或 C# 文件；后续正式打包、分离测试程序集或拆分游戏适配器时，须同时更新构建路径、启动配置及独立游戏验证。

## 变更入口

事件场景复用原生同步器、选牌、奖励和战斗，不为每个事件重新实现效果。英文事件格式化按原生变量赋值与克隆来源读取分离数据，不能靠重新生成选项或全文相等猜测引用身份；契约与专属界面边界见[事件接口](events.md)。

增加工具时，先核对目标版本游戏 API 与可见信息边界，再实现游戏内采样或正常动作。外部层分别补齐操作响应校验、玩法字段投影、会话中的令牌规则和工具定义。状态、正文和字段语义只在对应的开发指南完整定义；MCP 公共规则放在服务说明，工具描述只保留用途和独特约束，参数放在 schema 中。

结构化读取和视图操作在完整校验成功响应后保存新令牌；截图仅在状态未变时保留旧令牌。动作消费旧令牌，经过完整校验的成功结果在可继续行动时提供新令牌；并发排队请求不能借用未来观察。后台文件请求通过 `anyio.to_thread.run_sync` 等待，取消后不恢复观察权限；取消不能撤回已提交的游戏操作。完整的令牌、重试和控制锁约定见 [MCP 指南](mcp.md#调用和错误语义)，文件协议见 [往返指南](roundtrip.md#原型接口)。

动作停止须覆盖会继续修改观察的整段有限流程，包括延迟启动飞牌的预览，不能只检查当时是否已有飞牌节点。`verify_action_stability.py` 通过真实 MCP 取得动作回执，在随后数秒多次读底层状态并比较令牌，再使用该 MCP 连接保存的许可继续操作；诊断读取不刷新 MCP 许可。新增异步显示链路时，应同时核对其前置阶段、可见字段及选择暂停边界。

输出投影只保留声明字段，不会证明游戏侧读取是可见的；游戏采样仍需检查 UI 与生命周期。错误类型不以 0、空数组或空对象替代。MCP 基础观察要求全部顶层字段存在，嵌套对象按实际提供的字段投影和检查类型，不把它表述为完整的 JSON Schema 校验。

## 无需游戏的验证

安装依赖后，在仓库根目录运行全部 Python 检查：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
```

覆盖文件投影、参数与错误输入、动作令牌、取消和超时、控制权竞争，以及通过真正子进程建立的 stdio 协议。测试中的游戏响应来自临时文件服务或固定载荷，不需要运行游戏，不操作正式存档。

只检查输出边界：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p 'test_output_boundaries.py'
```

C# 构建需要自行安装游戏程序集，命令见 [构建前提](roundtrip.md#前提与构建)。构建只验证编译与引用，不能替代游戏内 Mod 加载、线程与页面行为验证。

C# 停止条件与缓冲检查无需游戏，可运行 `dotnet run --project spikes/roundtrip-checks/Sts2Agent.Checks.csproj`；它不替代游戏内生命周期验证。

## 游戏内验证

多用例图形回归使用[图形测试套件](gui-testing.md)：`gui_suite.py` 管理进程、分局和证据，`verification_runtime.py` 为首批验证器提供独立/复用两种启动方式；`GameAdapter.Testing.cs` 与 `TestScenarioSettings.cs` 只承担测试生命周期和每局配置。场景白名单由 `test_scenarios.json` 同时供 Python 启动器和 C# 嵌入资源使用。

独立测试实例的准备、启动与结束回合验证见 [往返指南](roundtrip.md)。各详情和页面的 `verify_*.py` 命令见对应开发指南；页面检查会真实打开或关闭页面，往返检查会推进回合。不要把独立测试场景入口用于正式对局。

游戏 API 或生命周期变更须重新验证加载与相关行为。只修改外部输出层时，先用错误输入回归、真实 stdio 和已有合法游戏样本回放检查；报告仍须明确是否重新运行真实游戏。

## 选牌接口

`CardSelection.cs` 识别原生选择实例、数量规则和可用控件；`SelectionInspection.cs` 读取选择画面，`SelectionActions.cs` 定位并点击原生候选；`GameAdapter.Selection.cs` 处理参数、令牌、视图和结算等待。Python 的 `selection_details.py` 校验参数与详情，基础选择由 `game_output.py` 过滤。工具语义见 [选牌与查看战场](card-selection.md)。

## 出牌接口

`TargetInspection.cs` 负责可见手牌及纯目标规则查询，`GameAdapter.CardPlay.cs` 校验参数、跟踪原生入队动作并等待交互边界；`PlayFixture.cs` 只配置隔离测试初始条件。Python `card_play_details.py` 维护参数和目标响应结构，动作沿用既有会话许可及事件过滤。完整契约见 [出牌与目标查询](card-play.md)。

## 药水接口

`RunUi.cs` 判定战斗外顶栏可读范围，`PotionActions.cs` 负责可见槽位、菜单规则与目标查询，`GameAdapter.Potions.cs` 提交原生同步动作并跟踪交互边界。`PotionJournal.cs` 可独立记录战斗外药水事件，也由战斗事件记录器复用；`PotionFixture.cs` 仅配置隔离测试状态。外部参数与响应校验在 `potion_action_details.py`，工具语义见 [药水接口](potion-actions.md)。

## 奖励接口

`RewardInspection.cs` 识别奖励 UI、覆盖状态和稳定 ID，`GameAdapter.Rewards.cs` 执行原生领取及跳过/前进，`RewardCompatibility.cs` 适配目标版本已核实的互斥奖励信号参数。`RewardBoundary.cs` 独立判定已支持交互与手动处理边界。`RewardFixture.cs` 只在隔离测试模式构造场景。外部 `reward_details.py` 维护参数、观察和领取结果校验；契约见[战后搜刮](rewards.md)。

## 休息处接口

`RestSiteInspection.cs` 判定房间可见性、按钮特有灰置状态与结算后就绪；`GameAdapter.RestSite.cs` 校验并点击原生选项或前进。`DeckUpgradeSelection.cs` 读取已显示的升级比较，与原有选择工具共用确认和取消流程。`rest_site_details.py` 维护外部字段与参数边界；`RestSiteFixture.cs` 和 `verify_rest_site.py` 仅用于隔离验证。完整契约见[休息处](rest-site.md)。

宝箱房由 `TreasureInspection.cs` 读取当前原生开箱、遗物和按钮状态，`GameAdapter.Treasure.cs` 顺序点击开箱与领取；`RelicObtainTracker.cs` 仅观察原生 `RelicCmd.Obtain` 返回任务的完成状态，补上宝箱 UI 未等待遗物效果的边界，不替换游戏流程。`treasure_details.py` 校验外部字段，`TreasureFixture.cs` 与 `verify_treasure.py` 用于隔离验证。契约见[宝箱房](treasure.md)。

商店由 `ShopInspection.cs` 读取可见商品及槽位身份，`GameAdapter.Shop.cs` 点击原生商人、返回及商品；`ShopTransactions.cs` 只观察原生购买及阳伞任务，避免把选择暂停或自动购买间隙当作完成。`shop_details.py` 校验商品、摘要和购买结果；`ShopFixture.cs` 与 `verify_shop.py` 仅用于隔离验证。契约见[商店](shop.md)。

先古之民由 `AncientInspection.cs` 读取已显示对话、选项及其身份，`GameAdapter.Ancient.cs` 点击原生对话/选项并复用非战斗边界。`EnglishRelicText.cs` 使用已公开的动态引用重建英语文本，不修改游戏语言或生成随机结果；`DeckEnchantSelection.cs`、`TransformSelection.cs` 读取实际预览。`AncientFixture.cs` 与 `verify_ancients.py` 仅用于隔离测试；契约见[先古之民](ancients.md)。

`EventConfirmation.cs` 观察 Trial.DoubleDown 新增弹窗的来源，将节点绑定到当前事件及对局；`GameAdapter.Confirmation.cs` 校验许可、点击原生按钮并等待遮罩及放弃任务。`confirmation_details.py` 校验可见字段与严格参数，`verify_confirmation.py` 通过真实 MCP stdio 在隔离实例验证取消、旧令牌、来源隔离及确认失败。接口见[事件确认弹窗](events.md#事件确认弹窗)。

## 终章与结算

`EpilogueInspection.cs` 读取建筑师当前气泡和按钮；`RunResultInspection.cs` 识别原生结算、解锁及其可见内容；`RunResultMotion.cs` 追踪原生结算创建的有限补间，避免计分条提前就绪。`GameAdapter.RunEnding.cs` 执行原生按钮与令牌校验，`run_ending_details.py` 维护外部字段和工具参数边界。[接口说明](run-ending.md)统一定义阶段与返回菜单语义。
