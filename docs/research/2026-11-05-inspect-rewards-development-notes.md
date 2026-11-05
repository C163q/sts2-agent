# inspect_rewards 开发核验依据

> 本文保留 ae47d3d 的审阅基线：46 项检查、七种 GUI、9 份样本与两项探针。三项修复、summary 和 reward_ids 已确认并进入[实施与验证](2026-11-05-reward-inspection-presets-implementation.md)；下文缺口及原返回用于审阅基线对照。用户可读的问题与参数建议见[审阅记录](2026-11-05-inspect-rewards-review.md)。

## 基线与证据

- 项目提交 ae47d3d，Mod 0.69.1、MCP 0.71.1、schema 41。
- 核对日期 2026-11-05；Linux v0.107.1／release 59260271、RitsuLib 0.6.10。目标程序集安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，已核对 SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时 DLL 均为 d43d0d187331cf38918f751d8bd9b7439f8d2e9b3683fd0540c178ceaf6f6671。沿用已验证产物，无 Mod 或 MCP 生产代码改动，不重新构建或安装。
- 目标版本本地源码：`.tmp/2026-10-31-rewards/source/Nodes.Rewards.NRewardButton.cs` 的 OnFocus 直接使用 Reward.HoverTips；`Nodes.Screens.NRewardsScreen.cs` 的 Reload 按奖励对象生成普通行／互斥组并设置 Loot／Mugged 标题；`Rewards.Reward.cs` 的 HoverTips 在 ExtraHoverTips 后追加互斥组说明；`Rewards.SpecialCardReward.cs` 的 ExtraHoverTips 提供已指定卡牌预览。普通 CardReward 的 Description 只是未展开的选牌入口，不读取其内部候选。
- 原始证据根 `.tmp/2026-11-05-inspect-rewards/`。夹具只准备隔离局面，后续读取、覆盖、领取和离房由真实公开 MCP 调用执行。

## 代码职责

| 职责 | 入口 |
| --- | --- |
| 当前奖励页、就绪与完整可浏览行、稳定身份及英文提示 | [RewardInspection.cs](../../src/Sts2Agent/Observation/RewardInspection.cs) |
| 读取／领取／前进的原生入口 | [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 的 RewardRequest |
| available_actions 同一可用性判定 | [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)，Ready 且单人时提供 inspect_rewards |
| 参数、只读属性与默认预设 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py) 的 inspect_rewards；NO_ARGUMENTS 加通用 default/full |
| 奖励结构与类型校验 | [reward_details.py](../../src/sts2_mcp/output/reward_details.py) 的 rewards_details／inspect_rewards_details |
| 上下文与公共装配 | [inspection_details.py](../../src/sts2_mcp/output/inspection_details.py)、[scene_context.py](../../src/sts2_mcp/output/scene_context.py)、[public_output.py](../../src/sts2_mcp/output/public_output.py) |
| 许可与错误公开 | [game_session.py](../../src/sts2_mcp/game_session.py)、[error_output.py](../../src/sts2_mcp/output/error_output.py) |

RewardInspection.Buttons 使用 Shown 而非 OnScreen 筛选可滚动行和标签；Proceed 保留静态按钮的可见判断。Ready 同时要求奖励暴露、无淡入动画、所有原生行启用、动作队列空且无进行中战斗。RewardRequest 的 inspect 分支不执行 UiChanged、滚动或 ForceClick。读结果经 InspectionSuccess 使用同一快照上下文；公共装配统一补 scene/screen，因此 reward_details 内硬编码 rewards 不造成当前上下文分叉。

CardHoverTip 沿用已确认的[卡牌格式例外](2026-11-03-card-format-coverage.md)：悬停预览只有标题／正文，不将提示里的预览卡变成可操作候选或提前赋予完整实例字段。

## REWARDS-01：具体拒绝原因未公开

优先级中，源码与 GUI 确认。RewardRequest 把 Current 为空、未 Ready 与非单人合并为普通 FileMailbox.Error；public_message 未设置，公开层变成 The requested action is unavailable。建议将读取可用原因集中为小入口，供读取和 available_actions 共用，区分无奖励、覆盖、预览／动画／队列等等待与单人要求。保留当前纯读取恢复路径，不改为动作提交协议。

