# 开箱动作拒绝恢复实施计划

> **For agentic workers:** 使用 superpowers:executing-plans 自行执行，一次独立审查收尾。
>
> 当前状态：实施中，共1项，已完成0项；实现、完整检查与全部图形验证通过，正在独立审查及交付，无阻塞。

**Goal:** 修复 loot_treasure 明确点击前拒绝的许可恢复与原因，保持现有参数、原生流程及精简回执。

**Architecture:** TreasureInspection 集中开箱／领取目标和前置原因，供执行与 available_actions 复用，纯读取保留独立条件。执行只在首次点击前提供未提交保证，后续仍使用原生两阶段动作与总预算。Python复用既有恢复机制。

**Tech Stack:** .NET9/Godot/目标游戏、Python stdio MCP、unittest、隔离图形套件。

**Spec:** [已确认方案](../../research/2026-11-06-loot-treasure-review.md)及其开发依据；基线46e5fd1。

## Global Constraints

- 保留 open_only 默认false、default/full及动作精简回执，不新增summary、筛选或结果字段。
- 仅首次UiChanged/ForceClick前的明确拒绝带action_submitted:false；已点击、过期、超时、未知或矛盾证据清除许可。
- 未开箱仍正常开箱；空箱和已领取仅说明当前无可领取遗物，不读取未揭示内容或补隐藏历史。
- 25秒总预算、额外奖励/选择边界、无后台继续领取、延迟效果等待保持；proceed不扩大修改。
- 诊断仅公开固定说明；静态读取与动作Ready条件分开。复用现有测试设施，不增加新测试路由。
- Mod0.71.1/MCP0.73.1，schema41；正式Mod不自动安装。完成后本地合入main并清理临时分支。

## Review Focus

1. 第一阶段已经开箱后的第二次点击受阻、超时或异常，整个请求仍不能声明未执行。
2. 额外奖励、选择、地图或原生遗物效果改变上下文时，不继续点击旧对象，不重复发金币。
3. 共用前置入口与available_actions在关闭、空箱、已领取、禁用、离屏、隐藏及未就绪时一致；读取不误用动作条件。
4. 公开拒绝原因仅用当前UI及合法性信息，不公开未开箱内容、内部路径或异常；初始无许可仍不制造许可。
5. 同一25秒预算和两个原生点击保留，proceed与只读查看、已有显示测试设施及局间清理保持。

### Task 1: 两项修复、共用判断与验证

**Files:**
- Modify: src/Sts2Agent/Observation/TreasureInspection.cs、Adapter/GameAdapter.Treasure.cs、GameAdapter.AvailableTools.cs。
- Modify: src/sts2_mcp/tool_registry.py、output/treasure_details.py（仅说明文字）。
- Create: tests/python/test_loot_recovery.py；Modify: tests/game/verifiers/verify_loot_treasure_review.py与现有套件。
- Modify: 版本与相关现行文档；Create: docs/research/2026-11-06-treasure-loot-recovery-implementation.md及修复后样本。

**Interfaces:** 复用FileMailbox.RejectedBeforeSubmission和ToolSpec.unsubmitted_rejection_unchanged；新增LootUnavailableReason(room,openOnly,out button)，CanLoot和实际执行共用；查看诊断继续使用暴露条件。

- [x] **Step 1: RED。** 新增Python行为测试：明确拒绝后直接合法动作；不确定/过期/已交互/矛盾证据仍清除许可；本地参数错误和无初始许可保持。更新GUI为具体诊断和直接续接，先在旧DLL运行一例证明失败。预期缺少恢复和诊断的断言失败。
- [x] **Step 2: 实现。** 集中前置检查及目标解析、首次点击前证明，接入可用工具列表；后续领取只在原有条件满足时执行。更新提示词以明确输入边界会停止。预期针对性Python通过，原生原流程保持。
- [x] **Step 3: 完整验证。** 全部Python、124项C#、构建/准备与十类GUI；原生无效参数/过期优先、拒绝直接领取/继续/选择/旅行，保留三种显示扰动。原有basic/open和查看拒绝回归。每次新目录，失败先定位，预期全部通过。
- [x] **Step 4: 交付材料。** 同步版本、文档、已有TODO覆盖，导出完整新返回，验证来源/哈希/链接/退出；正式Mod不安装。预期交付校验脚本通过。
- [ ] **Step 5: 提交与集成。** 一次独立只读审查，重要问题一次修复并验证；随后本地合入main、删除临时分支，归档并清理本计划工作区。最终校验命令为证据根verify_delivery.py。
