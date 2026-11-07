# 占卜工具视图切换实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：实现与验收完成，共1项，已完成1项；等待独立最终审阅及合入，无阻塞。

**Goal:** set_divination_tool直接切换，返回actions_only并提供准确、安全的拒绝恢复。

**Architecture:** 单独的原生工具切换分支，共用DivinationInspection页面和按钮检查；视图注册与已有许可恢复复用，不再记录事件。divine动作保持原有流程。

**Tech Stack:** C#／Godot、Python MCP、隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-set-divination-tool-review.md#输出定稿)及其开发核验。

## Global Constraints

- tool仅big/small，default/full，不增加参数或summary；成功仅actions_only，无transition、事件或图片。
- 明确未交互拒绝保留已有许可；首次失败、已交互、未知／坏响应不生成或恢复许可；成功现场校验棋盘与工具。
- 原生切换不消耗次数、揭开或改变资源；divine保留expected_state、记录与停止边界。
- Mod0.77.0、MCP0.79.0，schema45不变；中文文档、英文注释与Conventional Commits英文描述。
- 当前工作区临时分支，验证后自行合入main；不正式安装或推送；旧样本不覆盖。

## Review Focus

- 无先前观察的合法切换成功并可直接divine；冷调用拒绝不会授权其他动作。
- 覆盖／完成／非法参数拒绝不改画面，已有许可可直接选择、领取、proceed或结束回合。
- 已交互、矛盾保证或坏响应清除许可，切换中上下文改变不可报告成功。
- tools[].enabled、available_actions与执行一致，Ready无递归，静态读取范围保持。
- 重复当前工具不消费资源；divine与事件／占卜详情回归保留真实揭开、奖励及结算。

### Task 1: 视图切换与安全拒绝恢复

**Files:** 修改GameAdapter.Divination.cs、GameAdapter.Resources.cs、GameAdapter.AvailableTools.cs、DivinationInspection.cs、tool_registry.py及版本；新增test_divination_tool_view.py、verify_divination_tool_view.py及套件；更新受影响契约测试／验证器、divination/mcp/architecture/gui/TODO文档与实际样本。

**Interfaces:** 新增SetDivinationTool(Request)、ToolSwitchUnavailableReason(screen?)、ToolUnavailableReason(screen,tool)、SelectedTool(screen)。消费既有SettledObservation、Success、ui_unchanged和actions_only投影；divine仍用原有DivinationRequest。

- [x] **Step 1:** Python行为测试冷切换成功→直接揭开、无transition、明确拒绝恢复、冷拒绝／已交互／未知／矛盾／坏响应、本地参数及重复切换；GUI覆盖五类审阅场景，增加冷切换及同工具快照稳定。
- [x] **Step 2:** 新Python与旧DLL至少一类GUI先失败，确认原因是旧前置许可或旧回执，保留RED日志。
- [x] **Step 3:** 拆出原生切换、共享具体原因与按钮条件；注册为无需许可且不记录的视图；切换后核对上下文与实际工具，原始参数错误提供未交互保证。
- [x] **Step 4:** 新测试变绿，全量Python、C#和构建；五类GUI及事件详情、揭开／发奖、原生响应失败等相关回归通过。
- [x] **Step 5:** 同步文档、版本及修复后实际JSON，核对日志／来源／哈希／链接／进程退出；提交feat: treat divination tool switching as a view。

新测试：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_divination_tool_view`。证据根`.tmp/2026-11-07-divination-tool-view/`。task-done使用verify_delivery.py核对已运行日志和样本，不重复构建。按[隔离运行](../../development/roundtrip.md)及[GUI指南](../../development/gui-testing.md)验收。

## 最终审阅与合入

- [ ] 一次独立最终审阅；必要问题按RED→GREEN修复。
- [ ] 归档并校验任务工作目录，合入main、删除临时分支、核销工具。
