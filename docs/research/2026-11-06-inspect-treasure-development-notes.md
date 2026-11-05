# inspect_treasure 开发核验依据

> 当前状态：现状核验完成，待确认修复与 summary。59 项 Python、七类 GUI、102 次 MCP、四种损坏上下文及 14 份完整样本已核对。用户可读结论见[审阅记录](2026-11-06-inspect-treasure-review.md)，尚未修改生产行为。

## 基线与证据

- 项目提交 d01713c；Mod 0.70.1、MCP 0.72.1、schema 41。
- 核对日期 2026-11-06；Linux v0.107.1／release 59260271，RitsuLib 0.6.10。游戏安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时 DLL 均为 ee2bc3a12d4571d9fdc131644646771664451fe440fc7e3f33d22bb429c0cf8b；沿用已验证产物，无构建、版本更新或正式安装。
- 目标版本本地源码 `.tmp/2026-10-31-treasure/source/` 中 NTreasureRoom.cs、NTreasureRoomRelicCollection.cs、NTreasureRoomRelicHolder.cs；焦点规则另核对 `.tmp/2026-11-03-architecture-refactor/` 中 NButton.cs 与 NClickableControl.cs。
- 原始证据根 `.tmp/2026-11-06-inspect-treasure/`，夹具只准备隔离状态；开箱、领取、选择、覆盖与后续推进使用真实 stdio MCP。

## 问题清单

| 编号 | 优先级 | 影响与证据 | 状态 |
| --- | --- | --- | --- |
| TREASURE-01 | 中 | 原生无宝箱／覆盖拒绝的内部原因未作为 public_message 公开，均映射笼统提示；GUI 对照 native_error 确认 | 待讨论修复 |
| TREASURE-02 | 中 | 详情未校验 screen 与 treasure.status:visible 一致；四类合成损坏响应均被接受并创建许可 | 待讨论修复 |
| TREASURE-03 | 低 | Read(full:true) 对 Relic(room) 无条件调用正文，缺少 HoverAccess 判定与不可悬停说明 | 源码边界已确认，未新增禁用扰动实测，待讨论修复 |

## 当前实现职责

| 职责 | 入口 |
| --- | --- |
| 当前房间、暴露、开箱／遗物／按钮状态及正文读取 | [TreasureInspection.cs](../../src/Sts2Agent/Observation/TreasureInspection.cs) |
| 查看与原生开箱／领取共用分发 | [GameAdapter.Treasure.cs](../../src/Sts2Agent/Adapter/GameAdapter.Treasure.cs) |
| 工具范围、纯读取许可与公共错误 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)、[game_session.py](../../src/sts2_mcp/game_session.py)、[error_output.py](../../src/sts2_mcp/output/error_output.py) |
| 宝箱内容、上下文与公共装配 | [treasure_details.py](../../src/sts2_mcp/output/treasure_details.py)、[inspection_details.py](../../src/sts2_mcp/output/inspection_details.py)、[scene_context.py](../../src/sts2_mcp/output/scene_context.py) |

TreasureInspection.Relic 先要求 Opened 和 Picking，再读取 SingleplayerRelicHolder，核对 holder／图标 OnScreen 及非空纹理。尚未开箱时不会读取 TreasureRoomRelicSynchronizer 的预生成遗物。Read(full:true) 使用 RelicInspection.Details，正文与额外关键词来自模型实际 HoverTips，经英语文本入口读取。

NTreasureRoomRelicHolder.OnFocus 同样使用 Relic.Model.HoverTips。NTreasureRoom.OpenChest 先完成正常金币和额外奖励，再初始化遗物并执行 AnimIn；领取后等待原生 RelicPickingFinished，再关闭集合并启用 Proceed。额外奖励、嵌套奖励、选择和地图覆盖时，原生适配器通过 Exposed 拒绝详情；基础观察把相应 treasure 标为 covered。

成功详情经 InspectionSuccess 补上同次快照 scene/screen，当前正常路径未发现上下文分叉；没有 available_actions 符合已确认的详情工具职责。inspect 分支不要求 Ready，因此支持静态读取未就绪页面；修复应维持这一点，不把点击合法性整体套到读取。

## TREASURE-01：错误公开与许可恢复

TreasureRequest 在 Current 为空或未 Exposed 时使用 FileMailbox.Error，未设置 public_message；内部统一写 Return to an available single-player treasure room，公开层显示 The requested action is unavailable。建议集中查看前置原因，与 available_actions 中的 inspect_treasure 判定复用，覆盖无房间、地图、牌组、选择、奖励、预览和过渡等原因。

