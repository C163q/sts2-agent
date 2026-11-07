# 对话推进拒绝恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> 当前状态：已完成，共1项，完成1项；实现、验收及独立审阅完成并合入main，临时分支清理。无阻塞。结果及边界见[实施记录](../../research/2026-11-07-dialogue-recovery-implementation.md)。

**Goal:** 先古之民和建筑师明确未点击的推进拒绝保留已有许可，并给出具体原因。

**Architecture:** 两类页面分别提供DialogueUnavailableReason，复用现有原生就绪与按钮判定；执行、continue.enabled和available_actions使用同一入口。沿用明确未提交保证和MCP注册恢复策略，成功仍走原生点击及既有动作观察。

**Tech Stack:** C#／Godot／RitsuLib，Python MCP及unittest，隔离GUI测试。

**Spec:** [输出定稿](../../research/2026-11-07-advance-dialogue-review.md#输出定稿)；[源码与审阅证据](../../research/2026-11-07-advance-dialogue-development-notes.md)。

## Global Constraints

- 零操作参数，preset仅default/full；不新增summary、筛选或连续推进。
- 明确未点击且未改UI的拒绝只保留已有许可；首次、过期、已交互、不确定、缺失或矛盾证据不授予许可。
- 先古最后一句转入馈赠，建筑师最终按钮使用proceed；动作回执保持精简，普通翻句events为空。
- 原生点击、线程及生命周期规则不变；不扩大为项目级对话框架。
- 不安装正式Mod，不推送；当前检出临时分支，验证后自行合入main。

## Review Focus

- 初次错误、过期令牌和伪造未提交证据不能授予许可；Python负例及GUI外部推进验证。
- 地图、牌组、选牌和奖励覆盖只返回对应恢复提示，不穿透点击；GUI检查前后快照、执行事实及直接关闭／选择／前进。
- 两类页面的按钮enabled、可用工具和真实提交一致，终章proceed不被advance_dialogue点击；GUI最终边界检查。
- 动画／资源忙碌和非单人路径仍拒绝；源码核验及可复用夹具范围内验证，未实测部分明确记录。
- 已开始交互后的异常不能带点击前保证；审阅UiChanged与ForceClick位置，Python提交及矛盾证据负例。

---

### Task 1: 修复对话推进拒绝并完成交付

**Files:**
- Modify: AncientInspection.cs、EpilogueInspection.cs、GameAdapter.Ancient.cs、GameAdapter.RunEnding.cs、GameAdapter.AvailableTools.cs、RequestDispatcher.cs、tool_registry.py。
- Create: tests/python/test_dialogue_recovery.py、tests/game/verifiers/verify_dialogue_recovery.py、tests/game/data/gui_suite_dialogue_recovery.json。
- Modify: tests/game/suite.py、README版本、Mod/MCP清单、ancients.md、run-ending.md、mcp.md及工具核销清单。
- Create: docs/research/2026-11-07-dialogue-recovery-implementation.md及修复后JSON。

**Interfaces:**
- Consumes: FileMailbox.RejectedBeforeSubmission、ToolSpec.unsubmitted_rejection_unchanged、既有Ready／Continue／Button及ActionObservation。
- Produces: AncientInspection.DialogueUnavailableReason(Context?)和EpilogueInspection.DialogueUnavailableReason(Context?)返回string?；null表示当前可推进。

- [x] Step 1: 写Python外部响应边界用例：明确未提交后的直接合法调用成功且公开原因保留；stale／submitted／缺失／矛盾证据拒绝续接；cold不发送，错误本地参数不撤销已有许可。
- [x] Step 2: 运行`python -m unittest tests.python.test_dialogue_recovery`，确认许可恢复用例因现有注册策略失败。对旧DLL运行一类GUI拒绝后直接合法操作，确认原生错误缺少具体原因及未提交保证。
- [x] Step 3: 实现两个DialogueUnavailableReason，共用原有页面／就绪判断；三个消费位置接入。点击前错误改明确拒绝，底层多余参数同样明确拒绝；注册恢复策略，保留stale及点击后的不确定语义。
- [x] Step 4: Python专项转绿；构建及C#检查、完整Python套件通过。准备隔离运行时并执行GUI：错误房间、对话中段／结束、已领馈赠、选牌、奖励、地图／牌组、stale；单独终章验证覆盖、最终按钮及run_won。预期明确拒绝不改快照且下一合法动作无需观察，成功仍原生推进一步。
- [x] Step 5: 更新维护文档及版本，导出真实full/default回执，检查来源、链接、DLL和自有进程退出；提交`fix: preserve dialogue permission and rejection reasons`。
- [x] Step 6: 一次全分支独立审阅；按实际影响处置，必要修复RED→GREEN，不重复审阅。完成记录和核销，合入main并删除临时分支。
