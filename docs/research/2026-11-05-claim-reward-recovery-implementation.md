# claim_reward 拒绝恢复与回执校验实施记录

> 当前状态：实施中，共 1 项，已完成 0 项。三项修复、完整检查、十一类 GUI 与三类回归已通过，正在准备独立审查及交付。暂无阻塞。

最终契约见[审阅定稿](2026-11-05-claim-reward-review.md)，步骤见[实施计划](../superpowers/plans/2026-11-05-claim-reward-recovery.md)，审阅基线的证据见[开发核验](2026-11-05-claim-reward-development-notes.md)。

## 范围与实现

- 领取前的明确拒绝公开固定原因，并使用既有未提交证明保留已有操作许可；旧状态、未知错误、超时和已交互失败沿用重新观察。
- 奖励页判断由查看与领取共用，具体奖励行由统一领取入口解析，enabled 与 available_actions 复用 Claimable；proceed 的原有检查与原生流程保持。
- Reveal 在首次设置滚动目标前回调 BeginInteraction，点击前同样触发；每次请求只调用一次 UiChanged。滚动失败的固定公开说明与未交互拒绝分开。
- 领取成功校验接收原请求，四种 status 均核对 reward_id；完整响应通过后才精简并刷新许可。无请求参数的内部直接校验保持兼容，公开 MCP／文件客户端带请求参数走相同核对。
- 原生领取信号、药水取得监听及选择／嵌套奖励边界保持；监听设置纳入 finally 清理范围。
- 参数保持 reward_id 和 default/full，版本更新至 Mod 0.70.1、MCP 0.72.1，schema 41 不变；正式 Mod 未安装。

## 基线与原生证据

基线 55c02af，分支 fix/claim-reward-recovery。核对日期 2026-11-05；Linux v0.107.1／release 59260271、RitsuLib 0.6.10。游戏安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。

复用审阅记录列出的目标版本反编译源码。滚动扰动另核对 NRewardsScreen._Process／UpdateScrollPosition／_targetDragPos：原生逐帧按目标位置移动奖励容器。测试夹具仅在首次实际滚动后禁用一行，制造页面失去就绪条件；finally 和局间重置恢复按钮、位置并移除补丁。该扰动不是自然游戏复现，不进入公开工具。

证据根为 `.tmp/2026-11-05-claim-reward-recovery/`。

## 测试记录

- python-red.log：5 项新测试执行，10 个子场景按预期失败，分别是两种明确拒绝续接和四种 status × 两预设的 ID 错误接收。
- python-focused.log：领取、动作、共用许可及响应链 53 项通过，1.202 秒。
- gui-red：使用审阅基线 DLL d9475a7e92e93bd2fbb0941167475fb6ad900ffdeece7d23d9d66db9f040a6fd 执行新 basic 断言，未知奖励 ID 的错误仍为笼统原因、recovery:get_observation，按预期失败；自有进程 153538 已退出。原报告与日志保留。
- python-full.log：718 项通过，41.360 秒。
- csharp.log：124 项检查通过；build.log：构建通过，零警告、零错误，4.74 秒。
- 最终构建与隔离运行时 DLL SHA-256 均为 ee2bc3a12d4571d9fdc131644646771664451fe440fc7e3f33d22bb429c0cf8b，prepare.log 记录准备结果；GUI 使用同一产物。
- gui/report.json：十一类 GUI 全部通过，292.726 秒，101 次 MCP；覆盖普通领取、满槽、互斥、嵌套、追回、地图、无奖励、变牌、牌组覆盖、成功滚动及滚动后失败。自有进程 154918 已退出。
- gui-regression/report.json：三类回归全部通过，88.724 秒，38 次 MCP。包含旧 basic 奖励全流程、无奖励页纯读取拒绝后直接结束回合，以及原生测试入口的双模式门控，每个禁用模式 77 项均拒绝。自有进程 155961 已退出。
- 共 139 次真实 MCP；专项另有五次文件原生请求，包含参数拒绝、过期优先和滚动扰动控制。三项问题均修复，成功结果、pending 两种边界和 proceed 回归通过。
- [18 份修复后完整返回](2026-11-05-claim-reward-fixed-examples/README.md)包含 17 份 full 与一份 default；原 15 份审阅样本保持不变。全部 33 份样本哈希与来源已核对，链接及退出证明保存在 verification.json。
- 一次独立审查尚未完成。

## 未验证范围

移除卡牌奖励、未知第三方奖励、多人与所有遗物组合不作穷举。not_obtained 由目标版本分支及 Python 身份校验覆盖，尚未新增添水实际领取样本。
