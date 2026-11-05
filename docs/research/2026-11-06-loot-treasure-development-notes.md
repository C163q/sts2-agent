# loot_treasure 开发核验依据

> 本文保留8753038／46e5fd1的审阅基线。两项问题与保留参数方案已确认并进入[修复实施](2026-11-06-treasure-loot-recovery-implementation.md)；下文原问题、旧样本及断言用于修复前对照。

## 基线与证据

- 项目提交 8753038；Mod 0.71.0、MCP 0.73.0、schema 41。
- 核对日期 2026-11-06；游戏 Linux v0.107.1／release 59260271、RitsuLib 0.6.10。游戏安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建及隔离运行时 DLL 均为 a6bc533839a22224adaa0c3564ddbc5936d8d4d31258647e417f3a4a58fd5b00，沿用已验证产物，无构建、版本更新或正式安装。
- 目标版本本地源码 `.tmp/2026-10-31-treasure/source/` 中 NTreasureRoom.cs、NTreasureRoomRelicCollection.cs、TreasureRoom.cs、RelicCmd.cs、TreasureRoomRelicSynchronizer.cs；项目原始证据根 `.tmp/2026-11-06-loot-treasure-review/`。

## 问题清单

| 编号 | 优先级 | 影响与证据 | 状态 |
| --- | --- | --- | --- |
| LOOT-01 | 中 | 明确点击前拒绝缺少未交互证明，注册未启用对应恢复；已开箱／已领取／覆盖等拒绝后合法动作被 observation_required 拦截 | 实测复现，待讨论修复 |
| LOOT-02 | 中 | 错误分支合并原因，且未设置 public_message；全部映射成 The requested action is unavailable | 实测对照 native_error 确认，待讨论修复 |

## 实现与原生流程

