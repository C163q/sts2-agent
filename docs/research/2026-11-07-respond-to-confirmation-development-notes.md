# respond_to_confirmation 开发核验依据

> 当前状态：源码、12项相关Python检查及六类GUI现状核验完成，十二份JSON已交付；两项产品修复建议待确认，过时文档已同步现状，产品代码未修改。用户决策内容见[核验与建议](2026-11-07-respond-to-confirmation-review.md)。

## 问题依据

| 编号 | 优先级 | 依据与状态 |
| --- | --- | --- |
| CONFIRMATION-01 | 中 | ConfirmationRequest的参数／页面／按钮拒绝均使用FileMailbox.Error，没有action_submitted:false，注册未启用unsubmitted_rejection_unchanged。无确认框拒绝未交互、前后令牌一致，后续end_turn仍observation_required；待修复 |
| CONFIRMATION-02 | 中 | 两类illegal_action未设public_message，MCP投影为统一错误。没有受支持弹窗、尚未就绪与按钮不可用无法区分；待修复 |
| CONFIRMATION-03 | 低；文档／测试 | events.md及旧verify_confirmation.py将确认终态动作列表断言为空；当前确认实际进入run_result，保留inspect_ui／inspect_run_result／inspect_potions／inspect_relics。文档已同步，旧验证器迁移纳入建议范围 |

共用会话要求明确保证后才保留许可，不能仅依据execution:false推断。拒绝在UiChanged及ForceClick之前，可采用已审阅动作的RejectedBeforeSubmission及对应注册策略。

## 基线与证据

- 项目d4d1cef，核对日期2026-11-07；Mod0.77.1、MCP0.79.1、schema45。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。
- 目标程序集相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256再次核对为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 隔离运行时DLL为754f17436a7ecdaa477b5a8131774c8922f35681842eef6b3d3e1c0709260f8c；没有重建、更新版本或正式安装。
- 证据根`.tmp/2026-11-07-respond-to-confirmation-review/`；原生缓存`.tmp/2026-10-31-events/source/Trial.cs`、NAbandonRunConfirmPopup.cs、RunManager.cs及`.tmp/2026-10-31-confirmation/source/NVerticalPopup.cs`和NPopupYesNoButton.cs。旧实现依据见[原确认框验证](2026-10-31-event-confirmation-validation.md)。

## 原生与当前实现

Trial.Reject第一次拒绝生成DoubleDown选项，附致死警告且允许重复选择。DoubleDown调用NModalContainer.Add(NAbandonRunConfirmPopup.Create(null))，并不直接杀死玩家。弹窗_Ready初始化固定本地化标题／正文及Yes／No；入场透明与位置补间分别0.1／0.3秒。

NVerticalPopup.InitYesButton／InitNoButton将Released先接到原生回调，再接到Close。No回调排队释放弹窗，Close清空模态容器，遮罩另有退出动画。Yes调用RunManager.Abandon；AbandonInternal标记IsAbandoned，GuaranteeKillAllPlayers使用CreatureCmd.Kill(force:true)，并等待原生失败流程。

[EventConfirmation](../../src/Sts2Agent/Actions/EventConfirmation.cs)只观察Trial.DoubleDown新建的弹窗，将Trial实例及IRunState绑定到节点。Current要求来源、当前事件和对局仍一致。Exposed检查单人、无其他覆盖、标题／正文／两按钮标签已显示；Ready另等弹窗与遮罩动画、事件及放弃任务。

Clickable额外检查按钮OnScreen、IsEnabled、MouseFilter。Read.options[].enabled使用Clickable；[available_actions](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)目前只看Ready就列respond_to_confirmation，未检查至少一个按钮可交互。正常原生按钮均启用，尚未发现自然流程中的错误列表；建议集中可操作条件，避免条件漂移。固定弹窗正文及按钮使用OnScreen读取，未实测异常离屏布局。

[ConfirmationRequest](../../src/Sts2Agent/Adapter/GameAdapter.Confirmation.cs)严格校验单个字符串option，再核对expected_state；Current／Ready检查后选Yes／No，检查Clickable再UiChanged／ForceClick。等待时要求同一对局、放弃任务及遮罩结束；confirm另等EventTaskTracker.RunLost，再交给NonCombatBoundary。动作已接入共用事件日志；MCP成功采用精简动作回执，不附整个确认框。

