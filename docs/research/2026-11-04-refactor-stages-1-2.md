# 工具重构第 1–2 阶段实施记录

> 当前状态：本轮第 1–2 阶段全部完成并验证，整体完成 2／7。固定行为、解除循环依赖、统一成功解码已交付；第 3–7 阶段留待后续，当前没有正在执行的步骤，暂无阻塞。

## 范围与结果

依据[重构计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)和[源码审查](2026-11-03-architecture-refactor-audit.md)，固定工具现有输出，分离 Python 契约、领域校验与公开装配，并让 MCP 和非 raw 文件客户端使用统一的成功解码入口。本轮不改变四项已经确认、留待后续阶段实施的筛选／上下文／遗物规则。

起始提交 a9eb4d7，Mod 0.53.0、MCP 0.54.0、观察 schema 34。本轮 MCP 更新为 0.54.1，Mod 与 schema 保持原值；当前版本仍只在 README 维护。未修改原生 C#、游戏 API、线程、事件记录、许可策略或动作等待；未运行游戏或安装 Mod。

## 第 1 阶段：固定行为

- [固定样本](../../tests/data/tool_contracts/)包含 228 组 MCP 调用及 51 组 CLI 调用，覆盖全部 42 个玩法工具的现有预设、成功、明确拒绝和参数拒绝；另保留媒体、共享提示、事件方向／null、空筛选和部分无效位置。
- states.json 与 expected.json 分别去重保存输入和固定期望，cases.json 与 cli_cases.json 引用它们。期望不在测试运行时由生产实现生成。
- 样本来自基线版本和既有单元夹具，是合成原生响应，不冒充自然游玩证据。自然禁用图标、跨房间动画等仍由后续原生阶段补采。
- FakeGame 和 map_payload 迁入 tests/python/support/fake_game.py；原 test_mcp_server 导入处保留兼容，既有测试调用不变。
- 基线 Python 541 项通过，加入样本及文件客户端检查后 544 项通过；C# 纯检查 60 项通过。

独立提交：ce5b217，`test: capture tool contracts before architecture refactor`。

## 第 2 阶段：共用输出链路

| 职责 | 当前入口 |
| --- | --- |
| 纯字段形状与枚举 | output/contracts/；不依赖会话、reader 或总装配 |
| 领域校验 | 各 *_details；手牌、选牌、观察、UI、药水及战斗字段分别归属自己的入口 |
| 按原生操作分派 | inspection_details；关闭页面与带结果的动作校验位于 view_details／action_details，避免观察反向依赖动作 |
| 生产成功解码 | response_pipeline.decode_success；不处理许可、用户筛选、预设或媒体附加 |
| 共享说明及 notes | public_output.assemble_details；接收已校验数据并保持输入不变 |
| 空值与媒体基础类型 | null_fields／media；不依赖 preset 装饰器或占卜 reader |
| 文件浏览预设组合 | browse_output；卡牌格式模块不再反向导入总解码 |
| 旧直接调用 | player_result 及 game_output；保留片段投影和现有导入路径，生产成功链路不经 GAMEPLAY 并集 |

完整领域校验先于筛选与 summary。生产卡牌范围由契约和调用入口明确选择，不按 description 是否存在猜测正文范围。旧片段兼容投影仍识别历史片段形态，不将该兼容入口当作完整原生校验使用。

Python 输出模块的静态依赖已消除原有 22 模块强连通分量；自动检查同时遍历函数内导入，防止把循环藏进延迟导入。另检查纯 contracts 和领域 reader 不反向导入公开总装配。

## 保留和收紧的行为

- 228 组固定 MCP 结果、原生调用参数与媒体内容保持一致；51 组 CLI 结果和默认值保持一致。遗物提示仍使用旧的筛选后下标，显式 null 的接受范围及缺少 scene 的工具也未提前迁移。
- CLI 的完整原生观察范围独立于 MCP 专用详情／动作回执。统一解码通过 include_observation=True，在确有完整观察字段时先校验完整观察，再合并该操作的详情；不使用大范围字段并集猜测工具类型。
- CLI 两个既有专用入口 start_test_combat／close_deck 继续可用；没有加入 MCP catalog 或 available_actions。raw 保留原始包装，不走公开解码。
- CLI 原先部分入口只做宽松投影，会接受缺少必需字段的坏响应。现在按原生操作完整校验，统一返回 transport_error；新增容器检查避免坏 state 引发未处理异常。这是本阶段允许的坏响应拒绝收紧，不改变合法结果。
- 旧 player_result 的直接调用仍可转换不完整片段，不能据此推断 CLI 或 MCP 会接受同样的不完整原生响应。现行指南已区分两个入口。
- 占卜图片仍在 MCP 原有位置附加和校验；媒体捕获与动作结果的原生耦合留在第 5 阶段处理。动作许可／错误恢复集中化留在第 4 阶段，不借此次解码重构扩大拒绝后的许可保留范围。

## 验证与审查

本机日志保留在被忽略的 `.tmp/2026-11-04-refactor-stages-1-2/`。以下区分基线、红绿过程与最终验收，不将中间失败记为通过：

| 检查 | 证据与结果 |
| --- | --- |
| 基线 | python-baseline.log：541 通过；csharp-baseline.log：60 个 PASS |
| 第 1 阶段 | python-stage1-final.log：544 通过 |
| 依赖方向 RED | architecture-red.log：2 项失败，分别是缺纯契约及既有循环 |
| 纯契约迁移 | python-contracts-move.log：546 通过 |
| CLI 缺字段 RED | pipeline-red.log：38 个子例失败，证明原路径未检查必需字段；统一解码后通过 |
| 非对象 state RED | pipeline-containers-red.log：90 个异常子例，统一入口增加容器检查后通过 |
| 旧 CLI 入口 RED | legacy-cli-red.log：2 个入口未登记，补显式文件兼容路由后通过 |
| 定向 GREEN | pipeline-reviewed-local.log：9 项通过，覆盖输出依赖、缺字段、坏嵌套、额外字段、输入不变性、raw、旧入口及 CLI 固定结果 |
| 全量最终检查 | python-final.log：552 项通过，34.891 秒；compileall、标准库 CLI --help 与 Git 差异检查通过 |

独立只读审查使用 gpt-6.1-sol／high，核对本轮代码、既有契约、CLI 完整观察合并、字段过滤、卡牌范围及兼容入口。未发现可复现 Critical／Important 或 Minor；审查者定向检查 7 项通过，另比较 144 组成功样本的新解码与旧兼容投影，结果一致。最终全量运行由主执行者完成。

未验证范围：真实游戏加载、自然动画、实战对局、原生新上下文与遗物禁用 note；这些没有被本轮 Python 重构实现，不能用固定样本或编译替代后续 GUI。用户 TODO 完成数与原工具逐项审阅的 4／43 完成数保持不变。
