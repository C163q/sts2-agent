# 原生快照、路由与响应重构

当前状态：第 5 阶段完成并验证，8／8 项完成；总体完成 5／7。测试分派、快照与路由、统一响应、上下文及媒体已交付；第 6–7 阶段未开始，暂无阻塞。

依据：[实施计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)与[架构审查](2026-11-03-architecture-refactor-audit.md)。起始提交 `0a889b3`，Mod 0.53.0、MCP 0.55.1、schema 34。目标程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；当前版本仍以 [README](../../README.md#当前版本与前提)为准。

## 测试分派

测试请求移至 `Testing/TestRequestDispatcher.cs`，保留生命周期／控件扰动的采样前入口，以及其余测试的采样后入口。每个测试操作原有 testMode、suite、scenario、玩家存在条件保留；创建测试战斗仍检查当前状态令牌与私有可用性，不作为公开玩法工具。

新增原生门控检查在隔离图形实例中分别以关闭 testMode、关闭 suite 且未配置场景的适配器尝试 63 个测试操作，均返回 illegal_action，未替换当前对局；测试夹具本身需要双重门控。该检查不表示对所有场景组合逐项自然游玩。

验证：Mod／纯检查项目编译成功，0 警告、0 错误；60 项 C# 纯检查、571 项 Python 检查通过；GUI native_dispatch 单例通过。证据位于忽略目录 `.tmp/2026-11-04-refactor-stage-5/gui-dispatch-fixed/`，构建哈希由其 report.json 记录。首轮因新增检查的 Environment 命名冲突构建失败，随后误准备了旧 DLL；该次 GUI 拒绝未知测试请求，保留于 gui-dispatch，不计为通过。命名已修复，并先确认构建再准备新运行时。

## 快照与生产路由结构

GameObservation 持有各类对象身份、代次和同步读取器；Capture 返回 ObservationSnapshot，绑定同次 JSON、token 和原生对象身份。Observe() 保留已有文件／检查调用兼容。生产分派使用该快照的 State，浏览页面及等待逻辑分别位于 GameAdapter.Views／Settling；原有 proceed、inspect_event、药水目标等优先顺序保留。单人条件原样迁至共用 RunContext。

schema 仍为 34，没有在纯迁移中改变哈希输入；ObservationSnapshot 的 5 项新增纯检查锁定序列化样例的旧 SHA-256、token 与对象身份、占卜 dialogue 的哈希例外及可见正文不变。65 项 C# 纯检查通过；Mod／纯检查项目编译 0 警告 0 错误。gui-capture-fixed 两例通过，覆盖真实 MCP 费用拒绝后 end_turn、错误恢复、覆盖页查看和关闭后的许可，构建哈希见对应 report.json。

首轮 GUI 的 basic 分支仍把 sources:null 当非法参数，与第 3 阶段已确认的契约不同；已更新为布尔错误输入并重新运行新目录。三个相关 GUI 入口的固定旧 MCP 版本断言改为引用 SERVER_VERSION；未将旧测试失败当作新玩法故障。

## 响应、上下文与媒体

ResponseBuilder 统一结构化组装详情上下文、动作附加结果和协议响应，不再拼接 transition 字符串。TransitionResult 统一 complete 和事件附加；各场景仍决定原停止原因，保留缓冲顺序、预留发布、截断与战斗交接，不改变事件捕获原理。

四类原来缺少上下文的详情（手牌、卡牌／药水目标、药水、遗物）从同次快照复制控制标识和 scene/screen；协议 35 在 Python 解码中要求上下文，历史片段样本保留兼容且不补造场景。界面覆盖、眼睛查看战场及终章的上下文仍沿同一采样入口。

内部 response_options.include_divination_image 将媒体需要与游戏参数分离，省略保持旧文件行为。MCP 的完整观察／summary、占卜详情及确实返回棋盘的关闭页需要图片；动作回执、actions_only/top_bar 和无棋盘的详情不捕获。close_card_view 的既有 MCP 范围没有棋盘，文件入口仍保留完整观察范围，没有借此扩大返回内容。

根部 execution 只记录正向事实，不交给 LLM；缺失或 false 不代表未执行。拒绝恢复仍仅消费已经审查的 play_card 未提交且 UI 未变保证；矛盾事实拒绝，其他动作不自动套用。规范定义见[文件协议](../development/roundtrip.md#原型接口)和[MCP 上下文](../development/mcp.md#成功结果的场景上下文)。

本次功能交付为 Mod 0.54.0、MCP 0.56.0、schema 35；持续版本与兼容基线只维护在 README。最终测试 DLL SHA-256：`c294a4144b2112573136e6aca47d816247083e1a9ef1dae14509e64b6d6e6dee`。

## 独立审查与修复

独立只读审查无 Critical／Important，提出两项低影响差异。本轮依照保留原异常分类和正向事实的要求修复，未扩大玩法范围：

- state_captured 改为成功完成 Capture 时记录，避免之后的详情／transition 序列化异常抹掉已知采样事实；明确它不保证快照晚于最后一次动作。RecordCapture 成功边界有纯检查，响应序列化异常为夹具注入，不声称自然游戏已触发。
- ResponseBuilder.Failure 使用 GetBaseException 保留旧 BridgeMod 的包装超时分类；覆盖直接、反射和单内层聚合超时，日志仍保留完整私有异常。

修复检查先失败后通过。没有延期审查项；没有追加或核销用户 TODO。

## 最终验证

- Mod 和 C# 检查项目编译成功，0 警告、0 错误；86 项 C# 纯检查通过。
- 575 项完整 Python 检查通过（36.201 秒），含固定 228 个 MCP／51 个 CLI 样本、媒体需求、协议上下文与矛盾执行事实；标准库 CLI --help、compileall、文档链接和 Git 差异检查通过。
- 最终同一构建的 12 个 GUI 目标场景、18 个步骤累计通过，另有全新进度的 victory_unlock 结算独立通过。涵盖测试门控、四类详情、地图／牌组／牌堆、零能量续接、事件和先古之民选牌、火堆、商店、宝箱、奖励、占卜故障、战斗交接及终章覆盖页。

GUI 的通过证据分批保存：gui-reviewed 中前 7 个场景通过；宝箱旧脚本把明确读取拒绝误当成清除许可，导致该批失败。修正后以 gui-remaining 新进程验证宝箱及后续 5 个场景，全部通过。两个批次及 gui-ending-reviewed 的 report.json 记录的 DLL 哈希完全相同；不能把失败批次整体写成全绿。摘要位于忽略目录 `.tmp/2026-11-04-refactor-stage-5/verification-summary.json`。

其他发现的旧验证假设也已同步：火堆／宝箱不再要求事件恒为空，改为核对停止／完成和事件序列；锻造明确检查 card_upgraded，基础宝箱检查 relic_obtained。占卜坏图只拒绝确实要求图像的读取，不阻断纯动作回执；私有响应选项不作为地图游戏参数。

媒体故障通过双重门控夹具注入：旧文件默认媒体在工具已实际切换后返回 screenshot_unavailable，仍保留交互和采样事实，随后无图读取确认 UI 已变化；MCP 无图读取及动作在同一故障下成功。该故障证据不等同于自然游玩复现。

本轮只运行隔离存档和自有游戏／MCP 进程，不安装正式 Mod。展示／悬停与反射辅助整理仍属于第 6 阶段，完整组合回归与兼容入口清理属于第 7 阶段；本轮不核销其他逐工具审阅。
