# 奖励详情预设与筛选交付

> 当前状态：实施中，共 1 项，已完成 0 项。三项修复、summary、reward_ids 和文档表达调整已完成；713 项 Python、124 项 C# 与构建通过，九类 GUI 与 11 份真实返回已完成，20 份新旧样本、351 个相对链接及进程退出校验通过；剩余独立审查和合并，暂无阻塞。

依据：[已确认规格](2026-11-05-inspect-rewards-review.md)、[开发核验](2026-11-05-inspect-rewards-development-notes.md)及[实施计划](../superpowers/plans/2026-11-05-reward-inspection-presets.md)。起点 537f7ae，临时分支 feat/reward-inspection-presets。

## 返回契约

inspect_rewards 的 default/full 保持原有详情范围，summary 使用基础观察的静态奖励格式：状态、标题、id/type/text/enabled/linked_group、proceed。summary 应用 default 空值规则。

get_observation 的 full/default/summary 奖励主体均为静态格式；full 保留普通 null，default/summary 的 rewards 与未筛选 inspect_rewards.summary 一致。静态转换共用 rewards_details，读后的 UI 操作许可沿用原有规则。

reward_ids 作用于当前奖励页的 items。省略／null 取全部，[] 取空；重复 ID 去重，结果维持原生顺序。title 和 proceed 保留整页信息。缺失 ID 按请求顺序合并为 errors:[{code:"reward_ids_not_found",reward_ids:[...]}]，有效行同时返回。

完整原生响应先经过详情和上下文校验，再进行投影。矛盾 screen、损坏的悬停提示或其他必要字段返回 transport_error，并清除操作许可；该检查同样覆盖摘要、空筛选和被筛掉的损坏行。

## 实现入口与整理范围

- [reward_presets.py](../../src/sts2_mcp/output/reward_presets.py)：参数、稳定 ID 筛选与摘要；参数经 native_keys:() 留在 Python，原生请求保持零参数。
- [reward_details.py](../../src/sts2_mcp/output/reward_details.py)：共用 scene_context，要求奖励详情为 scene:rewards、screen:{status:visible}，完整读取 hover_tips。
- [RewardInspection.cs](../../src/Sts2Agent/Observation/RewardInspection.cs)：共用 InspectionUnavailableReason；首先保留原 Ready＋单人判定，然后区分无奖励、地图／卡牌页／选牌覆盖、预览、过渡和动作等待。
- [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 与 [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：读取与工具列表使用同一诊断入口。领取／前进继续沿用各自原生动作分支。
- [verify_rewards.py](../../tests/game/verifiers/verify_rewards.py)：通过当前目录核对真实发现的工具集合，保留 basic 的领取、跳过、卡牌与药水／遗物结果断言。

代码调整集中在奖励查看的共用诊断与校验后投影。文档使用直接的行为和作用域说明，删除了为预防假设误解而连续列举的否定句；保留状态字段含义和实际验证范围。

## 基线与验证证据

当前兼容基线集中在 README。核对 Linux v0.107.1／release 59260271、RitsuLib 0.6.10；游戏程序集 SHA-256 与[审阅基线](2026-11-05-inspect-rewards-development-notes.md)一致。沿用已核对的原生 Reward／NRewardsScreen API、静态可浏览行与悬停来源。

私有证据根 `.tmp/2026-11-05-reward-inspection-presets/`：

- python-red.log：7 项新回归，31 个子用例按预期失败，涵盖新增参数和旧的上下文保护缺口。
- python-focused.log：53 项通过，2.148 秒。
- python-full.log：713 项中一项冻结基线覆盖清单失败，因为新增 summary 尚未加入独立覆盖定义；冻结 JSON 保留原样，新增 summary 由 test_reward_presets 验证。更新清单后 python-full-corrected.log：713 项通过，39.965 秒。
- build.log：0 警告／错误，6.25 秒；csharp.log：124 项通过。
- 最终构建与隔离运行时 DLL 均为 d9475a7e92e93bd2fbb0941167475fb6ad900ffdeece7d23d9d66db9f040a6fd；Mod 0.70.0、MCP 0.72.0、schema 41。正式 Mod 尚未安装。
- [GUI 清单](../../tests/game/data/gui_suite_reward_inspection_review.json)覆盖旧 basic 全流程、原七种奖励详情及牌组覆盖。核心详情场景逐项对照三种 get_observation、三预设空筛选、null、重复／缺失 ID 和具体拒绝；首批旧流程及七类详情共八例通过；牌组覆盖的拒绝通过，收尾时立即 proceed 因原生淡入尚未结束而失败。原始报告 gui/report.json 保留，251.498 秒，进程 139121 已退出。

牌组关闭触发 NRewardsScreen.AfterOverlayShown 的 0.5 秒淡入；当时 close_card_view 返回的 available_actions 已准确省略奖励操作。测试改为读取实际工具列表，等待 inspect_rewards 可用后继续一次 proceed。仅补跑这一例，gui-deck/report.json 通过，28.639 秒，进程 140396 已退出，使用相同 DLL。九类有效场景分两批完成，共记录 204 次 MCP 调用，包含原失败步骤的保留证据。

旧流程验证器返回后，新的 MCP 会话通过原生选路离开奖励房间，完成夹具父任务，随后进行套件重置。

[11 份新完整返回](2026-11-05-reward-presets-examples/README.md)包括 full/summary、空／部分筛选、缺失 ID、互斥组、基础观察对照与具体拒绝。[原 9 份返回](2026-11-05-inspect-rewards-examples/README.md)保留为审阅基线。

## 验证边界

card_removal、第三方奖励、多人与全部遗物组合沿用审阅时的证据范围；实际游戏验证覆盖上表场景。接口整理以当前奖励页为边界，其他工具的审阅继续由总清单跟踪。

verification.json 核对 713 项 Python、124 项 C#、九类有效 GUI、204 次实际 MCP 调用、20 份样本和 351 个相对链接；两个自有测试进程均已退出。
