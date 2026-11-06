# 商店打开拒绝恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：实施中，共1项，已完成0项；实现和验收完成，正在提交；剩余独立审阅与合入。暂无阻塞。

**Goal:** open_shop在明确点击前拒绝后可以直接继续合法操作，并提供具体原因。

**Architecture:** ShopInspection提供共用页面检查及OpenUnavailableReason；执行、静态打开按钮与available_actions复用打开检查。打开分支独立于购买监听，MCP根据明确未提交证明保留已有许可。

**Tech Stack:** C#／Godot／Harmony，Python MCP，真实游戏GUI套件。

**Spec:** [输出定稿](../../research/2026-11-07-open-shop-review.md#输出定稿)及其链接的开发核验。

## Global Constraints

- 无操作参数，preset仅default/full，精简回执与transition保持原格式。
- 不变更关闭、购买流程；首次未观察、stale、交互后失败仍要求观察。
- 使用原生商人点击，不改金币、库存或存档；不正式安装、不推送。
- 版本更新为Mod0.74.1、MCP0.76.1，schema43不变。
- 中文文档、英文注释，Conventional Commits英文提交；验收后自行合入main。

## Review Focus

- 已有许可的明确拒绝可续接，但首次没有许可不能借拒绝建立许可。
- stale及交互后错误即使包含消息也不能续接。
- 详情读取须保持可读性独立于动作就绪，旧覆盖诊断与预设不退化。
- 正常商人／假商人／阳伞使用原生流程，打开不挂购买监听。
- 静态按钮enabled、available_actions和实际打开条件一致；动作范围保留原生交互检查。

### Task 1: 统一打开条件、修复拒绝并验收

**Files:**
- Modify: src/Sts2Agent/Observation/ShopInspection.cs、src/Sts2Agent/Adapter/GameAdapter.Shop.cs、GameAdapter.AvailableTools.cs、RequestDispatcher.cs。
- Modify: src/sts2_mcp/tool_registry.py、src/Sts2Agent/Sts2Agent.json、src/sts2_mcp/mcp_server.py、README.md。
- Test: tests/python/test_shop_opening.py、tests/game/verifiers/verify_open_shop_review.py，以及已有shop套件。
- Docs: docs/development/shop.md、gui-testing.md、TODO.md，审阅清单与本任务实施记录及修复后JSON。

**Interfaces:**
- Consumes: ShopInspection.Context、Ready、FileMailbox.RejectedBeforeSubmission和GameSession现有恢复协议。
- Produces: OpenUnavailableReason(Context?)返回null或固定英文原因；明确拒绝包含action_submitted:false，open_shop注册unsubmitted_rejection_unchanged。

- [x] **Step 1:** 写test_explicit_rejection_allows_legal_close等行为测试，覆盖具体提示、首次无许可、stale、未知／矛盾执行证据；GUI改为点击前证明与合法后续操作直接成功。
- [x] **Step 2:** 运行新Python及至少一类GUI，确认旧实现因许可丢失／通用错误而失败，保留证据。
- [x] **Step 3:** 提取PageUnavailableReason(context,purpose)与活动等待原因；OpenUnavailableReason复用，详情仍允许输入阻挡期间读取；Ready复用活动判断但保持原按钮规则。
- [x] **Step 4:** 打开分支独立调用共享检查、返回明确拒绝，UiChanged后再原生ForceClick；available_actions、open.enabled接入相同检查；注册MCP证明规则与原始参数拒绝。
- [x] **Step 5:** 新Python变绿，运行全量Python、C#及构建，准备隔离运行时；五类专项GUI及普通／送货员／删牌、药水瞄准及详情显示回归通过。
- [x] **Step 6:** 同步持续文档和版本、导出修复后样本，核对来源／哈希／相对链接／进程退出，更新计划与实施记录。
- [ ] **Step 7:** 提交fix: preserve shop opening rejection recovery，并记录任务验收。

## 最终审阅与合入

- [ ] 独立最终审阅，必要问题按RED→GREEN处理。
- [ ] 将证据归档并清理本计划工作目录，自行合入main，删除临时分支，更新核销清单。

新测试命令：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_shop_opening`，RED为明确拒绝后close_shop得到observation_required，GREEN为直接成功。

完整验证命令遵循[隔离运行](../../development/roundtrip.md)及[GUI指南](../../development/gui-testing.md)，所有输出使用全新`.tmp/2026-11-07-shop-opening-recovery/`路径。最终检查使用该目录verify_delivery.py，逐条验证已有测试日志、真实样本及边界，不重复编译或改写旧证据。