| 职责 | 入口 |
| --- | --- |
| 参数、默认值与动作策略 | [treasure_details.py](../../src/sts2_mcp/output/treasure_details.py)、[tool_registry.py](../../src/sts2_mcp/tool_registry.py) |
| 原生按钮、前置校验、两阶段点击与预算 | [GameAdapter.Treasure.cs](../../src/Sts2Agent/Adapter/GameAdapter.Treasure.cs) 的 TreasureRequest |
| 开箱状态、显示与可点击目标 | [TreasureInspection.cs](../../src/Sts2Agent/Observation/TreasureInspection.cs) |
| 边界等待与可用操作 | [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 的 NonCombatBoundary、[GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs) |
| 许可与公开精简 | [game_session.py](../../src/sts2_mcp/game_session.py)、[action_output.py](../../src/sts2_mcp/output/action_output.py)、[transition_details.py](../../src/sts2_mcp/output/transition_details.py) |

NTreasureRoom.OnChestButtonReleased 启动 OpenChest 并禁用宝箱按钮。OpenChest 依次调用 DoNormalRewards 和 DoExtraRewardsIfNeeded，再初始化集合、入场并设置已开箱；随后等待遗物选择开始／结束，更新 Skip/Proceed 并收起集合。TreasureRoom.DoExtraRewardsIfNeeded 等待本地奖励任务，因此可在宝箱遗物揭示前停在额外奖励页。

原生集合通过 PickRelicLocally 提交选择，AnimateRelicAwards 进行手部动画、创建取得的遗物并运行 RelicCmd.Obtain，然后隐藏单人 holder。适配器调用 ForceClick 复用这套流程，不直接加金币或写背包。

TreasureRequest 先验证参数和原状态，检查 Exposed/Ready，选择 Chest 或 Relic。首次点击前 UiChanged，然后等待 NonCombatBoundary。仅在最初为关闭宝箱、open_only=false、第一次停止为 action_completed、同一宝箱仍可领取时，才执行第二次点击。两阶段共享 25 秒总预算，第二次不会获得新的完整预算。

返回场景、选择、奖励和稳定画面的判断来自完整快照；公开回执投影为 actions_only 加 transition。工具不接收奖励／遗物目标 ID，无需新增类似 claim_reward 的目标 ID 核对；传输层继续核对请求 ID，回执没有独立 loot_result。UI 开箱动画不在当前事件分类中，空箱无资源／物品变化时 events:[] 正常。

## LOOT-01／02：明确拒绝与具体原因

参数拒绝、无房间／被覆盖／未就绪、按钮不可用／已打开还要求 open_only 都使用 FileMailbox.Error，没有 action_submitted:false 或 public_message。loot_treasure 的 ToolSpec 为 action/requires_permission，但 unsubmitted_rejection_unchanged 保持 false；GameSession 清除已有许可，也不会仅凭 execution 的 false 字段推断未执行。

实测 open：首次 open_only:true 成功后，再传 true 返回 illegal_action；execution.ui_interaction_started 为 false，随后合法的普通 loot_treasure 在发送前返回 observation_required。inspect_treasure 刷新后才能领取。empty/basic 的已领取拒绝后 proceed、choice 的覆盖拒绝后 select_card、extra 的覆盖拒绝后 claim_reward 同样复现。

native_error 在页面不可用时仅写 Return to an available single-player treasure room，目标不可用时写 This treasure action is unavailable；公开层均显示笼统错误。需要新建固定原因分类，而非仅将旧字符串公开。

建议用共用前置入口解析当前点击目标及原因，供实际执行和 available_actions 复用。空箱与已领取可统一说明当前没有可领取遗物，未开箱时仍正常开箱，不按内部预生成内容提前拒绝。只在首次 UiChanged/ForceClick 之前返回明确未提交保证；一旦开过箱，即使未执行第二次领取，整个请求也不能声明未交互。过期、超时、未知异常继续清除许可。查看的 Exposed 与动作的 Ready 要求不同，proceed 的语义不在这里扩大修改。

## 已核验的正常边界

- basic：同一请求记录 gold_changed 和 relic_obtained，界面停在宝箱房。
- open：只开箱记录金币；后续领取只有遗物事件，没有重复金币。
- empty：白银熔炉空箱 action_completed/complete:true，events:[]，金币与遗物持有物不变。
- extra：既有夹具向原生 RewardsSet 添加 7 金币奖励，第一次停在 rewards、无 relic_obtained；奖励处理完成后仍展示 Anchor，持有物未增加，证明没有残留自动领取；显式再次调用后才取得。
- nested：获得 Calling Bell、预览 Curse of the Bell 入牌组后停在奖励页，complete 指输入边界。
- choice：获得 Astrolabe 后停在 deck_transform，后续由既有选择工具完成。
- map_pending：已有测试设施延迟 AfterObtained，打开地图后再加 7 金币；返回时 delayed_done 为 true、obtaining 为 false，事件包含这次可见金币变化。它是人工延迟场景，不代表自然遗物会这样打开地图。
- display：已有设施注入 disabled/offscreen/hidden，动作均在点击前拒绝，恢复后正常领取；不作为自然游玩复现。

## 参数及提示词建议

保留 open_only 默认 false 和 default/full。回执已经精简，不新增 summary 或筛选。LOOT_SCHEMA 的 false also takes the relic 可以明确为默认尝试开箱并领取、遇输入边界返回；主工具说明已有后续另行处理的提示。

## 验证与限制

- python.log：test_treasure、test_action_observations、test_session_policy、test_gui_suite、test_default_presets 共 67 项通过，3.311 秒。
- [验证器](../../tests/game/verifiers/verify_loot_treasure_review.py)与[十场景套件](../../tests/game/data/gui_suite_loot_treasure_review.json)：全部通过，212.604 秒，134 次真实 MCP 与 19 次文件原生辅助请求；自有进程 182425 已退出。
- [17 份完整返回](2026-11-06-loot-treasure-examples/README.md)包含 16 份 full、一份 default，逐对象对照实际 structuredContent，无图片。验证器保留审阅基线的拒绝与恢复断言，实施修复时须同步。
- 无生产代码修改，不重跑构建、完整 Python 或 C#。真实超时、对局中途退出、多人、教程、藏宝图及全部遗物组合未新增实测，相关保护只核对源码与既有共用测试。

17 项样本来源／哈希、218 个相对链接、运行时产物一致性及进程退出已校验，结果保存在证据根 verification.json。参数注释歧义另记 documentation-conflict-report.md；当前指南已明确真实拒绝限制，未把说明更新当作行为修复。工具清单保持25/44，待用户讨论。
