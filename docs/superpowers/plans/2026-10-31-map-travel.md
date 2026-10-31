# 地图选路与跨幕实施计划

当前状态：实施中。共 3 项，已完成 2 项；接口、11 个导航图形场景及独立审阅已完成，14 个图形场景已通过，剩余提交与安装交付。暂无阻塞。

> 执行方式：使用 executing-plans，在当前功能分支连续实施，最后进行独立审阅。

**目标：** 让 LLM 按已观察候选完成原生选路，并从 Boss 奖励继续跨幕。

**设计依据：** [地图选路与跨幕](../specs/2026-10-31-map-travel-design.md)。

**架构：** 地图读取、导航执行和外部 MCP 校验分离；复用原生节点点击、跨幕按钮及现有选择/战斗边界。

**技术：** .NET 9、Godot 4.5.1、游戏 v0.107.1、RitsuLib 0.6.10、Python MCP。

## 全局约束

- 只实现单人；主线程操作游戏，逐帧异步等待。
- 不直接改写游戏状态代替公开动作；不揭晓问号或未来幕。
- 工具仅接受 `node_id`，令牌与原生合法候选共同校验。
- 不自动领剩余奖励，不自动选后续输入，不重试未知结果。

## 审阅重点

- 非连线飞鞋路线合法，普通连线不耗次数；耗尽后拒绝非连线。
- 地图关闭、绘图、上层选择或过渡期间不可选路。
- 原生入场父任务可能等待玩家输入；及时返回选择。
- 同坐标跨幕、地图重新生成、外部操作使旧令牌失效。
- Boss 前进不得误在旧奖励页或新幕动画中宣告完成。

## 任务

### 1. MCP 接口与地图摘要

涉及 `scripts/map_details.py`、`game_output.py`、`game_tools.py`、`inspection_details.py`、`mcp_catalog.py`、`mcp_server.py`、`roundtrip_client.py`；测试 `test_map_travel.py`。

- [x] 写失败测试：严格 ID 参数；摘要投影过滤；隐藏地图拒绝动作；允许非连线候选；成功动作续接，损坏输出撤销许可。
- [x] 运行测试确认 RED，再实现 `travel_arguments` / `map_summary` 和工具分发；运行新测试至 GREEN。

### 2. 原生选路和跨幕等待

涉及 `MapInspection.cs`、`GameAdapter.Navigation.cs`、`NavigationTasks.cs`、`BridgeMod.cs`、`GameAdapter.cs`、`GameAdapter.Rewards.cs`，及隔离 `NavigationFixture.cs` / `verify_navigation.py`。

- [x] 先编写图形验证，旧版确认缺少地图摘要和工具。
- [x] 暴露地图摘要、地图身份代数和选路动作；点击当前原生节点，复用 CombatEntryCapture 和 ActionObservation。
- [x] 监测原生跨幕 Task，阻止未完成跨幕宣告完成；新增隔离场景和 CLI 启动参数。
- [x] 构建并运行图形验证：普通战斗/非战斗、选择、奖励放弃、飞鞋、双 Boss、跨幕、终章及错误/旧 ID。

### 3. 验证、文档与交付

涉及地图、奖励、观察、MCP、构建指南与 README，版本和本次调研记录。

- [x] 完整 Python 与 C# 检查、编译、相关奖励/事件/地图回归；保留实际截图和未验证范围。
- [x] 独立审阅，修正问题；文档同步真实能力，版本升至 Mod 0.29.0 / MCP 0.25.0 / schema 14。
- [ ] 提交并本地合入 main，备份安装 Mod；验证文件一致，不触碰正式运行的对局。
