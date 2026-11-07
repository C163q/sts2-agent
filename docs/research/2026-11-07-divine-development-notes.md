# divine 开发核验依据

> 当前状态：源码、26项相关Python检查及12类GUI现状核验完成，十七份实际JSON已交付；两项修复建议待确认，产品代码未修改。用户决策内容见[核验与建议](2026-11-07-divine-review.md)。

## 问题依据

| 编号 | 优先级 | 依据与状态 |
| --- | --- | --- |
| DIVINE-01 | 中 | GameAdapter.Divination的页面／目标／参数拒绝使用FileMailbox.Error，缺少action_submitted:false；工具注册未启用unsubmitted_rejection_unchanged。点击前拒绝后，MCP已有许可被撤销。无棋盘、重复揭开、地图／牌组／奖励／选牌覆盖及已结束均已实测确认，待修复 |
| DIVINE-02 | 中 | 页面与目标拒绝没有public_message；MCP将不同内部原因统一投影为通用illegal_action。无棋盘、已清除格、覆盖与结束无法区分，待修复 |

拒绝发生于UiChanged/ForceClick之前；原始execution表明未交互、未观察到提交，拒绝前后snapshot_id相同。共用恢复协议要求显式未提交保证及对应注册承诺，不能仅凭execution的false恢复许可；可参考已实现的choose_event_option。

## 基线与证据

- 项目f5edfb4，核对日期2026-11-07；Mod0.77.0、MCP0.79.0、schema45。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。
- 目标程序集相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256再次核对为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建及隔离运行时Sts2Agent.dll均为f811e016623541167b17fdbc6edab13fb6cba2f95273be225126b0dea7901c4d；未重新构建、变更版本或正式安装。
- 新证据根`.tmp/2026-11-07-divine-review/`；原生源码缓存`.tmp/2026-10-31-divination/source/`、事件CrystalSphere及`.tmp/2026-10-31-treasure/source/OneOffSynchronizer.cs`。

## 原生操作与信息边界

NCrystalSphereScreen._Ready将格子的MouseReleased与Released接到OnCellClicked；适配器ForceClick走原生Released。OnCellClicked要求次数大于零并等待CrystalSphereMinigame.CellClicked。CellClicked先扣一次次数，再按当前工具ClearCell；大范围使用横、竖、对角及中心格，边缘按范围裁剪。ClearCell对已清除格直接返回，但NCrystalSphereCell.EntityClicked已将这些格子的MouseFilter改为Ignore、FocusMode改为None，因此公开动作要求目标仍为覆盖格，与原生可交互格一致。

所有占用格清除后才RevealItem。普通图案先进入已揭开列表；次数归零触发完成，CompleteMinigame等待0.75秒后调用OneOffSynchronizer.DoLocalCrystalSphereRewards→OfferCrystalSphereRewards→RewardsCmd.OfferCustom，最后Finished。CrystalSphereCurse.RevealItem立即AddCurseToDeck<Doubt>，与正常奖励的发放时机不同。

公开文字棋盘仍由可见贴图、几何与遮罩读取，动作回执不读取隐藏物品位置。GUI中的check_test_divination仅用于挑选覆盖目标，不进入公开样本或工具目录。

## 当前调用链

[GameAdapter.Divination](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)先处理已独立的set_divination_tool；divine严格要求两个0–10的Int32坐标，再核对expected_state。当前页面检查只有Current非空且Ready；目标由Playing和Clickable筛选。UiChanged后ForceClick，ActionObservation等待NonCombatBoundary，TransitionSuccess生成回执。

[DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs)已有共用PageUnavailableReason，但只供只读检查和工具切换使用。divine仍重复使用粗粒度布尔检查。Ready等待揭开任务、0.5秒遮罩动画、物品补间、卡牌预览、资源／遗物动画与动作队列。Clickable检查IsEnabled、IsHidden、MouseFilter和FocusMode。

[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)在Playing时列出divine，没有另核对是否仍有可交互格。正常棋盘最多六次3×3，仍有覆盖格；未据此认定已出现自然流程中的错误列表。建议与揭开检查共用入口，避免后续漂移。

