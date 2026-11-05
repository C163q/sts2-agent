# close_map 开发核验依据

> 本文件保留审阅基线的四项缺口及来源；修复已完成约定验证，等待一次独立审查和合入，见[实施记录](2026-11-05-close-map-results-implementation.md)。下文“待修复”等描述指原审阅时的状态。

用户可读的问题、适用范围与候选方案见[审阅记录](2026-11-05-close-map-review.md)。

## 基线与来源

- 项目提交 b6eb397，Mod 0.68.0、MCP 0.70.0、schema 41。
- Linux 游戏 v0.107.1、release 59260271、RitsuLib 0.6.10；目标程序集 data_sts2_linuxbsd_x86_64/sts2.dll 的已核对 SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时 DLL 均为 `1ffb82d5790e9bc51729c44e092223ce0faa511cb302f08627bbc8820fd8d774`。沿用上一任务验证后的产物，未重新构建或安装。
- 目标版本本地证据 `.tmp/decompiled/NMapScreen.cs`：Close、AnimClose、OnBackButtonPressed、Open。Close 会同步 IsOpen=false、禁用返回按钮并取消单人战斗暂停，再等待 Tween 完成退场；本工具调用实际按钮，不直接改状态。
- 证据目录 `.tmp/2026-11-05-close-map-review/`。GUI 夹具仅准备一次性局面，后续查看／关闭由真实 MCP 调用执行。

## 代码入口

| 职责 | 位置 |
| --- | --- |
| 原生合法性、点击、等待、页面稳定性与完整文件返回 | [RequestDispatcher.cs](../../src/Sts2Agent/Adapter/RequestDispatcher.cs) 的 close_map 分支 |
| 按钮与地图就绪判断 | [MapView.cs](../../src/Sts2Agent/Observation/MapView.cs) 的 CanClose、Ready、Clear |
| 工具列表 | [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs) 的 MapView.CanClose |
| 公开注册与媒体 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py) 的 close_map，effect:view、requires_permission:false、media:true |
| 普通与专项页面投影 | [view_details.py](../../src/sts2_mcp/output/view_details.py) 的 closed_map、legacy_view_observation |
| 解码与权限 | [response_pipeline.py](../../src/sts2_mcp/output/response_pipeline.py)、[game_session.py](../../src/sts2_mcp/game_session.py) |

## CLOSE-MAP-01：未交互拒绝不恢复许可

优先级中，源码确认，待修复。原生入口拒绝使用 FileMailbox.Error，没有 ui_unchanged 保证；注册项也没有 unchanged_view_rejections。GameSession 因 effect:view 在请求前清除许可，不能按已经审阅的关闭／查看工具规则恢复。没有初始许可时不应制造许可；已点击或不确定的结果也不应恢复。

## CLOSE-MAP-02：原因没有公开区分

优先级中，源码确认，待修复。入口把所有 CanClose:false 合为 The current map cannot be closed；关闭中变化使用另一固定字符串，但都没有 public_message，公开层变为 The requested action is unavailable。合法性当前在 MapView.CanClose 和执行入口共用布尔值；可将其改为原因入口，继续用于工具列表与执行，不改变原生能否关闭。

## CLOSE-MAP-03：旧返回裁剪遗漏字段且绕过完整校验

优先级中，合成数据与源码确认，待修复。closed_map 对普通页面只用 legacy_view_observation，保留 scene/screen、turn/player/enemies/top_bar/buttons/available_actions；忽略 selection、allies 和房间对象。GameAdapter.Responses.Success 仍会附 selection_view，由公开装配生成 notes.selection；因此缺失的是结构化选牌元数据，不是全部返回提示。仅当 screen.view 为 divination 或 epilogue 才调用 observation_details，导致两种返回范围，也只有专项分支完整校验。

`validation-gap.json` 使用现有冻结 event 状态，将 event 改为缺少全部必要字段的对象；closed_map 仍接受，observation_details 抛出 ValueError。这是合成损坏响应的校验探针，不是声称游戏自然返回过坏对象。该成功解码若进入正常会话，会参与刷新动作许可；少返回内容不能替代完整解码。

建议改用 observation_details 完整校验，并按定稿应用 observation_presets.actions_only_result。普通页面补回 selection.type/status，media 可相应关闭，避免关闭占卜地图时附送 PNG；文件原始完整响应保留。业务层仍需确认这项返回策略。

## CLOSE-MAP-04：独立旧验证器固定旧契约

优先级低，源码确认。verify_mcp_map.py 仍固定 len(names-capture_screenshot)==42，而现有是43；还将 close_map 与完整 get_observation 作相等断言。其脚本未在本阶段强行运行过时入口，不能说它已通过；此次新验证器使用当前工具发现与真实调用采样。后续修复应同步旧脚本或明确替代，不通过恢复旧输出迎合测试。

## 生命周期与未验证分支

原生点击前确认 CanClose；点击后使用同一 run、graph、act、map 实例和 underlyingOverlay 身份，监听 Opened 判断重开。等待退场后 SettledObservation，再次核验。地图重开、房间／幕变化或覆盖变化返回拒绝，不自动重试；finally 解除捕获 map 上的事件。此处尚未发现需要全项目重构的依据，关闭流程可从 dispatcher 迁入现有 GameAdapter.Map.cs，与地图查看和共用合法性入口相邻。

未打开地图、正常战斗、事件、待选牌战场含牌组覆盖、原生 MapRoom 入口与占卜是本次六类采样。建筑师的特殊完整观察分支、中途重开和并发替换仅核对源码，不冒充新增 GUI 实测。

## 验证记录

- `python.log`：test_gui_suite、test_mcp_map、test_native_response_contract 共 24 项通过，2.664 秒；未因纯审阅重跑完整单元测试或 C# 构建。
- `gui/report.json`：未打开地图、正常战斗、事件三组通过；selection 在确认关闭结果后因验证器误断言 notes 全部缺失而失败。实际 notes.selection 仍由 selection_view 生成；已修正断言为仅缺失 selection 且 note 存在。原失败完整保留，未改产品输出。
- `gui-remaining/report.json`：选择战场及牌组覆盖、换幕强制入口、占卜三组通过并清理，81.684 秒；首批 97.342 秒。两个自有进程分别为 90920、91565。
- 共 56 次实际 MCP 调用，包括保留的失败审阅步骤；112 个相对文档链接与样本哈希已核对，两个自有进程均退出。6 份典型 JSON 与原 structuredContent 逐对象一致；manifest 保存原调用、下标、SHA-256 和图像块数量。
- `validation-gap.json` 保存合成损坏响应校验差异，未冒充自然游戏缺陷复现。
- 开发指南现已区分完整文件返回与当前 MCP 裁剪，并停止将固定 42 工具的旧脚本列为当前可用验收入口。代码中的这两处缺口未修复；冲突说明在 `.tmp/2026-11-05-close-map-review/documentation-conflict-report.md`，后续规格仍以本审阅问题为依据。

未覆盖所有房间、所有瞬态动画或并发人工输入；建筑师特别分支仅源码核对。正式安装未变更，未宣称现有旧独立脚本通过。
