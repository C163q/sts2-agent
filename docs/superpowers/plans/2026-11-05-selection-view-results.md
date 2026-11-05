# set_selection_view 修复及精简实施计划

> **For agentic workers:** 使用 `superpowers:executing-plans` 在当前会话执行，最终只做一次独立整分支审查。
>
> 当前状态：实施中。共 1 项，已完成 0 项；实现、构建及 688 项 Python／124 项 C# 已通过，8 组主 GUI、9 组回归、6 项原生检查及 6 份典型新样例完成，正在最终资料核对和独立审查。暂无阻塞。

**Goal:** 明确未切换的拒绝保留旧许可并说明原因，成功结果仅返回 actions_only 内容。

**Architecture:** 在 `SelectionAvailability` 添加视图专属诊断，供可用操作与实际请求复用；原生切换拆到独立适配文件。Python 复用既有 view 未交互保证与 actions_only 投影；完整解码、许可刷新、原生眼睛与逐帧等待保持不变。

**Tech Stack:** C#/.NET 9、Godot 原生 NPeekButton、Python stdio MCP、现有单元和隔离 GUI 设施。

**Spec:** [设计定稿](../../research/2026-11-05-selection-view-review.md#设计定稿)。

## Global Constraints

- 保留 view=battlefield/selection 与 default/full，不新增 summary/actions_only 参数，不返回 transition。
- 成功恰含 scene、screen、available_actions、selection:{type,status}；不从精简字段推断许可，底层文件仍完整。
- 明确未交互拒绝使用 ui_unchanged:true 和 unchanged_view_rejections，仅恢复已有许可；首次失败、交互后失败、异常、矛盾证据不制造许可。
- 视图允许当前选择处于 battlefield，不复用会拒绝 battlefield 的卡牌／按钮前置检查。
- 保留旧 6 份审阅 JSON；新版本 Mod 0.67.0、MCP 0.69.0、schema 40，原生 API 基线不变。
- 不正式安装、不推送；用户已授权直接实现及自动本地合并，复用干净 checkout 临时分支与隔离运行时。

## Review Focus

- 同一视图的重复请求不点击，仍提供新许可；没有原生眼睛不能伪造切换。
- 隐藏／禁用眼睛与覆盖选择应有准确的不同原因，available_actions 和执行条件一致。
- 点击后选择变化或异常不能带未交互保证；正常切换仍使用原生流程，不能直接设置 peeking。
- 缩减输出后仍能执行已知 ID 或确认，但首次未读候选时测试不得用内部快照代替公开读取来获得 ID。
- 历史验证器和冻结契约应识别精简后的公共结果，不能通过恢复旧完整输出来迁就测试。

## Task 1: 实现、验证及交付

**Interfaces:** `SelectionAvailability.ViewUnavailableReason(CardSelection?)`；新增 `Adapter/GameAdapter.SelectionView.cs` 的 `SetSelectionView(Request, CardSelection?, string)`；ToolSpec 登记 view 未交互保证并使用 `observation_presets:actions_only_result`。

**Files:** 上述文件及 `GameAdapter.Selection.cs`、`GameAdapter.AvailableTools.cs`、`tool_registry.py`，相关 Python／GUI 测试、版本及当前指南。必要的隐藏／禁用眼睛检查仅放双重测试门控，复用 grid_manual 夹具，不新增公开玩法工具。

- [x] 写 Python 失败测试：view 的未交互保证、缺少保证、已交互、矛盾、首次无许可；full/default 精确成功字段、格式校验失败不刷新许可、无新增 preset。
- [x] 修改 8 项 GUI 断言并先运行旧实现：拒绝应具体并允许直接合法续接；成功只返回最小字段；用另列原生证据核对保留选择及不重复点击，首次未读 ID 仍用公开 inspect_selection 获取。确认失败来自旧行为。
- [x] 实现共享可用性、独立切换流程、公开固定诊断与 view 保证；复用完整解码后投影。专项 Python 转绿，构建零警告／错误。
- [x] 准备隔离运行时，运行 8 项主 GUI；检查覆盖页恢复、往返保留、重复请求、无许可首次成功／首次拒绝，补隐藏／禁用眼睛及门控检查；按受影响范围回归旧选择验证器和卡牌／按钮工具。全量 Python、C# 各运行一遍，无新改动不重复全量测试。
- [x] 保存典型新 JSON、失败与通过证据、哈希及退出 PID，同步选择／MCP 文档、TODO 既有进度及清单，校验旧 6 份样例未改、链接有效。
- [ ] 提交 `fix: recover selection view rejections and compact results`，完成一次独立整分支审查并处理重要问题，合入 main、删除临时分支，核销工具。

**Verification:** Python 专项 `-m unittest tests.python.test_selection tests.python.test_session_policy tests.python.test_tool_contracts tests.python.test_default_presets`，全量 `-m unittest discover -s tests -t . -p 'test_*.py'`；构建 `dotnet build Sts2Agent.sln ... --no-restore`，C# `dotnet run --project tests/csharp/Sts2Agent.Checks --no-build --no-restore`；GUI `scripts/gui_suite.py --suite tests/game/data/gui_suite_selection_view_review.json --output <新目录>`。每条命令有限超时，证据位于 `.tmp/2026-11-05-selection-view-results/`；预期全部通过，最终资料检查逐项核对实际数量及样例来源。