[GameObservation](../../src/Sts2Agent/Observation/GameObservation.cs)包含模态实例代次，旧弹窗取消重开会更换令牌，即使文案一致。[输出校验](../../src/sts2_mcp/output/observation_details.py)要求confirmation属于event、底层场景覆盖且仅提供respond_to_confirmation；未知来源弹窗不输出受支持confirmation字段。

## 文档核对

events.md原写确认后返回空动作列表，旧verify_confirmation.py也有该断言。当前NonCombatBoundary、RunResultInspection与终态动作投影支持结算只读工具；当前DLL实测确认scene:run_result、run_lost／complete:true，公开动作列表保留inspect_ui、inspect_run_result、inspect_potions、inspect_relics。事件指南已同步实际语义，并标明旧验证器尚未迁移。

旧验证器还使用固定IPC及旧完整观察断言，例如要求covered事件含description；当前基础观察采用事件摘要，旧断言不适用。仅按源码核对这些旧断言与新样本的差异，没有运行旧脚本宣称已复现其全部失败。建议在产品修复时迁移并接入自有测试实例；问题记录另存`.tmp/2026-11-07-confirmation-documentation-report.md`。

## 验证

test_event_confirmation与test_event_option_recovery共12项通过，0.617秒；python.log。覆盖确认框形状、严格参数、本地拒绝许可、取消重开、终态撤销及真实stdio。未运行全套Python、C#或构建。

GUI使用自有隔离进程与实际MCP stdio。首批no_dialog确认点击前拒绝后仍要求观察；cancel准备在初始事件options中直接读取lethal_warning失败。get_observation.full复用事件summary，省略false，脚本误将此字段当作必填；只在新脚本中改为可选读取，原失败及证据保留，剩余五类在新目录核验通过。

原生私有入口仅用于取消／重建弹窗及核对放弃标记、失败信号和HP，不进入公开工具或样本。确认放弃只作用于隔离测试局。

六类最终完成，共七次场景尝试，其中一次为脚本读取可省略字段的错误。首批48.684090651秒，no_dialog通过、cancel准备失败；补充五类一次通过，110.901285244秒。PID27795、28081均已退出，两批均加载基线754f1743…0f8c；原失败、脚本与报告保留。

两批共54次MCP调用、23次直接原生检查，包含失败尝试，运行器创建／重置请求不计。交付检查核对报告、进程退出、DLL、十二份JSON的来源／参数／哈希及179个相对链接；未重复构建或运行全套测试。

| 场景 | 核验结果 |
| --- | --- |
| no_dialog | 首次无许可拒绝；观察后误用无确认框，未交互、前后令牌一致；随后end_turn仍要求观察 |
| cancel | 原生弹窗标题／正文／两按钮可读；本地及原始非法option拒绝；取消不改资源／事件RNG；取消后重复响应拒绝，合法重开仍要求观察；重新观察后可重开并default取消 |
| replacement | 私有入口取消并重建相同文案的新弹窗，令牌改变；旧原始请求及MCP请求均stale_state；重新观察后取消成功 |
| unowned | 相同弹窗类型从Trial.DoubleDown以外创建，confirmation为空、screen为covered/confirmation；响应拒绝，没有放弃对局 |
| covered | 地图、牌组页打开期间误用，均明确没有交互但只返回通用错误；关闭页仍可直接调用 |
| confirm | 实际Yes放弃该测试局，原生IsAbandoned／RunLost为true、任务结束且HP0；返回run_lost并保留结算只读工具，旧玩法许可撤销 |

[十二份实际JSON](2026-11-07-respond-to-confirmation-examples/README.md)为十一份full、一份default，逐份保存MCP返回、参数、来源行及SHA-256。地图／牌组误用等相同结构不重复导出。没有新增结算忙碌中途、异常按钮禁用／隐藏／离屏、多人或第三方弹窗的GUI验证；这些状态只核对当前检查源码。

## 候选实现边界

EventConfirmation集中动作与单个按钮的可读拒绝原因，Ready保持独立；执行、options.enabled和available_actions共用。区别没有受支持弹窗、未知来源、覆盖、动画／事件／放弃等待及按钮不可用；保持原生来源绑定和实例代次。

点击前明确拒绝采用已有未提交保证及MCP恢复策略；过期、已交互、未知／坏响应保持撤销。沿用原生No／Yes回调、退出与放弃等待、事件日志和精简回执，不新增通用弹窗框架。
