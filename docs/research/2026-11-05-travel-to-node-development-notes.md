# travel_to_node 开发核验依据

> 本文保留提交 3627c2c 的审阅基线；49 项单元、九种 GUI 与 10 份原始样本已完成。修复已获确认，当前实施另见[修复记录](2026-11-05-travel-recovery-implementation.md)，下文的缺口描述不是修复后行为。用户可读的问题与候选方案见[审阅记录](2026-11-05-travel-to-node-review.md)。

## 基线与来源

- 项目提交 3627c2c，Mod 0.69.0、MCP 0.71.0、schema 41。
- 核对日期 2026-11-05；Linux v0.107.1、release 59260271，RitsuLib 0.6.10。
- 游戏安装目录相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，已重新核对 SHA-256：d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建及隔离运行时 DLL 均为 d188e26338c54fa7687bbf02ed43fd96d037b72027410a43f7b007a5ea6bcb4f；复用已经验证的产物，无生产代码改动，不重新构建或安装。
- 本地目标版本证据：`.tmp/decompiled/NMapScreen.cs` 的 RecalculateTravelability、OnMapPointSelectedLocally、TravelToMapCoord、ProcessScrollEvent、IsNodeOnScreen；`.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Screens.Map.NMapPoint.decompiled.cs` 的 OnRelease。原生选点入队 VoteForMapCoordAction，随后旅行动画和 EnterMapCoord 负责离房与入场。本工具调用 ForceClick，不直接调用旅行或进入房间 API。
- 测试原始记录 `.tmp/2026-11-05-travel-review/`；夹具仅准备隔离局面，公开工具通过真实 stdio MCP 执行。

## 当前职责与链路

