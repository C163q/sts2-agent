# claim_reward 拒绝恢复与回执校验实施计划

> **For agentic workers:** 使用 superpowers:executing-plans 执行已确认方案。
>
> 当前状态：实施中，共 1 项，已完成 0 项；约定代码与全部验证已完成，正在独立审查和交付。无阻塞。

**Goal:** 修复领取的明确拒绝恢复、具体诊断和回执 ID 核对，保留现有参数与精简返回。

**Architecture:** RewardInspection 集中领取可用性及原因，供执行、基础观察和可用工具列表复用。Reveal 在第一次滚动前回调交互开始，执行入口只为此前拒绝提供明确未提交证明。Python 在完整响应校验时核对请求 ID，再精简并续接许可。

**Tech Stack:** .NET 9／Godot、目标游戏与 RitsuLib、Python stdio MCP、unittest 与隔离 GUI 套件。

**Spec:** [已确认审阅](../../research/2026-11-05-claim-reward-review.md)，开发证据见其链接。基线 55c02af；当前版本以 README 为准，schema 41 保持。

## Global Constraints

- reward_id 与 preset:default/full 保持；不新增 summary；原生领取、信号、后续选择和 transition 行为保持。
- 点击／滚动前明确拒绝保留已有许可，第一次滚动及点击即标记交互；状态过期、超时、损坏响应和已交互失败清除许可。
- public_message 仅使用受控原因；异常消息保留内部诊断。
- 观察、执行、许可及公开投影职责分离；proceed 共用入口的原行为须回归。
- 测试用扰动限定双重门控，重置恢复；正式 Mod 安装另需用户请求。采用当前目录临时分支，完成后自行合入 main。

## Review Focus

1. 奖励页在准备或滚动期间消失／被覆盖时，旧引用与未交互证明保持正确。
2. 多种覆盖及无本地对局时，读取与领取诊断准确、available_actions 与执行共用条件。
3. pending/choice_required 与 pending/action_completed 均保留；嵌套流程及监听清理完整。
4. 全部四种领取 status 的 ID 都在投影和许可刷新前核对；文件客户端及旧直接校验的兼容调用有明确范围。
5. 测试扰动的场景／双模式门控及局间清理可靠，proceed 与奖励查看保持正常。

### Task 1: 领取恢复、响应核对及验证

**Files:**
- Modify: src/Sts2Agent/Observation/RewardInspection.cs；src/Sts2Agent/Adapter/GameAdapter.Rewards.cs、GameAdapter.AvailableTools.cs。
- Modify: src/sts2_mcp/output/action_details.py；src/sts2_mcp/tool_registry.py。
- Create: tests/python/test_claim_recovery.py；src/Sts2Agent/Testing/Fixtures/RewardClaimFailureFixture.cs。
- Modify: 测试路由、重置及门控清单；tests/game/verifiers/verify_claim_reward_review.py 和对应套件；版本与相关现行文档。
- Create: docs/research/2026-11-05-claim-reward-recovery-implementation.md 与修复后典型 JSON。

**Interfaces:** 使用既有 FileMailbox.RejectedBeforeSubmission、GameSession.unsubmitted_rejection_unchanged 与 reader_argument:request；Reveal 增加 Action 回调参数，第一次写滚动目标前触发。

- [x] **Step 1: RED。** 新增 Python 行为测试：明确拒绝后直接结束回合；不确定／过期／已滚动拒绝仍要求观察；四种 status 的错误 ID 在 full/default 均拒绝且清除许可；本地参数错误及无初始许可保持既有行为。运行该文件，预期恢复与 ID 核对缺失导致断言失败。
- [x] **Step 2: 实现。** 集中页面与奖励行的领取检查，接入 available_actions 和 enabled；领取前错误提供具体原因及未提交证明；第一次滚动／点击前标记交互。接入 Python 请求 ID 校验和恢复声明。预期步骤 1 及奖励／动作／许可相关检查通过。
- [x] **Step 3: 原生验证设施。** 更新原八场景为修复后断言，增加原生参数／过期优先、直接错误续接和成功滚动。增加双重门控的滚动后禁用奖励扰动，验证交互事实和必须重新观察；finally 与局间 reset 恢复。预期清单可加载，设施未越过测试路由。
- [x] **Step 4: 完整验证。** 全部 Python、C# 检查、构建与隔离 GUI；GUI 使用新目录并保留失败证据。运行测试入口双模式门控，核对旧奖励、查看及 proceed 回归。预期全部通过，读取日志并记录真实范围；未通过即调查，禁止继续依赖失败步骤。
- [ ] **Step 5: 交付。** 同步版本（Mod 0.70.1、MCP 0.72.1）、现行契约与已授权 TODO 覆盖，导出修复后样本；验证链接／哈希／进程退出。提交后做一次独立全范围审查；重要问题一次修复并验证，再合入 main、清理分支与本计划临时工作区。最终验证命令为证据根 verify_delivery.py。