这里没有丢失已有许可的同类缺口：spec.effect 为 read，GameSession.READ_REJECTIONS 会保留已有许可；无初始许可不制造新许可。真实覆盖／非奖励拒绝后直接合法操作用于证明这一点。

## REWARDS-02：上下文矛盾的成功没有拒绝

优先级中，合成损坏探针确认，不冒充自然游戏复现。inspect_rewards_details 只要求 scene 为 rewards、奖励 full 内容为 visible；共用 scene_context 只核对 screen 字段类型／枚举，不核对奖励详情与 screen 的一致性。

synthetic-context-probe.json 从真实成功原始 state 复制，仅将 screen 分别改成 covered/map、hidden、not_ready。三种情况均通过 decode_success 和 GameTools.inspect_rewards，并由无初始许可的会话保存新令牌。实际 GameAdapter 仍通过 Ready 拒绝覆盖页，未发现正常路径返回同类矛盾内容；问题在接收损坏响应的防护层。

建议只在奖励详情入口核对其已暴露上下文，拒绝 screen 不是当前奖励详情页面的成功对象；清除许可并返回 transport_error。详情工具无需完整基础观察才能校验这一不变量，也无需为此重构所有房间读取器。

首次异步探针误在沙箱运行，20 秒超时且无输出；改在沙箱外以 30 秒超时运行后通过，probe-context.log 和合成结果保留。该探针使用内存回复客户端，不向实时游戏发出请求。

## REWARDS-03：旧全流程验证器的目录断言过时

优先级低，源码与目录元数据探针确认。[verify_rewards.py](../../tests/game/verifiers/verify_rewards.py) 显式开启 screenshots 后仍 assert len(list_tools)==43，当前目录为 43 个玩法工具、加截图后 44。legacy-catalog-probe.json 保存核对结果。旧入口未作为当前有效验收运行，不能据新核验器通过宣称原全流程脚本通过。

持续维护指南需要说明该限制并指向新的奖励详情核验；后续修复建议改为当前目录发现，保留既有领取顺序、互斥、嵌套和前进断言。旧脚本的其他分支尚未重新核对，不凭目录修正保证全部旧断言可用。

## 重构范围与验证

既有 RewardInspection 已集中可浏览行和 Ready，无需拆分整个奖励流程。建议将只读前置诊断与动作分支分清，并在现有 Python 详情入口补上下文一致性；summary／筛选应在完整校验后裁剪，沿用当前稳定奖励 id 和空值规则。

- python.log：test_rewards、test_gui_suite、test_session_policy、test_response_pipeline 共 46 项通过，2.122 秒。
- [专项验证器](../../tests/game/verifiers/verify_reward_inspection_review.py)与[GUI 清单](../../tests/game/data/gui_suite_reward_inspection_review.json)：七种典型场景全部通过，184.191 秒，一个自有游戏进程 127984 已退出，共 70 次真实 MCP 调用。
- [9 份真实返回](2026-11-05-inspect-rewards-examples/README.md)逐对象核对原始 structuredContent，保留 full 的 null 及 default 对照；成功结果没有 available_actions，符合已确认的详情工具职责。
- 没有生产代码修改，不重跑完整 Python 或 C# 构建。card_removal、未知自定义奖励、多人与所有遗物组合未单独游戏验证。

## 持续维护文档冲突

rewards.md 原先将固定旧工具数量的 verify_rewards.py 列作可直接使用的验证入口。已按实际实现注明旧入口会在当前目录断言失败，改为列出已通过的奖励详情专项套件；没有借此宣称旧全流程断言都已验证。差异及处理记录在 `.tmp/2026-11-05-inspect-rewards/documentation-conflict-report.md`。

样本来源与文件哈希、七例报告、46 项日志、185 个相对链接及游戏进程退出均已校验；verification.json 保存结果。未修改生产源码，工具清单仍为 22/44，等待用户确认三项修复及候选参数。
