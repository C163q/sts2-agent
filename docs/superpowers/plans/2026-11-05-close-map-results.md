# 地图关闭结果与恢复实施计划

> 当前状态：实施中。共 1 项，已完成 0 项；核心实现与约定验证完成，剩余一次独立审查与合入 main。暂无阻塞。
>
> For agentic workers: REQUIRED SUB-SKILL: superpowers:executing-plans。本会话实施，最终一次独立审查。

**Goal:** 修复 close_map 的拒绝恢复、具体诊断、完整校验及最小成功返回，并更新旧地图验证器。

**Architecture:** MapView.CloseUnavailableReason 服务可用工具列表与原生前置校验；关闭流程迁入 GameAdapter.Map，保留原生返回按钮和生命周期检查。Python closed_map 先完整校验观察，再用共用 actions_only_result；原始文件状态保持完整，MCP 不要求占卜 PNG。

**Tech Stack:** C#/.NET 9、Godot、Python MCP、已有隔离测试运行时。

**Spec:** [审阅及已确认方向](../../research/2026-11-05-close-map-review.md)、[开发核验](../../research/2026-11-05-close-map-development-notes.md)。用户已确认按建议实施全部四项。

## Global Constraints

- 仅保留 default/full；成功返回 scene/screen、available_actions、适用 selection.type/status；无 transition、主体或图像。
- 完整原生响应先校验，格式损坏不得刷新许可；没有输入许可不能凭拒绝创建。
- 仅明确点击前 ui_unchanged:true 的拒绝恢复已有许可；中途变更、已点击、异常和矛盾证据仍需重新观察。
- 只能点击暴露且启用的原生返回按钮；不可穿透牌组或强行关闭 MapRoom；保留重开、run/map/act/overlay 身份校验及 finally 解绑。
- 不安装正式 Mod、不推送；验证和一次独立审查后自行合入 main。Mod 0.69.0、MCP 0.71.0，schema 保持 41。

## Review Focus

1. 未打开、覆盖和禁用按钮原因正确，可用操作与执行前判断一致；不扩大原生可关闭范围。
2. 没有初始许可、显式未交互、点击后变化与矛盾事实分别处理，不制造权限。
3. 错误房间或选择数据即使最终省略也必须完整校验；地图未关闭不能当成功。
4. 战场待选牌保留 type/status，普通事件和占卜均为同一最小格式，MCP 不附或依赖 PNG。
5. 关闭继续使用原生恢复战斗与动画，监听生命周期不因迁移改变；旧独立验证器可在真实 GUI 运行。

## Task 1: close_map 完整修复与验证

**Files:** MapView.cs、GameAdapter.Map.cs、RequestDispatcher.cs；view_details.py、tool_registry.py；test_close_map_results.py、既有契约与媒体测试、verify_close_map_review.py、verify_mcp_map.py、GUI 清单及当前文档。

**Interfaces:** `MapView.CloseUnavailableReason(NMapScreen?) -> string?`；`CanClose` 为 reason==null；`GameAdapter.CloseMap(Request)` 返回完整原生成功。Python `closed_map(state)` 返回完整校验观察，MCP 注册共用 actions_only_result 与 unchanged_view_rejections。

- [x] 补充具体输出、完整校验、许可保留／无初始许可／矛盾事实及预设拒绝的测试，运行并确认失败。
- [x] 提取原生关闭流程、共用原因；接入完整观察投影与最小输出，关闭媒体需求，更新旧验证器及版本。
- [x] 地图、媒体和契约专项，以及全套 Python、C#、构建通过；保留失败证据。
- [x] 原六类 GUI 以修复后契约验证；普通战斗中串行运行旧独立地图验证器；补恢复后无需观察继续选牌／旅行。
- [ ] 同步指南、真实新 JSON 与审阅记录；提交实现，完成一次独立审查。
- [ ] 合入 main、清理临时分支及自有进程；归档并删除本计划工作区，核销工具。

验证使用有限 timeout，Python 异步和 GUI 按项目既有 socket 沙箱限制申请沙箱外执行；预计所有检查退出 0。交付校验核对全部真实日志、样本、相对链接、DLL 与进程退出，不无故重跑已通过整套验证。
