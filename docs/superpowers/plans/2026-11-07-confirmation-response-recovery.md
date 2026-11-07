# Trial 确认响应恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：已完成，共1项，已完成1项；终态断言已补齐，最终798项及确认复查通过，已归档并合入main，无剩余步骤或阻塞。

**Goal:** respond_to_confirmation明确拒绝后可直接继续合法操作，提示及可用操作与真实按钮状态一致。

**Architecture:** EventConfirmation集中页面／动作／按钮检查，Ready独立；复用现有未提交拒绝恢复。旧验证器迁入共享隔离实例流程，测试按钮状态通过严格门控的私有入口调整。

**Tech Stack:** C#／Godot、Python MCP、隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-respond-to-confirmation-review.md#输出定稿)及其开发核验。

## Global Constraints

- 仅原生单人Trial来源；option仅confirm/cancel，default/full，不增加summary或公共参数。
- 明确点击前拒绝保留已有许可；冷调用、过期、已交互、未知／坏响应不恢复。
- 保留来源／实例绑定及原生取消、放弃等待、事件与终态只读工具。
- Mod0.77.2、MCP0.79.2，schema45不变；当前检出临时分支，自行提交合入main，旧样本保留，不正式安装或推送。

## Review Focus

- 未提交保证仅覆盖未交互分支；过期令牌与替换弹窗不能恢复许可或被误点。
- Ready不递归调用诊断，执行／enabled／available_actions一致；两个禁用按钮不造成坏观察或虚假工具列表。
- 无弹窗、取消后重复、覆盖及非Trial来源给准确原因；合法后续动作直接执行，未知来源弹窗保持人工处理。
- 取消不改资源／事件RNG，可连续重开；confirm仍等原生放弃完成并返回run_lost及实际结算查看工具。
- 新私有按钮夹具严格门控；旧验证器正确复用同一测试局，不启动或接管正式对局。

### Task 1: 拒绝恢复、统一检查与验证器迁移

**Files:** 修改EventConfirmation.cs、GameAdapter.Confirmation.cs、GameAdapter.AvailableTools.cs、tool_registry.py及版本；迁移verify_confirmation.py、配置suite；新增test_confirmation_recovery.py；扩展ConfirmationFixture、TestRequestDispatcher与TestDispatchChecks；同步事件／MCP／GUI／既有TODO及研究文档和实际JSON。

**Interfaces:** ActionUnavailableReason(NAbandonRunConfirmPopup?)、ButtonUnavailableReason(popup,NPopupYesNoButton)；Clickable复用按钮检查。私有set_test_confirmation_buttons接受两个bool confirm/cancel，使用原生SetEnabled；仅test_mode及trial场景可执行。

- [x] **Step 1:** Python测试明确拒绝后直接取消／重开、冷调用、本地参数、过期／未知／矛盾／坏响应；迁移GUI六类审阅场景并新增按钮场景。
- [x] **Step 2:** 新Python先失败；先仅编译测试夹具，GUI在两个按钮禁用后暴露旧工具列表造成的观察失败，保留RED。首次夹具接线失败已修正并保留，随后得到有效RED。
- [x] **Step 3:** 集中原因及至少一按钮条件；点击前使用未提交保证，MCP启用现有恢复；原生响应与边界保持。
- [x] **Step 4:** 新测试GREEN；完整Python、C#、最终构建；七类GUI、事件确认进入及私有入口门控回归通过；验证器非复用的独立启动分支另在自有主菜单实例通过。
- [x] **Step 5:** 更新版本、文档及实际JSON，核对日志／哈希／来源／退出；提交fix: preserve permission after confirmation rejection。

证据根`.tmp/2026-11-07-confirmation-response-recovery/`；新测试为`.tmp/mcp-venv/bin/python -m unittest tests.python.test_confirmation_recovery`。task-done使用verify_delivery.py核对已运行证据，不重复构建；最终GUI仅使用最终DLL。

## 最终审阅与合入

- [x] 一次独立最终审阅；长期终态断言按既定迁移要求补齐，变异RED→GREEN及完整798项、确认GUI复查通过。
- [x] 核对归档任务工作目录、合入main并删除临时分支；核销工具与同步清单阶段。
