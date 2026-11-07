# 事件选项拒绝恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：实现与验收完成，共1项，已完成1项；等待独立最终审阅及合入，无阻塞。

**Goal:** choose_event_option点击前拒绝给出具体原因，并允许直接继续合法操作。

**Architecture:** EventInspection共享页面、动作与选项检查；执行、静态enabled和工具列表复用，Ready保持独立。MCP接入已有未提交拒绝恢复；成功仍走原生按钮和共享结算等待。

**Tech Stack:** C#／Godot／Harmony、Python MCP、隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-choose-event-option-review.md#输出定稿)及其开发核验。

## Global Constraints

- 单个非负Int32 option_id、default/full、现有精简回执，不新增summary或参数。
- 首次无许可、stale、已交互、坏响应及未知结果不恢复许可；只在原生明确保证未提交且未改UI时续接。
- 静态事件列表不增加离屏过滤；保持原生选项、选择边界、结算及可见事件记录；不正式安装或推送。
- Mod0.76.1、MCP0.78.1，schema45不变；当前工作区临时分支，验证后合入main。
- 中文文档、英文注释，Conventional Commits英文描述；历史样本不覆盖。

## Review Focus

- 覆盖页面误用后能直接取消确认、选择卡牌、领取奖励或切换占卜工具。
- 明确未提交与矛盾执行证据严格区分；冷调用和过期观察不能获得许可。
- 事件完成提示proceed；无效／旧ID与锁定原因分开；可重复原生选项保持可用。
- 详情、enabled与available_actions一致，Ready与原因检查无递归，静态读取和悬停保持原有范围。
- 事件进入首场战斗、首回合选牌和瓶中精灵复活保留实际停止原因与事件。

### Task 1: 共用事件检查与拒绝恢复

**Files:** 修改EventInspection.cs、GameAdapter.Event.cs、GameAdapter.AvailableTools.cs、tool_registry.py及版本；新增tests/python/test_event_option_recovery.py、tests/game/verifiers/verify_choose_event_option_review.py和对应套件；同步events/mcp/gui/TODO、定稿、实施记录与修复后样本。

**Interfaces:** 消费FileMailbox.RejectedBeforeSubmission及既有恢复协议；提供ActionUnavailableReason(Context?)、OptionUnavailableReason(NEventOptionButton)，与InspectionUnavailableReason共用私有页面检查。Ready独立；Clickable复用单项检查，ActionUnavailableReason另排除已完成事件。

- [x] **Step 1:** 添加Python行为测试：明确拒绝后直接合法选择、原因公开、冷调用／未知／stale／矛盾证据不续接、本地参数错误保留许可；GUI覆盖11类基线并补牌组覆盖、旧ID、完成后proceed及普通战斗。
- [x] **Step 2:** 运行新Python及旧DLL的至少一个GUI恢复测试，确认因旧行为失败并保留RED证据。
- [x] **Step 3:** 实现共享页面／动作／单项检查，执行与列表／enabled接入；明确未提交拒绝与注册恢复；更新版本及简洁说明。
- [x] **Step 4:** 新Python变绿；全量Python、C#、构建通过；专项GUI及事件详情／选牌／确认／占卜相关回归通过。
- [x] **Step 5:** 同步当前文档与修复后实际JSON；验证来源、哈希、链接、版本、进程退出和日志；提交fix: preserve event option rejection recovery。

新Python命令：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_event_option_recovery`。RED应为恢复仍要求get_observation，GREEN应为直接合法动作成功。完整验收使用[隔离运行](../../development/roundtrip.md)及[GUI指南](../../development/gui-testing.md)，证据根`.tmp/2026-11-07-event-option-recovery/`。task-done使用该目录verify_delivery.py核对已运行日志，不重复编译。

## 最终审阅与合入

- [ ] 独立最终审阅，必要问题按RED→GREEN处理。
- [ ] 归档并校验本任务工作目录，自行合入main、删除已合并分支并核销工具。
