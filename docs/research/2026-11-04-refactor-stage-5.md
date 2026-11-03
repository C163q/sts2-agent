# 原生快照、路由与响应重构

当前状态：第 5 阶段实施中，8 项完成 1 项；总体完成 4／7。测试分派已迁移并验证，正在处理快照、生产路由、上下文和媒体，暂无阻塞。

依据：[实施计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)与[架构审查](2026-11-03-architecture-refactor-audit.md)。起始提交 `0a889b3`，Mod 0.53.0、MCP 0.55.1、schema 34。目标程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；当前版本仍以 [README](../../README.md#当前版本与前提)为准。

## 测试分派

测试请求移至 `Testing/TestRequestDispatcher.cs`，保留生命周期／控件扰动的采样前入口，以及其余测试的采样后入口。每个测试操作原有 testMode、suite、scenario、玩家存在条件保留；创建测试战斗仍检查当前状态令牌与私有可用性，不作为公开玩法工具。

新增原生门控检查在隔离图形实例中分别以关闭 testMode、关闭 suite 且未配置场景的适配器尝试 63 个测试操作，均返回 illegal_action，未替换当前对局；测试夹具本身需要双重门控。该检查不表示对所有场景组合逐项自然游玩。

验证：Mod／纯检查项目编译成功，0 警告、0 错误；60 项 C# 纯检查、571 项 Python 检查通过；GUI native_dispatch 单例通过。证据位于忽略目录 `.tmp/2026-11-04-refactor-stage-5/gui-dispatch-fixed/`，构建哈希由其 report.json 记录。首轮因新增检查的 Environment 命名冲突构建失败，随后误准备了旧 DLL；该次 GUI 拒绝未知测试请求，保留于 gui-dispatch，不计为通过。命名已修复，并先确认构建再准备新运行时。

## 待完成

快照和代际所有权、生产优先路由、四类详情上下文、结构化 transition、显式媒体需求及执行证据尚未声明完成。最终将补针对性 GUI、独立审查及当前指南。本轮不安装正式 Mod，不核销用户 TODO。
