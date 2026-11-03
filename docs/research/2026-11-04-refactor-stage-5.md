# 原生快照、路由与响应重构

当前状态：第 5 阶段实施中，8 项完成 2 项；总体完成 4／7。测试分派与快照迁移已验证，正在处理生产路由收尾、上下文和媒体，暂无阻塞。

依据：[实施计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)与[架构审查](2026-11-03-architecture-refactor-audit.md)。起始提交 `0a889b3`，Mod 0.53.0、MCP 0.55.1、schema 34。目标程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；当前版本仍以 [README](../../README.md#当前版本与前提)为准。

## 测试分派

测试请求移至 `Testing/TestRequestDispatcher.cs`，保留生命周期／控件扰动的采样前入口，以及其余测试的采样后入口。每个测试操作原有 testMode、suite、scenario、玩家存在条件保留；创建测试战斗仍检查当前状态令牌与私有可用性，不作为公开玩法工具。

新增原生门控检查在隔离图形实例中分别以关闭 testMode、关闭 suite 且未配置场景的适配器尝试 63 个测试操作，均返回 illegal_action，未替换当前对局；测试夹具本身需要双重门控。该检查不表示对所有场景组合逐项自然游玩。

验证：Mod／纯检查项目编译成功，0 警告、0 错误；60 项 C# 纯检查、571 项 Python 检查通过；GUI native_dispatch 单例通过。证据位于忽略目录 `.tmp/2026-11-04-refactor-stage-5/gui-dispatch-fixed/`，构建哈希由其 report.json 记录。首轮因新增检查的 Environment 命名冲突构建失败，随后误准备了旧 DLL；该次 GUI 拒绝未知测试请求，保留于 gui-dispatch，不计为通过。命名已修复，并先确认构建再准备新运行时。

## 快照与生产路由结构

GameObservation 持有各类对象身份、代次和同步读取器；Capture 返回 ObservationSnapshot，绑定同次 JSON、token 和原生对象身份。Observe() 保留已有文件／检查调用兼容。生产分派使用该快照的 State，浏览页面及等待逻辑分别位于 GameAdapter.Views／Settling；原有 proceed、inspect_event、药水目标等优先顺序保留。单人条件原样迁至共用 RunContext。

schema 仍为 34，没有在纯迁移中改变哈希输入；ObservationSnapshot 的 5 项新增纯检查锁定序列化样例的旧 SHA-256、token 与对象身份、占卜 dialogue 的哈希例外及可见正文不变。65 项 C# 纯检查通过；Mod／纯检查项目编译 0 警告 0 错误。gui-capture-fixed 两例通过，覆盖真实 MCP 费用拒绝后 end_turn、错误恢复、覆盖页查看和关闭后的许可，构建哈希见对应 report.json。

首轮 GUI 的 basic 分支仍把 sources:null 当非法参数，与第 3 阶段已确认的契约不同；已更新为布尔错误输入并重新运行新目录。三个相关 GUI 入口的固定旧 MCP 版本断言改为引用 SERVER_VERSION；未将旧测试失败当作新玩法故障。

## 待完成

生产路由的跨场景回归、四类详情上下文、结构化 transition、显式媒体需求及执行证据尚未声明完成。最终将补针对性 GUI、独立审查及当前指南。本轮不安装正式 Mod，不核销用户 TODO。
