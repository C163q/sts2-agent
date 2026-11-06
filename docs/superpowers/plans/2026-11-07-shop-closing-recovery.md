# 商店关闭恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：已完成，共1项，已完成1项；独立审阅通过并合入main，无剩余步骤或阻塞。

**Goal:** close_shop点击前拒绝给出准确原因，并可直接继续合法操作。

**Architecture:** ShopInspection共用页面用途和关闭检查；打开／关闭共用按钮动作和生命周期等待，购买保持独立。MCP复用已有未提交拒绝协议。

**Tech Stack:** C#／Godot／Harmony、Python MCP和隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-close-shop-review.md#输出定稿)及其开发核验。

## Global Constraints

- 无操作参数、default/full、现有成功回执；仅精简工具说明，不新增summary。
- 未观察、stale、点击后错误不恢复许可；保留打开／详情原有语义和购买行为。
- 原生按钮动作，遵循线程及生命周期；不改库存或金币、不正式安装或推送。
- Mod0.74.2、MCP0.76.2，schema43不变；中文文档、英文注释和Conventional Commits英文提交。

## Review Focus

- 首次无许可、未知／矛盾执行证据不能从拒绝生成许可。
- 已有许可在明确拒绝后可直接打开、取消选择、结束回合或继续奖励。
- 打开／详情既有提示、输入阻挡时的静态读取和购买流程不退化。
- 执行、available_actions和显示按钮enabled一致；保留原生按钮坐标与快捷键含义。
- 关闭后直接续接以MCP许可验证，直接原生读回不刷新会话；生命周期更换返回interrupted。

### Task 1: 共用关闭条件与恢复

**Files:** 修改ShopInspection.cs、GameAdapter.Shop.cs、GameAdapter.AvailableTools.cs、RequestDispatcher.cs、tool_registry.py及版本；新增tests/python/test_shop_closing.py，更新verify_close_shop_review.py；同步shop/mcp/gui/TODO、任务记录和样本。

**Interfaces:** 消费Context、FileMailbox.RejectedBeforeSubmission和既有恢复协议；提供CloseUnavailableReason(Context?)及共享ShopViewRequest；PageUnavailableReason以明确的用途枚举区分详情、打开、关闭。

- [x] **Step 1:** 新Python断言明确拒绝后直接open成功、无许可／未知／stale不续接、本地非法参数保留许可；GUI六类改为具体提示、action_submitted:false和直接合法操作成功。
- [x] **Step 2:** 运行新Python和至少一类旧DLL GUI，确认因旧恢复行为失败，保留证据。
- [x] **Step 3:** 实现共用关闭检查，执行／列表／enabled接入；共享开关按钮流程，参数拒绝与注册恢复规则接入；更新版本和说明。
- [x] **Step 4:** 新Python变绿，全量Python、C#和构建；六类专项GUI、已完成打开五类及购买／补货／详情显示回归通过。
- [x] **Step 5:** 同步当前文档与十五项以内典型修复后JSON，核对来源／哈希、链接、日志、进程退出和版本；提交fix: preserve shop closing rejection recovery。

新测试：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_shop_closing`；RED应为get_observation而非choose_legal_action，GREEN为直接open成功。完整验收遵循[隔离运行](../../development/roundtrip.md)及[GUI指南](../../development/gui-testing.md)，证据根`.tmp/2026-11-07-shop-closing-recovery/`，最终验收脚本verify_delivery.py核对真实日志和样本，不重复编译。

## 最终审阅与合入

- [x] 独立最终审阅，必要问题按RED→GREEN处理。
- [x] 归档并校验本任务工作目录，自行合入main、删除已合并分支并核销工具。
