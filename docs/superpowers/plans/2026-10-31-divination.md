# 占卜小游戏实施计划

> 当前状态：已完成，共4项，已完成4项。占卜图像与动作、全部本次验证、独立审阅、main合并和0.27.0备份安装均完成；正式游戏须完整重启，MCP须重连。确认框操作和视觉模型自主试玩不在本次交付验证范围。
>
> 实施方式：使用 executing-plans 在当前会话执行，逐项验证，最后独立审阅。

**目标：** LLM 可通过真实可见图像和原生按钮完成占卜。

**架构：** 独立 DivinationInspection 读取 UI、裁剪已绘制棋盘；GameAdapter 执行原生按钮并等待完整结算。Python 过滤文字并把私有图像转换为 MCP ImageContent，沿用观察令牌。

**规格：** [占卜规格](../specs/2026-10-31-divination-design.md)。技术栈为 .NET9/Godot、Python3、mcp1.26.0；目标游戏 v0.107.1，RitsuLib0.6.10。

## 审阅重点

- 动态 shader 图像不能进入观察令牌，逻辑覆盖状态与忙碌状态必须进入。
- 最后一次点击仍在结算时不可提前返回 complete。
- 图片不能穿透奖励/地图，也不能在缺图时继续授予操作许可。
- 原生子奖励等待父任务时仍须可以选牌、腾药水栏和前进。
- 重复格、bool/float坐标、旧观察及外部点击不能误执行。

## 任务

### 1. 可见投影与 MCP 图像

- [x] 在 `scripts/test_divination.py` 写并运行失败测试：严格参数、未知字段过滤、覆盖字段 null、坏 PNG、真实 stdio 两内容块及 JSON 不含 base64。
- [x] 新增 `scripts/divination_details.py`，接入 game_output、inspection_details、game_tools、mcp_server/catalog；使用独立图像载体承接已校验图片，保留现有纯 JSON 工具行为。
- [x] 运行新增测试及完整 Python 测试，结果记录至忽略的本次证据目录。

### 2. 原生观察与动作

- [x] 在图形验证脚本新增占卜断言，先验证当前返回 manual_input_required 而失败。
- [x] 新增 DivinationInspection、原生任务监听和 GameAdapter.Divination；核对 NClickableControl.ForceClick、目标 GodotSharp Image/Transform API 和遮罩 shader。
- [x] 接入 Observe、Success、NonCombatBoundary、RunUi、proceed、inspect_event；支持3/6次及原生子奖励边界。
- [x] 编译并运行真实图形占卜验证，截图核对坐标和雾边界。

### 3. 边界与回归

- [x] 通过隔离 fixture 验证重复格、边缘裁剪、完整揭开诅咒、奖励、满药水栏、最后结算和地图覆盖；fixture 隐藏真值只用于断言，不进入公开观察。
- [x] 运行通用事件、Trial、商店、奖励、战斗回归及完整 Python/C# 检查，独立审阅并处理缺陷。

### 4. 文档与交付

- [x] 更新版本、README、事件/占卜/MCP/观察说明，添加可格式化的 JSON 示例与视觉客户端前提。
- [x] 记录程序集哈希、截图、实测结果、未覆盖范围；检查 diff 与文档链接。
- [x] 创建本次提交、合入 main，备份并安装已测试 Mod；说明完整重启与重连要求。