不存在此前动作工具的许可丢失问题。spec.effect 为 read，GameSession.READ_REJECTIONS 保留已有许可；首次失败不生成新许可。no_treasure 实测无初始许可时仍要求观察，已有许可时拒绝后直接 end_turn 成功；额外奖励、嵌套奖励及选牌覆盖后也直接继续原生动作。basic 在地图覆盖读取拒绝后调用 loot_treasure，抵达原生 illegal_action，证明读取保留了许可；loot_treasure 自身拒绝后的恢复另属后续审阅。

## TREASURE-02：详情上下文一致性

inspect_treasure_details 仅验证 scene 为 treasure 及完整宝箱对象；共用 scene_context 验证枚举和字段类型，未要求 screen 是当前暴露的宝箱画面。

context-probe.json 从真实已开箱原始成功响应复制，仅修改 screen 为 covered/map、hidden、not_ready、visible/deck。decode_success 和 GameTools.inspect_treasure 的 full 均接受，并从无许可状态创建后续操作许可。探针是内存回复，不调用游戏；正常游戏中的覆盖详情会被拒绝，不能把该探针描述成自然泄漏。

建议在详情入口核对 scene/screen，按原生暴露语义要求 screen 为 visible 且无浏览 view。损坏结果在预设和许可刷新前返回 transport_error。基础观察中的 covered 宝箱仍保留既有结构。

## TREASURE-03：读取、悬停与点击

Read(full:true) 在 Relic 返回对象后无条件读取 description 和 hover_tips。Relic 只检查开箱／选择标记、显示位置与纹理，没有 HoverAccess.CanFocus 或等价判断。NClickableControl.AllowFocusWhileDisabled 默认 false，Disable 关闭输入并令 FocusMode=None；原生 RelicFtueCheck 会暂时禁用集合，领取处理也会禁用 holder。正常就绪样本均可悬停，不能据此证明所有过渡／外部 UI 变化都可悬停。

建议沿用现有[遗物边界](../development/relic-inspection.md#读取边界)：静态身份继续提供，不可悬停时 description:null、hover_tips:[]，并通过公共 unavailable_hover_sources／note 标出 treasure.relic；Python 的完整遗物字段形状需要允许该空值。该边界尚未新增人工禁用实测，实施时应补充。

另有读取用的 OnScreen 视口截断，和已审阅遗物工具的 Displayed 规则不同。建议分开显示、悬停、点击条件，读取使用 Displayed 的隐藏／透明／容器裁剪，RelicClickable 保留动作所需位置、启用和原生动画检查。这里没有可滚动候选列表被截断的实测，不能称为自然丢失宝箱遗物的复现。

## 参数与小范围重构建议

新增 summary 复用 treasure_details 的静态 relic{name,enabled}，继承 default 的 relic:null 例外；full/default 保留正文。可将原生静态房间／遗物读取与悬停扩展分开，确保 get_observation 的各预设和 inspect_treasure.summary 使用同一静态格式。当前为单件遗物，不增加筛选。

## 验证与范围

- python.log：test_treasure、test_gui_suite、test_default_presets、test_session_policy、test_response_pipeline 共 59 项通过，3.365 秒。
- [验证器](../../tests/game/verifiers/verify_treasure_inspection_review.py)与[套件](../../tests/game/data/gui_suite_treasure_inspection_review.json)：七类 GUI 全部通过，165.657 秒，102 次 MCP，自有进程 165213 已退出。包含 basic、empty、extra、nested、choice、no_treasure、map_pending。
- [14 份完整样本](2026-11-06-inspect-treasure-examples/README.md)逐对象对照 structuredContent，12 份 full、2 份 default；无图片。
- 验证器保留审阅基线的笼统提示断言；实施修复时须更新错误预期及新增预设覆盖。
- 未改变生产代码，不重跑完整 Python／C# 或构建。opening 瞬态仅核对源码；不可悬停与离屏条件仅源码核对，未添加测试扰动。多人、藏宝图、全部遗物组合及第三方宝箱未在此专项新增实测。

样本 14 项哈希、206 个相对链接、构建／隔离运行时一致性及自有进程退出已校验，结果保存在证据根 verification.json。现行指南已补充实现限制；悬停边界与说明差异记录于证据根 documentation-conflict-report.md，补充文档不代表问题已修复。
