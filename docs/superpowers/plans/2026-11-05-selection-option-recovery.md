# selection_option 错误恢复实施计划

> **For agentic workers:** 使用 `superpowers:executing-plans` 在当前会话执行；最终仅作一次独立整分支审查。
>
> 当前状态：实施中。共 1 项，已完成 0 项；实现与全部验证已通过，45 份样例及文档已同步，正在提交并进行独立审查。暂无阻塞。

**Goal:** 明确未点击的选择按钮拒绝保留已有观察许可，并提供具体公开原因。

**Architecture:** `SelectionAvailability` 共用基础场景判断，分开候选与按钮的合法性检查。动作适配器先校验快照，再返回明确未提交保证；Python 通过已有动作登记恢复许可，成功仍执行原生按钮并使用既有动作等待和事件记录。

**Tech Stack:** C#/.NET 9、Godot 游戏原生按钮、Python stdio MCP 与既有 GUI 套件。

**Spec:** [selection_option 设计定稿](../../research/2026-11-05-selection-option-review.md#设计定稿)。

## Global Constraints

- 保留 `option_id`、`default/full`、按钮 ID 和紧凑成功回执，不新增 summary。
- 仅当前状态有效且尚未交互的明确拒绝恢复已有许可；过期、交互后失败、未知结果不恢复，无初始许可不创建许可。
- `set_selection_view` 完整审阅仍在本项范围外；共用判断维持 `select_card` 原有具体语义。
- 保留 81 份审阅基线样例；新返回另存，不替换旧证据。
- 不安装正式 Mod、不推送远程；验证后自行提交并合入 main、删除临时分支。

## Review Focus

- 状态过期和页面消失同时发生时，应先报告 stale_state，不返回可保留许可的普通拒绝。
- 禁用按钮可能被原生隐藏；不存在按钮与仍可见但禁用的按钮须分别准确诊断，禁止猜测尚未公开的要求。
- 按钮点击后异常不携带“未交互”保证，不让 LLM 误以为可以安全重复提交。
- 奖励重掷的新页面与旧按钮有不同生命周期，旧 ID 不因许可保留而获得跨页固定含义。
- 共用基础判断不能改变候选点击的确认预览、整包和结果页诊断，不能更改未审阅视图切换的操作语义。

## Task 1: 修复、验证并交付按钮错误恢复

**Interfaces:** `SelectionAvailability` 提供共用场景诊断及 `OptionUnavailableReason(CardSelection?, string, out NButton?)`；`GameAdapter.Selection` 仅在快照校验后、`UiChanged` 前返回 `RejectedBeforeSubmission`；Python `selection_option` 登记 `unsubmitted_rejection_unchanged=True`。

**Files:** 修改 `Actions/SelectionAvailability.cs`、`Adapter/GameAdapter.Selection.cs`、`tool_registry.py`，扩展 `tests/python/test_session_policy.py`、`tests/game/verifiers/verify_selection_option_review.py`；若需模拟可见禁用按钮，在现有双重门控检查下增加原生测试检查，不新增公开玩法工具。同步版本、选择／MCP 指南、已有 TODO 进度、工具清单和实施记录。

- [x] 写 Python 恢复矩阵：明确未提交的 illegal_action/invalid_request 保留许可；submitted、缺少保证、stale_state、game_error、交互证据均不保留；无初始许可不产生许可。
- [x] 更新 GUI 拒绝断言，先运行 Python 专项与无效按钮 GUI，确认旧实现失败于许可或笼统错误。命令均有限超时，日志放 `.tmp/2026-11-05-selection-option-recovery/`。
- [x] 实现共用基础诊断、按钮独立判断、快照优先校验和动作恢复登记；不改变实际点击、取消预览事件或成功投影。
- [x] 运行专项 Python（预期全过），构建（预期 0 错误），准备隔离运行时。全量 Python 和 C# 检查运行一遍，预期全部通过。
- [x] 运行 25 项 selection_option GUI 清单：无需刷新即可纠正无效 ID、取消／确认或结束回合；覆盖与查看战场有准确恢复提示；全部原有成功分支正常。补原生禁用按钮与过期优先检查，必要时用双重门控夹具；回归 select_card 的无效候选／预览、inspect_selection、原生测试入口门控。
- [x] 记录实际 full JSON、各组产物哈希、失败尝试和退出的自有 PID，检查样例来源、链接与旧样例哈希；按需求同步当前文档，移除“待定稿”状态。
- [ ] 提交 `fix: preserve selection option permission on preflight rejection`。独立整分支审查后处理重要发现，按项目规则自行合入 main、清理分支，不重复已通过且未受新改动影响的测试。

**Verification:** Python 专项使用 `.tmp/mcp-venv/bin/python -m unittest tests.python.test_session_policy tests.python.test_selection tests.python.test_gui_suite`；完整 Python 使用 `-m unittest discover -s tests -t . -p 'test_*.py'`，C# 使用既有 `Sts2Agent.Checks`；GUI 使用 `scripts/gui_suite.py --suite tests/game/data/gui_suite_selection_option_review.json --output <新目录>`。预期全部通过，准确记录实际数量，不把仅源码核对的边界计入游戏实测。
