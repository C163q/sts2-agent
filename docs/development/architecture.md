# 代码结构与验证

当前版本与依赖基线见[项目 README](../../README.md#当前版本与前提)，接口目录见[开发文档索引](README.md)。游戏内 Mod、外部文件客户端与 MCP server 保持分离，不在游戏线程调用模型或等待文件请求。

## 代码职责

| 位置 | 职责与主要入口 |
| --- | --- |
| [Infrastructure/](../../src/Sts2Agent/Infrastructure/) | `BridgeMod` 初始化与主线程任务泵；`FileMailbox` 负责原子文件协议、队列、缓存及超时 |
| [Adapter/](../../src/Sts2Agent/Adapter/) | `GameAdapter` 组装观察、令牌与动作分派；各 partial 文件处理对应场景；`AvailableTools` 与调用入口共用可用性条件，`Resources` 包装游戏动作的共享记录作用域 |
| [Observation/](../../src/Sts2Agent/Observation/) | 可见数据采样及专项详情；`VisibleUi`、`RunUi` 维护显示边界，`CardView/DeckView/MapView` 管理原生浏览页面，`ViewportCapture` 读取帧后图像 |
| [Actions/](../../src/Sts2Agent/Actions/) | 原生选择、目标与界面操作辅助；`ActionSettling/CombatMotion` 等等待有限流程，`EventTaskTracker/ShopTransactions/NavigationTasks` 跟踪原生任务，不替代游戏效果 |
| [Events/](../../src/Sts2Agent/Events/) | `ActionEventScope` 管理单动作缓冲；资源、物品、永久卡牌、战斗及充能球记录器采集公开变化，`CombatJournalScope` 管理战斗生命周期与交接 |
| [Localization/](../../src/Sts2Agent/Localization/) | 独立英语读取和格式化、共享悬停解释；事件及结算文本保留原生来源，不切换全局语言或重新生成随机文本 |
| [Testing/](../../src/Sts2Agent/Testing/) | 隔离夹具、原生检查及测试生命周期；随 Mod 编译，仅在相应测试门控开启时调用 |
| [roundtrip_client.py](../../src/sts2_mcp/roundtrip_client.py) | 标准库文件客户端与 CLI；默认玩法输出，`--raw` 保留诊断协议 |
| [game_tools.py](../../src/sts2_mcp/game_tools.py)、[controller_lease.py](../../src/sts2_mcp/controller_lease.py) | 串行游戏会话、动作令牌、每个 IPC 目录的进程控制锁；文件请求在线程中等待 |
| [mcp_catalog.py](../../src/sts2_mcp/mcp_catalog.py)、[mcp_server.py](../../src/sts2_mcp/mcp_server.py) | 工具描述与参数 schema、stdio 分派及结果封装 |
| [output/](../../src/sts2_mcp/output/) | `game_output/inspection_details/*_details` 校验并过滤已声明字段；`player_output` 整合共享解释与错误；`presets` 统一空值规则，`observation_presets/card_summary/selection_summary/top_bar_summary` 提供摘要，`action_output` 精简动作回执 |
| [mcp_config.py](../../src/sts2_mcp/mcp_config.py)、[screenshot_tool.py](../../src/sts2_mcp/screenshot_tool.py) | 截图配置、PNG 校验和独占文件保存；占卜图像另由 `output/divination_details.py` 校验 |
| [scripts/](../../scripts/) | 常用 CLI、运行时准备／启动及 `_bootstrap.py` 源码路径引导 |
| [tests/python/](../../tests/python/)、[tests/csharp/](../../tests/csharp/) | 无需游戏的自动检查；C# 纯检查不依赖游戏程序集 |
| [tests/game/](../../tests/game/) | `suite.py` 编排游戏验证，`verifiers/` 为显式执行的验证器，`support/` 和 `data/` 为共享代码与场景清单 |

Python 内部使用完整包导入，常用入口仍为 `scripts/mcp_server.py`，无须设置 `PYTHONPATH` 或安装项目包。`roundtrip_client.player_result`、`mcp_server.GameTools/ControllerLease` 保留兼容导入。

C# 使用根 [Sts2Agent.sln](../../Sts2Agent.sln)，包含 Mod 和纯检查项目。目录按职责分组，命名空间仍为 `Sts2Agent`；文件移动不拆分程序集。结构变化须同步构建路径、启动配置和验证入口。

## 变更入口

1. 核对目标游戏 API、当前 UI 和[可见信息边界](../observation.md)，确认调用的是原生动作或实际可读内容。
2. 在对应 `Observation/Actions/Events` 实现采样、流程或记录，通过 `Adapter` 接入游戏线程、状态校验和生命周期。事件效果复用原生同步器、选牌、奖励与战斗，不逐事件重写规则。
3. 外部层补齐响应校验、字段投影、参数 schema 和公共工具分类；会话令牌在 `GameTools` 处理。工具提示只保留用途和独特限制，字段契约放在对应开发指南，公共规则见[MCP 接入](mcp.md)。
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