[工具注册](../../src/sts2_mcp/tool_registry.py)为action，要求已有许可，记录事件并返回transition；通过end_turn_details解码和精简动作投影。MCP坐标检查严格拒绝布尔、浮点、字符串、缺项、额外项和越界；本地拒绝发生于会话执行前，保留已有许可。

[GameAdapter.Resources](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs)已将divine接入ActionEventScope、资源、物品与永久牌组日志。NonCombatBoundary允许停在奖励及选择页面；普通可交互奖励页为action_completed，卡牌选择为choice_required，完成占卜为action_completed。纯揭开没有资源或物品取得时，events为空符合当前动作记录职责。

## 验证

相关Python检查为test_divination、test_divination_tool_view和test_event_inspection_presets，共26项通过，0.863秒；python.log。覆盖严格参数、真实stdio、文字／可选图片、覆盖数据边界与视图切换。未运行全套Python、C#或构建。

GUI使用本任务自有隔离实例及实际MCP stdio，验证当前行为；断言包含已知的拒绝后许可缺口，通过不代表问题修复。

| 场景 | 核验内容 |
| --- | --- |
| no_board | 冷调用要求许可；已有许可下无棋盘拒绝；结束回合被要求重新观察 |
| small | 严格本地参数拒绝后仍可揭开；full/default；原始非法坐标及过期令牌拒绝 |
| big | 中央3×3与左边缘裁剪，逐格比较前后覆盖范围及次数 |
| cleared | 重复清除、原生角落空白拒绝；改选合法格仍observation_required |
| covered | 地图与牌组覆盖拒绝，原始令牌不变；关闭页面后恢复 |
| finished | 实际耗尽次数、等待结束；divine拒绝后proceed被要求重新观察 |
| rewards | 实际揭开药水并耗尽次数产生奖励页；拒绝后领取被要求重新观察 |
| selection | 实际揭开卡牌图案、耗尽次数并领取卡牌奖励；选牌中误用拒绝，skip被要求重新观察 |
| curse | 完整揭开立即产生Doubt永久牌组card_added事件 |
| gold | 展示金币奖励前后divine无gold_changed，实际claim_reward才记录 |
| relic | 六次占卜中用四次覆盖4×4箱体，展示奖励前后divine无relic_obtained，实际claim_reward才记录 |
| direct | set_divination_tool后直接揭开，再无观察地第二次揭开，两次均成功、共扣两次 |

首批前九类通过；gold检查误将奖励展示预期为立即获得，在空事件断言失败，后续relic尚未执行。核对OneOffSynchronizer与RewardsCmd确认普通奖励仍需领取，补充批次检查展示与领取的各自事件，并完成gold、relic及direct。没有修改产品代码，原失败脚本、报告及证据均保留。

共12类现状核验最终齐备，13次场景尝试中有上述1次审阅断言失败。两批报告为report.json与remaining/report.json，分别260.801336606秒、104.478044410秒；PID20435和21215均已退出，加载DLL均为基线f811e016…c4d。共144次MCP调用、25次直接原生检查，包含失败尝试；运行器创建／重置请求不计。

没有新增真正结算忙碌中途、异常隐藏／禁用格、多人、第三方图案、人工并发切页、超时或全部奖励组合的GUI验证；这些分支仅按源码核对。卡牌选择覆盖由claim_reward触发，没有将其冒充divine直接返回choice_required的实测。公开错误恢复尚未实现。

[十七份完整JSON](2026-11-07-divine-examples/README.md)均取自实际MCP结果，十六份full、一份default；来源行、原始响应路径及SHA-256见manifest。样本只包含公开输出，私有几何与奖励真值留在忽略的测试证据中。verify_delivery.py核对两批报告、进程退出、DLL、样本、连续调用和相对链接，不重新构建。

## 候选实现边界

复用现有PageUnavailableReason，增加揭开页面及目标格的可读拒绝原因，保持Ready独立；available_actions与执行共用。明确点击前拒绝改用RejectedBeforeSubmission，注册unsubmitted_rejection_unchanged:true，沿用公共choose_legal_action恢复。stale_state、已点击、坏响应、取消及未知结果仍清除许可。

无需新增通用恢复机制、棋盘读取器或动作结果字段；实际揭开、扣次数、原生奖励与事件等待保持现有流程。此为待讨论方案，尚未实施。