| 职责 | 当前入口 |
| --- | --- |
| 参数、状态令牌、候选、滚动、点击与到达等待 | [GameAdapter.Navigation.cs](../../src/Sts2Agent/Adapter/GameAdapter.Navigation.cs) 的 TravelRequest |
| 原生地图可见性／就绪与候选 | [MapView.cs](../../src/Sts2Agent/Observation/MapView.cs)、[MapInspection.cs](../../src/Sts2Agent/Observation/MapInspection.cs) 的 Choices |
| 可用操作 | [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)，直接检查 Choices 数量 |
| 跨房间战斗记录与入场任务 | [CombatJournalScope.cs](../../src/Sts2Agent/Events/CombatJournalScope.cs)、[NavigationTasks.cs](../../src/Sts2Agent/Actions/NavigationTasks.cs) |
| 等待稳定输入边界 | [GameAdapter.ActionObservation.cs](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)、[GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 的 NonCombatBoundary |
| 公开参数和注册 | [map_details.py](../../src/sts2_mcp/output/map_details.py) 的 travel_arguments／TRAVEL_SCHEMA、[tool_registry.py](../../src/sts2_mcp/tool_registry.py) |
| 完整解码、动作裁剪、许可更新 | [transition_details.py](../../src/sts2_mcp/output/transition_details.py)、[action_output.py](../../src/sts2_mcp/output/action_output.py)、[game_session.py](../../src/sts2_mcp/game_session.py) |

原生前置检查按规范 ID → expected_state → run/map/Ready/LocalPlayer → Choices 中的节点执行。单人和覆盖要求通过 Ready→Current→Clear 间接约束；绘图、切幕、debug travel 和原生候选开关由 Choices 约束。可用列表与执行使用同一 Choices，未发现二者候选规则分叉。

滚动最多 24 次，每次通过原生 ProcessScrollEvent 发送 InputEventPanGesture 后等待 6 帧。每轮检查同一 run、graph、act 及候选对象，露出后再次检查，再 UiChanged、ForceClick。到达要求当前坐标与目标一致；同局、地图或幕变化返回 interrupted。ActionObservation 等待入场任务及 UI 稳定 250ms，通常限时 25 秒；选牌边界可以及时返回，不死等父任务。

## TRAVEL-01：未交互拒绝不保留许可

优先级中，源码与 GUI 确认。TravelRequest 使用普通 FileMailbox.Error；注册项没有 unsubmitted_rejection_unchanged。执行事实虽然显示 ui_interaction_started:false、action_submission_observed:false，但并不构成明确保证，GameSession 正确地不据此恢复许可。非候选、关闭及覆盖拒绝后直接合法操作得到 observation_required。

候选修复：已完成参数和旧状态校验后，在确定没有任何滚动／点击的拒绝上使用明确保证，并注册恢复。没有初始许可不能创建许可，stale_state、异常、超时及发生交互后的失败不能恢复。注意当前 UiChanged 在滚动之后才调用；若增加恢复，必须在首次滚动前标记真实交互，或将滚动后的失败单独按已交互处理，不能把全部点击前拒绝都当作无变化。

## TRAVEL-02：具体拒绝没有公开

优先级中，源码与 GUI 确认。所有原生错误文本未设置 public_message，因此公开 illegal_action 统一为 The requested action is unavailable。原生最早分支也把无地图和被覆盖合并，绘图则落入节点不可选。

候选修复：仅公开固定、经检查的原因，区分无对局／单人、未打开地图、卡牌页覆盖、其他覆盖、过渡／旅行／尚未就绪、绘图／旅行开关、非候选等。继续用共用候选规则判断实际能否旅行，不在 Python 重新猜测原生路径。

## 重构范围与已核对部分

旅行检查已经集中在小文件中，无需重新拆分整个动作系统。建议只把地图旅行的可用原因整理成可复用的小入口，保留 Choices 为候选依据，并明确滚动／点击前后的拒绝边界。共用地图就绪检查不应因提供错误文本而改变正常可用性。

成功结果已经通过 end_turn_details 完整校验观察和 transition 后，再 action_result 裁剪为 actions_only 加 transition；没有 close_map 原先的局部解码缺口。default/full 仍使用统一过滤，原始文件响应保留完整观察。没有新增选路事件；普通入房 events 可以为空，普通战斗入场实测为能量恢复及抽牌。CombatJournalScope 仅在 hadCombat 已为 true 的后续战斗保留 combat_started，所以普通单次入场没有此标记；该标记用于同次动作的战斗交接，并非遗漏普通开战事件。未知房间只有到达后才读取实际 UI，未见提前泄露未来房间内容的路径。

## 文档同步

地图指南原先笼统要求“失败或不完整结果须重新观察”，会把可本地修正且保留许可的参数错误也包含进去。已按当前代码细分：旧状态、超时、不确定或不完整结果要求观察，本地参数错误保留已有许可，原生非法操作当前仍会清除。只是修正文档范围，没有把两项实现缺口写成已修复。

## 验证与边界

- `python.log`：test_map_travel、test_map_presets、test_map_coverage、test_mcp_observation_sources、test_gui_suite 共 49 项通过，3.201 秒。
- [GUI 清单](../../tests/game/data/gui_suite_travel_review.json)与[验证器](../../tests/game/verifiers/verify_travel_review.py)记录真实参数、structuredContent、原生错误及执行事实；九例全部通过，238.154 秒，一个自有游戏进程，进程退出后交付；测试使用上述 DLL。
- 共 67 次真实 MCP 调用；原生测试辅助请求另有记录。basic 覆盖无初始许可、地图关闭、参数错误、非候选、上层牌组、绘图状态／过期和滚动后的旅行；其余八例检查飞鞋跳线、普通战斗、入场选牌、商店、宝箱、问号、先古之民和双 Boss。原始证据无失败后覆盖或自动重试。
- 火堆与普通战斗成功后直接调用合法操作；choice 在 choice_required 后按需查看候选并继续原生选牌。未领奖励已消失；飞鞋次数按原生规则变化。滚动辅助使用原生输入，未记录每个候选的像素位置，因此不把这项实测表述为所有离屏布局均已验证。
- [10 份 full 样本](2026-11-05-travel-to-node-examples/README.md)逐对象匹配原 structuredContent，manifest 保存 SHA-256 和来源。GUI 夹具只准备局面，公开工具不使用测试入口替代旅行。
- 没有生产代码修改，因此不重新构建、重跑 C# 或完整 Python；49 项针对性检查加实际游戏加载／行为作为本阶段依据。不新增 TODO，不安装正式 Mod，不核销工具。
- 不声称任意并发页面变化、所有遗物 Hook、多人或第三方地图均已 GUI 验证。超时／中断、异常和旧状态的保守处理另核对源码。
