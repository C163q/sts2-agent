# claim_reward 开发核验依据

> 本文保留 43ea846／55c02af 的审阅基线与修复前证据。三项问题已确认并进入[修复实施](2026-11-05-claim-reward-recovery-implementation.md)；下文问题状态与旧返回用于基线对照，现行契约见[奖励指南](../development/rewards.md)。

## 基线与证据

- 项目提交 43ea846，Mod 0.70.0、MCP 0.72.0、schema 41。
- 核对日期 2026-11-05；Linux v0.107.1／release 59260271、RitsuLib 0.6.10。目标程序集安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时 DLL 均为 d9475a7e92e93bd2fbb0941167475fb6ad900ffdeece7d23d9d66db9f040a6fd，沿用已验证产物；无 C# 或 MCP 生产变更，无重新构建、正式安装。
- 原始证据根 `.tmp/2026-11-05-claim-reward-review/`；夹具准备隔离局面，后续领取、选择、覆盖及旅行由真实 stdio MCP 执行。
- 目标版本本地反编译源码位于 `.tmp/2026-10-31-rewards/source/`：Nodes.Rewards.NRewardButton.cs、Nodes.Screens.NRewardsScreen.cs、Rewards.Reward.cs、Rewards.PotionReward.cs、Rewards.CardReward.cs、Rewards.RelicReward.cs、Rewards.SpecialCardReward.cs。

## 问题清单

| 编号 | 优先级 | 影响与证据 | 状态 |
| --- | --- | --- | --- |
| CLAIM-01 | 中 | 明确点击／滚动前的 illegal_action 缺少未交互证明，已有许可丢失；重复 ID、错误场景和覆盖页实测 | 待确认修复 |
| CLAIM-02 | 中 | FileMailbox.Error 未公开具体原因，统一映射笼统错误；实测响应对照 native_error | 待确认修复 |
| CLAIM-03 | 中 | claim_reward_details 未核对结果 ID 与请求 ID；合成损坏响应通过完整 GameTools 链并刷新许可 | 待确认修复 |

## 实现职责与原生流程

