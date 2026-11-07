# divine 拒绝恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：已完成，共1项，已完成1项；独立最终审阅通过并合入main，清单阶段提醒已在核销时同步，无剩余步骤或阻塞。

**Goal:** divine明确拒绝后可直接继续合法操作，原因及可用操作与实际揭开条件一致。

**Architecture:** DivinationInspection复用页面检查，提供揭开及目标格诊断；Mod使用既有未提交拒绝保证，MCP复用许可恢复。原生动作及记录保持。

**Tech Stack:** C#／Godot、Python MCP、隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-divine-review.md#输出定稿)及其开发核验。

## Global Constraints

- x/y必填整数0–10，当前big/small范围，default/full；不加参数、summary或图片。
- 已有许可且明确未点击／未改UI的拒绝保留许可；冷调用、过期、已交互、坏响应与未知结果不恢复。
- 成功继续精简动作回执；次数、范围、诅咒立即入牌组和普通奖励领取沿原生规则。
- Mod0.77.1、MCP0.79.1，schema45不变；中文文档、英文代码注释与Conventional Commits描述。
- 当前检出临时分支，验证后自行合入main；不正式安装或推送，保留旧样本。

## Review Focus

- 前置拒绝的明确保证仅覆盖未交互路径，不扩大到过期或未知响应。
- Ready不递归调用诊断；available_actions只在至少一个可交互格存在时列出divine。
- 已清除格与覆盖页提供不同原因，重复揭开不扣次数；拒绝后直接合法揭开／领取／跳过／proceed／end_turn。
- 冷调用不授予许可；本地参数错误保留已有许可；成功仍允许连续揭开。
- 正常范围、边缘裁剪、诅咒与金币／遗物奖励时机及工具切换不回归。

### Task 1: 具体拒绝与安全恢复

**Files:** 修改GameAdapter.Divination.cs、DivinationInspection.cs、GameAdapter.AvailableTools.cs、tool_registry.py及版本；新增test_divination_recovery.py、verify_divination_recovery.py及GUI套件；更新gui runner和相关开发文档／既有TODO覆盖范围，新增实施记录与实际JSON。

**Interfaces:** 生成RevealUnavailableReason(NCrystalSphereScreen?)与CellUnavailableReason(NCrystalSphereCell?)；消费PageUnavailableReason、Ready、Clickable、RejectedBeforeSubmission与unsubmitted_rejection_unchanged。执行与available_actions共用RevealUnavailableReason，目标检查仅用于具体请求。

- [x] **Step 1:** 新Python测试明确拒绝后直接揭开、冷调用、本地参数、过期／未知／已交互／矛盾保证及坏响应；GUI覆盖无棋盘、小／大范围、重复清除、覆盖、结束、奖励／选牌、诅咒与领取时机。
- [x] **Step 2:** 先运行新Python及旧DLL的重复清除GUI，预期恢复断言失败，保留RED日志。
- [x] **Step 3:** 集中具体原因，点击前使用明确未提交保证；MCP启用已有恢复；保留原生等待与回执，缩短提示词。
- [x] **Step 4:** 新测试GREEN；完整Python、C#、构建及准备隔离实例；专项GUI及切换、详情、事件选择相关回归通过。测试脚本变量覆盖的失败已修复并保留，剩余场景通过。
- [x] **Step 5:** 更新文档与版本、实际JSON，验证日志／来源／哈希／链接／退出；提交fix: preserve permission after divination rejection。

新测试：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_divination_recovery`。证据根`.tmp/2026-11-07-divination-recovery/`。task-done使用verify_delivery.py核对已运行证据，不重复构建。GUI按[隔离测试](../../development/gui-testing.md)执行。

## 最终审阅与合入

- [x] 一次独立最终审阅；无产品问题，清单阶段提醒纳入既定收尾。
- [x] 归档并校验任务工作目录，合入main、删除临时分支、核销工具。
