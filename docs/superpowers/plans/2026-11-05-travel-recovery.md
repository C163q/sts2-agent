# 地图旅行拒绝恢复与赐福鹿角验证实施计划

> 当前状态：实施中，共 1 项，已完成 0 项。两项修复、706 项 Python、124 项 C#、11 类 GUI 与门控隔离完成；剩余独立审查与合并，暂无阻塞。
>
> 执行方式：使用 executing-plans 在当前会话实施；最终执行一次独立代码审查。用户已确认直接实施及本地自动合并。

**目标：** 修复 travel_to_node 的明确拒绝恢复和原因说明，并实测赐福鹿角三张眩晕的可见加入反馈。

**架构：** 地图候选沿用 MapInspection.Choices，抽出共用旅行可用原因；Godot 主线程保持原生滚动、点击与异步到达流程。只有首次交互之前的明确拒绝保留已有许可。遗物通过测试夹具获得，随后公开选路触发原生首回合效果，事件经现有可见性记录读取。

**技术：** C#／Godot／Harmony、Python MCP、unittest 与隔离 GUI 套件。

**规格：** [travel_to_node 审阅](../../research/2026-11-05-travel-to-node-review.md)及[开发依据](../../research/2026-11-05-travel-to-node-development-notes.md)。本计划记录附加遗物测试要求，保留原审阅 JSON 作为修复前证据。

## 全局约束

- 保留 node_id 与 default/full、完整校验后的精简动作回执；不新增 summary、位置或随机顺序字段。
- 无初始许可不制造许可，旧状态、超时、异常、交互后失败或矛盾保证不恢复；滚动前记录交互。
- 调用目标版本已核对的原生 API；不直接改写正常玩法状态。
- 正式 Mod 不安装，不推送；通过检查后提交、合入 main、清理临时分支。

## 审查重点

1. 未开地图、覆盖、绘图和非候选的原因是否准确，明确拒绝后能否直接执行合法动作。
2. 首次滚动至点击之间发生变化时，是否错误声明未交互或泄漏许可。
3. 无初始许可、旧状态与矛盾执行事实是否仍保守处理。
4. 飞鞋候选、幕起点、入场选牌与正常旅行的行为及回执是否保持。
5. 鹿角实际生成三张眩晕后，是否仅记录已展示身份和加入方向，不附送随机位置或未公开牌序。

### Task 1: 修复旅行拒绝并验证原生入场事件

**文件：** 修改 GameAdapter.Navigation.cs、MapView.cs／MapInspection.cs、tool_registry.py；修改 NavigationFixture.cs、场景目录及 verify_travel_review.py；新增 Python 回归、必要的原生测试检查与真实 JSON；同步地图、MCP、GUI 指南、版本、审阅及 TODO 既有覆盖计数。

**接口：** MapView.TravelUnavailableReason(NMapScreen?) 返回固定原因或 null；Choices 依赖该可用性检查并保留现有候选排序／规则。原生明确拒绝通过 action_submitted:false 声明无交互，注册 unsubmitted_rejection_unchanged:true。滚动或点击前 UiChanged；其后的失败不带无交互保证。

- [x] 写 Python 回归：明确 action_submitted:false 后保留许可、可直接 end_turn；缺失保证／旧状态／异常清除，矛盾交互事实变 transport_error；无初始许可不发请求。
- [x] 运行回归观察预期失败。给 navigation 增加 antler 测试场景：原生获得 BlessedAntler，下一节点为战斗；先仅编译夹具，运行真实旅行并断言恰有三条 card_added、name:Dazed、pile:draw。若不符，先分析原生预览与记录边界，再修改最小记录路径，保留原失败证据。
- [x] 实现两项旅行修复及小范围共用检查；更新 GUI 拒绝断言，增加点击前直接继续、覆盖、绘图、原生参数和过期分支。针对滚动后失败，用双重门控的测试扰动触发并核对执行事实及不恢复。
- [x] 针对性检查通过后运行完整 Python、C# 检查及最终构建；准备隔离运行时。九类旅行 GUI、antler、滚动后失败全部通过；保留原始响应并导出典型新 JSON。
- [ ] 同步文档、核销与版本；验证相对链接、样本来源／哈希、进程退出。提交并完成一次独立审查；按审查结果修复必要问题，再合入 main 清理分支。
- [ ] 执行 `PYTHONPATH=src:. .tmp/mcp-venv/bin/python .tmp/2026-11-05-travel-recovery/verify_delivery.py` 核对原始检查结果、全部 GUI、样本哈希和链接后完成 task-done；归档并清理本计划专属 workspace。最终说明遗物的实际事件、验证及未验证范围。
