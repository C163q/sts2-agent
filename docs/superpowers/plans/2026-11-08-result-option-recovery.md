# 结算选项操作与错误恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> 当前状态：实施中，共3项，已完成2项；正在整理最终样例和文档，剩余一次独立审阅及合入。暂无阻塞。

**Goal:** 修复结算动作的许可恢复、具体原因及已揭晓章节查看，并核验原生结算详情的返回流程。

**Architecture:** RunResultInspection集中页面和单项的操作条件，执行、enabled与available_actions复用；GameAdapter只负责合法性、首次交互标记和原生点击。MCP沿用已注册动作的未提交恢复策略。夹具仅在测试模式准备原生页面，生产入口保持原版状态。

**Tech Stack:** C#／Godot4.5.1、.NET9、Python stdio MCP、隔离Linux游戏。

**Spec:** [审阅输出定稿](../../research/2026-11-08-run-result-option-review.md#输出定稿)；证据与原生API见[开发核验](../../research/2026-11-08-run-result-option-development-notes.md)。

## Global Constraints

- 基线0d2aa20；目标游戏v0.107.1／59260271、RitsuLib0.6.10，API核对目标程序集。
- option_id及default/full保持，不增加summary、筛选或批量点击；卡牌和展示状态规则不变。
- 冷调用、过期、已交互、不确定、坏响应清除／不建立许可；恢复只适用于有旧许可且明确未交互的拒绝。
- 时间线首次滚动即记交互；同次根页面和目标按钮仍有效才点击。
- 未获得节点不增加操作；本局关联范围及原生解锁／菜单生命周期保持。
- 采用当前工作区临时分支；用户已授权连续完成、自行提交合main。只读调研和测试不另设确认。
- 不修改用户TODO、正式安装、个人存档；不推送。版本集中更新README，schema47不变。
- 英文代码注释、中文文档、英文Conventional Commits。失败证据保留，测试有限超时，清理自有进程。

## Review Focus

1. 滚动后目标隐藏、根页面改变或按钮禁用：不得恢复旧许可或点击新对象。
2. Complete、Obtained、NotObtained混合：ID稳定、只暴露原生可操作项，章节分页不提前泄露未来内容。
3. 同一页可读但仍展示／输入被阻挡／全部按钮禁用：读取状态和动作许可语义保持分离。
4. 夹具资源与真实结算入口不同、缺失或原生禁用：不能把伪造准备当成正常路径，不能启用生产按钮。
5. 外部返回菜单后重新打开时间线、坏响应与相互矛盾的未交互声明：不得误保留本局关联或旧许可。

### Task 1: 具体拒绝、共用条件与许可恢复

**Files:** GameAdapter.RunEnding.cs、RunResultInspection.cs、tool_registry.py；新增tests/python/test_result_option_recovery.py及tests/game/verifiers/verify_result_option.py，接入tests/game/suite.py。

**Interfaces:** 消费现有RejectedBeforeSubmission、UiChanged及game_session未提交策略；产生RunResultInspection.ActionUnavailableReason(Context?)、OptionUnavailableReason(Context?,string,out NClickableControl?)，Ready与执行复用。

- [x] 写Python边界测试：明确拒绝后直接纠正；冷调用、本地参数、过期、不确定、缺失／矛盾证据、交互后拒绝及坏成功响应。
- [x] RED：70秒内运行新模块，预期旧注册策略使明确拒绝恢复失败；保留输出。GUI旧DLL的错误房间已有本次审阅RED证据，开发记录明确引用。
- [x] 实现统一判断、具体public_message、点击前明确拒绝及注册策略；BeginInteraction在首次滚动／点击前调用，滚动后重新核对相同上下文和当前目标。
- [x] GREEN：新模块及结算／对话恢复相关测试通过；全Python检查通过。Expected：许可边界保持、无新错误。
- [x] 提交独立变更并记录结果。

### Task 2: 已揭晓章节、原生详情夹具及游戏验证

**Files:** RunResultInspection.cs、BrowsableContentChecks.cs、Testing相关受控夹具、verify_result_option.py、gui_suite_result_option.json；必要时修正run_ending_details.py中由新可操作项暴露出的真实校验缺口。

**Interfaces:** 使用Task1操作判断；Options同时提供原生Obtained／Complete，ButtonText区分Reveal／View。prepare_test_browsable_history使用原生结算资源或明确未支持，不返回不可用夹具的假成功。

- [x] 编写GUI核验：旧DLL揭晓后原ID不可重读应失败；本次审阅已观察到的旧历史页点击崩溃作为夹具RED，避免重复触发同一已知准备故障。
- [x] 先核实原生结算详情资源的存在、类型和连接生命周期，再实现夹具；不凭文件名假定可用。必要调查更新记录及Ruling，继续不依赖此资源的工作。
- [x] 扩展章节选项；验证同ID揭晓→重读、可用分页及返回，未获得项不变。
- [x] GUI：错误房间纠正、真实死亡／胜利、局部展示与禁用、非法参数、过期、正常连续动作、无关时间线、滚动中变化、原生详情返回或精确支持边界。Expected：所有已支持场景通过，不重复通过范围。
- [x] 编译零警告／错误，C#检查、全Python通过；最终产物准备到隔离运行目录，记录SHA。Mod0.80.0、MCP0.82.0、schema47。
- [x] 提交并记录实测边界。

### Task 3: 文档、样例与一次独立审阅

**Files:** README.md、docs/development/run-ending.md及mcp.md、审阅和工具清单、带日期实施记录与固定样例；不新增用户TODO。

**Interfaces:** 消费前两项实际返回、日志及相同DLL；当前文档描述最终行为，旧审阅样例保留基线。

- [ ] 更新现行规则和版本；导出实际完整JSON，标明场景、参数、来源与校验值。Expected：没有生成数据冒充GUI调用。
- [ ] 验证样例重放、相对链接、版本、最终DLL一致、自有进程退出；不在无变化情况下重复编译／测试。
- [ ] 提交实现和证据后，按executing-plans做一次全分支独立审阅。Critical／Important仅一轮TDD修复并重新验收受影响部分；Minor和所有Ruling完整记录并披露，不二次派审。
- [ ] 已拥有的技能工作区归档校验后删除；自行快进合main、删除临时分支，工作区干净。Expected：不推送、不安装、没有未披露遗留。