| 职责 | 入口 |
| --- | --- |
| 参数、许可和工具描述 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)、[reward_details.py](../../src/sts2_mcp/output/reward_details.py) |
| 读取当前奖励、稳定 ID、定位可点击行 | [RewardInspection.cs](../../src/Sts2Agent/Observation/RewardInspection.cs) |
| 领取／前进、等待边界和结果 | [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 的 RewardRequest／NonCombatBoundary |
| 互斥奖励信号兼容 | [RewardCompatibility.cs](../../src/Sts2Agent/Actions/RewardCompatibility.cs) |
| 许可续接及拒绝恢复 | [game_session.py](../../src/sts2_mcp/game_session.py) |
| 完整成功校验、领取回执与动作精简 | [response_pipeline.py](../../src/sts2_mcp/output/response_pipeline.py)、[action_details.py](../../src/sts2_mcp/output/action_details.py)、[action_output.py](../../src/sts2_mcp/output/action_output.py) |

原生 NRewardButton.OnRelease 启动 GetReward，先 Disable，再等待 RewardsSetSynchronizer.SelectLocalReward。成功发 RewardClaimed，失败重新 Enable 并发 RewardSkipped。NRewardsScreen 收集成功信号后移除对应行；互斥组经既有 RewardCompatibility 适配目标版本信号参数，保持原生收尾。

RewardRequest 不直接增金币或改背包：校验参数、快照、页面和按钮，调用 Reveal 后 ForceClick；监听上述完成信号和目标药水的 PotionProcured，再由 NonCombatBoundary 等待后续输入边界。pending 表示尚未收到 claimed/skipped 信号；打开嵌套页或选牌可以先于原领取任务结束。

PotionReward.OnSelect 仅在 TooFull 时返回 false。其他获取失败仍返回 true，因此适配层用目标药水的 PotionProcured 区分 claimed 与 not_obtained。SpecialCardReward.OnSelect 使用 CardPileCmd.Add(Deck) 并显示原生飞牌预览。领取动作既有事件记录负责金币、药水、遗物、卡牌及永久升级等变化。

## CLAIM-01／02：拒绝与交互开始位置

claim_reward spec 为 action/requires_permission，但未启用 unsubmitted_rejection_unchanged。RewardRequest 对无奖励页、未 Ready、非单人、找不到 ID、按钮禁用或不支持类型返回 FileMailbox.Error；没有 action_submitted:false 或 public_message。GameSession 先清除许可，无法把这些错误判为有保证的未交互拒绝；error_output 也不会公开普通诊断字符串。

可复现路径：inspect_rewards → claim_reward(有效金币 ID) → claim_reward(相同 ID) → claim_reward(有效药水 ID)。重复 ID 被拒绝时 execution.ui_interaction_started 和 action_submission_observed 均为 false，但这两个 false 按既定协议只表示未记录正面证据；下次调用仍返回 observation_required。错误场景、地图、牌组、选牌覆盖同样核对。

建议为领取提供共用前置原因与明确未交互拒绝，更新 registry 恢复声明，并保持 stale_state、超时、未知错误的既有保守处理。与 inspect_rewards 共用页面状态判断时，提示应使用领取语义；proceed 共用 RewardRequest，重构须避免改变未审阅的流程推进行为。

Reveal 可先写 _targetDragPos 并逐帧滚动，现有 UiChanged 直到 ForceClick 前才调用。修复前置拒绝时，需要同时把第一次滚动划为交互开始，防止将滚动后失败错误标记为未交互。该边界来自源码；此专项未人为注入滚动后失败。

## CLAIM-03：回执与请求的 ID 一致性

claim_reward_details 验证 reward_result 的字段、ID 范围与四种 status，但未读取 native_arguments。reader 未声明 reader_argument:request，因此请求中的 reward_id 不参与成功校验。

`outcome-id-probe.json` 复制真实成功原始响应，只将 reward_result.reward_id 改为另一个合法整数。decode_success 和完整 GameTools.claim_reward 均接受，且保存响应快照作为后续许可。探针使用内存回复客户端，无实时游戏请求；不能据此推断正常游戏曾返回错误 ID。

建议让领取结果校验接收原请求，并在完整校验阶段核对 ID。错误响应应在精简与许可刷新前变为 transport_error。现有 purchase 等工具的类似契约不在此专项扩大实现范围。

## 验证与未覆盖范围

- python.log：test_rewards、test_action_observations、test_default_presets、test_gui_suite 共 55 项通过，2.966 秒。
- [图形验证器](../../tests/game/verifiers/verify_claim_reward_review.py)与[八场景清单](../../tests/game/data/gui_suite_claim_reward_review.json)全部通过，229.172 秒，88 次真实 MCP 调用；自有进程 148828 已退出。basic、full、linked、nested、returned、covered、no_rewards、transform 覆盖上述正常结果与前两项问题。该验证器断言审阅基线的拒绝后许可丢失，实施修复时须同步新预期。
- [15 份完整返回](2026-11-05-claim-reward-examples/README.md)逐对象对照 evidence.json 中的 structuredContent，14 份 full、1 份 default，均无图片；manifest 保存调用与哈希。
- 样本 15 项哈希、276 个相对链接、构建／测试运行时 DLL 一致性及自有进程退出均已校验，结果保存于证据根 verification.json。无生产代码改动，未重跑完整 Python 或 C# 构建。
- not_obtained 核对目标版本 PotionReward 分支和现有 Python 回执保留检查，未新增添水 GUI 样本。
- 移除卡牌奖励、未知第三方奖励、多人及所有遗物组合未逐一实测；滚动后异常只检查源码边界。

## 文档现状同步

[MCP 接入指南](../development/mcp.md#接入-codex)仍写“默认 42 项”，而当前目录是 43 个玩法工具、可选截图另加一项。已删除该过时重复数量，指向指南前部的工具范围；这是文档过时，不涉及工具行为修改。

奖励指南同步已核实的明确拒绝仍需观察及未核对请求 ID 两项限制，并链接专项证据。工具清单仍为 23/44，claim_reward 处于设计讨论，等待用户确认后实施。
