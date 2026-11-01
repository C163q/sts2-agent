# 事件确认弹窗实施计划

> 当前状态：已完成，共3项，已完成3项。确认框协议、原生交互、244项 Python、24项 C#、8个图形场景及独立审阅修复均通过；已合入 main 并备份安装 Mod0.28.0。正式游戏须完整重启，MCP须重连；正式加载与LLM自主对局未验证。暂无阻塞。
>
> 实施方式：使用 executing-plans 在当前会话执行；沿用用户自行决定并完成的授权。

**目标：** LLM 可观察并明确确认或取消 Trial 原生确认框。

**架构：** EventConfirmation 追踪原生弹窗来源，GameAdapter 执行动作和等待，Python 过滤字段并沿用观察许可。

**技术栈：** .NET9/Godot、Python3/mcp1.26.0；游戏 v0.107.1、RitsuLib0.6.10。

**规格：** [事件确认弹窗设计](../specs/2026-10-31-event-confirmation-design.md)。源码证据保存于忽略的 `.tmp/2026-10-31-confirmation/source/`。

## 审阅重点

- 同类型但不由 Trial 打开的弹窗不能得到操作许可。
- 外部取消重开同样的弹窗必须使旧观察失效。
- 模态覆盖时不能穿透读取或操作底层事件、地图、药水。
- 确认不能在点击后立即返回完整，必须等原生失败信号。
- 缺少 confirmation 字段、假按钮或不一致屏幕不能授予许可。

## 任务

### 1. 协议与原生交互

- [x] 新建 `scripts/test_event_confirmation.py`：观察投影与缺损、严格参数、许可复用、未知弹窗不授予动作；先运行失败。
- [x] 新建 `scripts/confirmation_details.py` 并接入 game_output、game_tools、inspection_details、player_output、mcp_catalog/server 和 CLI。新增 respond_to_confirmation；动作结果走完整观察。
- [x] 新建 `src/Sts2Agent/Actions/EventConfirmation.cs` 与 `GameAdapter.Confirmation.cs`，接入初始化、Observe、CardView、NonCombatBoundary；来源与按钮都核对原生源码。
- [x] 运行新增及完整 Python 测试、C# 检查与编译；版本改为 Mod0.28.0、MCP0.24.0、schema13。

### 2. 隔离图形验证与文档

- [x] 新建 `scripts/verify_confirmation.py`；test-mode fixture 仅用于未知来源弹窗/外部点击验证，不增加公共测试工具。
- [x] 验证取消、重开、旧令牌、入场、覆盖、未知来源和原生失败；保存截图及真实 stdio JSON。
- [x] 回归普通事件、占卜、战斗动作链；更新 README、events、mcp、observation、roundtrip 与本次验证记录，核对本地链接。

### 3. 审阅与交付

- [x] 使用 requesting-code-review 独立审阅最终差异；修复重要问题并验证。
- [x] 按本次范围创建 Git 提交，合入 main，核对工作区。
- [x] 备份并原子安装 DLL/manifest，核对源与目标哈希；说明正式游戏和 MCP 的重启要求及未验证范围。
