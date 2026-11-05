# proceed 拒绝恢复与统一前进入口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 当前状态：实施与验收完成，共1项，已完成1项；最终审阅通过并已合入main，无剩余必修项或阻塞。

**Goal:** 让明确未点击的 proceed 拒绝保留许可并说明具体原因，统一执行与可用工具的判断。

**Architecture:** 新增 GameAdapter.Proceed.cs，集中选择前进按钮、诊断和执行；移除八个旧处理器的 proceed 分支。保留原生 ForceClick、各场景等待和共享事件记录，available_actions 调用同一判断。

**Tech Stack:** C# / Godot、Python MCP、真实隔离游戏 GUI。

**Spec:** [已批准的审阅方案](../../research/2026-11-06-proceed-review.md)及[开发依据](../../research/2026-11-06-proceed-development-notes.md)。用户已批准实现，沿用当前目录内临时分支及完成后自动合入 main 的约定。

## Global Constraints

- 零操作参数，preset:default/full；回执保持 actions_only 加 transition。
- 首次交互前明确拒绝使用 action_submitted:false 与公开的固定原因；状态过期、交互后失败、超时及未知结果保持保守。
- 原生前进含返回父奖励／事件、打开地图、换幕及 run_won，不改为统一打开地图。
- 保留事件的战斗日志边界、先古之民与宝箱上下文检查；全部 Godot 判断与操作在游戏线程执行。
- 修复旧终章脚本的终态断言，并实际回归其 victory_unlock 分支。
- 同步持续维护文档及用户已授权的两项错误恢复 TODO 覆盖记录，不增加新待办。

## Review Focus

- 覆盖顺序：地图、牌组、选牌和确认框优先诊断，底层奖励／事件不得被点击。GUI 增加奖励覆盖与火堆选牌、确认框拒绝。
- 奖励优先于底层房间；嵌套奖励只结束当前层。GUI 回归 nested_reward。
- 明确拒绝证明不能覆盖 stale_state、交互证据冲突、坏响应或超时。Python 许可矩阵及原生过期调用验证。
- 对话中段、占卜未完成、未开箱及商品页展开须给可操作的恢复提示。GUI 对照原因、未交互证明及随后合法动作。
- 终局允许只读工具，但没有连续玩法许可。独立新进度进程执行旧 verify_run_ending.py victory_unlock，并回归建筑师拒绝。

### Task 1: 统一前进判断、恢复与终章回归

**Files:**
- Create: `src/Sts2Agent/Adapter/GameAdapter.Proceed.cs`
- Modify: `src/Sts2Agent/Adapter/RequestDispatcher.cs`、`GameAdapter.AvailableTools.cs` 及旧八个场景处理器。
- Modify: `src/sts2_mcp/tool_registry.py`。
- Test: `tests/python/test_session_policy.py`、`tests/game/verifiers/verify_proceed_review.py`、`verify_run_ending.py`、对应 GUI 清单与白名单。
- Docs: README 版本、mcp/run-ending/roundtrip/gui-testing、工具清单、两项 TODO 覆盖记录、带日期实施报告与真实 JSON 样本。

**Interfaces:**
- Consumes: 各 Inspection.Current/Ready/Proceed/Clickable、FileMailbox.RejectedBeforeSubmission、ActionObservation、CombatJournalScope 与原生 ForceClick。
- Produces: `ProceedUnavailableReason(out ProceedTarget? target)`，仅成功时给出目标；`ProceedRequest(Request request, JsonElement before)` 统一执行；可用列表以同一原因函数返回 null 为准。

- [x] **Step 1: 添加失败用例。** Python 测试 proceed 对显式 action_submitted:false 恢复原许可；不恢复缺失证明、stale_state、超时、冲突交互证据及坏响应。GUI 审阅验证器更新为断言具体提示、未交互证明，以及无额外观察的下一合法动作；增加牌组／选择／确认覆盖，保留原正常路径。
- [x] **Step 2: 证明失败。** `timeout --kill-after=5s 60s .tmp/mcp-venv/bin/python -m unittest tests.python.test_session_policy -v` 应在 proceed 恢复用例失败；旧运行时执行最小 combat GUI 应因笼统提示或丢失许可失败。日志写入 `.tmp/2026-11-06-proceed-recovery/`，在沙箱外运行异步检查。
- [x] **Step 3: 实现。** 统一入口先校验 snapshot，再区分结算／覆盖／当前前进目标。只在全部前置判断通过后 UiChanged、ForceClick；保留每类原生等待。删除旧场景中的 proceed 操作分支；可用列表集中添加 proceed。注册未提交恢复；旧终章断言改为无 GAME_ACTIONS，并保留已有观察前置检查。Mod/MCP 补丁版本分别升至0.71.2/0.73.2。
- [x] **Step 4: 验证。** 先运行相关 Python；成功后完整 `unittest discover -s tests -t . -p 'test_*.py'`、dotnet build（目标版本依赖，无还原）、C# checks；预期全通过且构建无警告。准备隔离运行时后跑更新的 proceed GUI 清单，预期所有正常分支和拒绝恢复通过；独立新进度实例分别回归建筑师专项及旧 victory_unlock 完整脚本。保存失败日志，不将脚本前提错误误报产品故障。
- [x] **Step 5: 交付证据与文档。** 提取典型实际完整 JSON，记录来源与哈希；修正文档中未修复状态及旧终章限制，更新两项 TODO 的已覆盖工具；闭合清单为27/44。验证链接、JSON来源／哈希、构建运行时一致性、自有进程已退出及 git diff --check；私有 `.tmp/2026-11-06-proceed-recovery/verify_delivery.py` 返回成功作为 task-done 验证命令。
- [x] **Step 6: 提交和审阅。** 提交 `fix: unify proceed validation and preserve rejected action permission`；执行技能要求的一个独立完整审阅，按结果处理。归档并逐文件核对本计划执行工作区后删除原工作区；合入 main 并删除临时分支，复核交付证据，无正式安装或推送。
