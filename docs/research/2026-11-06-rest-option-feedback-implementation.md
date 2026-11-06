# 火堆动作拒绝恢复与遗物计数事件

> 当前状态：实现与行为验收完成，共1项，已完成0项；正在准备提交及最终独立审阅，剩余审阅与合入，无阻塞。

要求见[输出定稿](2026-11-06-choose-rest-option-review.md#输出定稿)，原问题和27份审阅样本固定于[审阅记录](2026-11-06-choose-rest-option-development-notes.md)，步骤见[计划](../superpowers/plans/2026-11-06-rest-option-feedback.md)。

## 实现与职责

- choose_rest_option的明确点击前拒绝使用已有未提交证明，并注册MCP许可恢复；本地参数错误继续保留已有许可。过期、结果不明及交互后失败不按明确未执行处理。
- RestSiteInspection集中页面、动作就绪及目标原因。available_actions、静态选项enabled和实际点击复用判断，详情继续使用独立可读性判断。公开原因区分无房间、覆盖、等待、目标不存在／已消耗、禁用、不支持和不可交互。
- RelicCounterJournal独立负责可见遗物计数，随每次RecordedActions创建／销毁，共用ActionEventScope.Buffer；不把计数职责继续加进RunInventoryJournal。原生NRelicInventoryHolder.RefreshAmount的postfix及GameObservation采样从真实标签取值，不以模型DisplayAmount补齐。
- RelicCounterChanges以模型和显示控件身份维护可空基线，输出relic_counter_changed的relic:{name}及before/after；重复刷新不重复，同帧连续刷新逐项入共享序列。隐藏或失去持有身份则丢弃基线，重新显示／取得／更换控件只建立基线。
- Python完整解码后保留精简回执；新增事件严格限制公开字段、两端类型和值不相等，事件null沿用公共保留规则。Mod0.73.0、MCP0.75.0、schema42；历史schema样本继续兼容。

现行契约见[火堆](../development/rest-site.md)、[期间事件](../development/end-turn.md#事件语义)。生产入口分别为[火堆模块](../../src/Sts2Agent/Observation/RestSiteInspection.cs)、[动作执行](../../src/Sts2Agent/Adapter/GameAdapter.RestSite.cs)、[计数采集](../../src/Sts2Agent/Events/RelicCounterJournal.cs)、[基线状态](../../src/Sts2Agent/Events/RelicCounterChanges.cs)及[外部校验](../../src/sts2_mcp/output/transition_details.py)。

## 基线与原生证据

基线dbfc435；Linux游戏v0.107.1/release59260271，RitsuLib0.6.10，目标安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。证据根`.tmp/2026-11-06-rest-option-feedback/`。

原生调用与火堆生命周期沿用开发核验引用的目标版本源码。计数方法另核对`.tmp/2026-11-04-inspect-relics-review/source/NRelicInventoryHolder.cs`的RefreshAmount/OnDisplayAmountChanged：原生通知同步刷新标签显隐和文本；Girya.TimesLifted与PumpkinCandle.KindleCount的setter发出通知。采集挂钩放在标签刷新之后，避免事件订阅顺序依赖。

核对新取得生命周期时，额外检查`.tmp/2026-11-01-action-stability-audit/source/RelicCmd.cs`及NRelicInventory.cs的Obtain/OnRelicObtained/Add：原生以startsShown:false建立新图标并执行入栏动画，AfterObtained的初始计数不从模型补报；采集以实际可读标签建立基线。取得／移除及同模型重新建控件的全部组合未新增GUI穷举。

## 失败验证与通过结果

- 新增5项Python方法先在旧实现出现1个失败、11个子场景错误：未恢复许可，以及新事件尚不支持而返回transport_error。畸形数据及矛盾未执行证明的反证保持拒绝。C#先以缺少新增类型CS2001失败。
- 旧DLL的no_rest新GUI断言在笼统错误处预期失败：15.264秒、3次MCP，PID26696退出。该场景不能算新实现验收通过。
- 实现后28项相关Python通过（0.670秒）；完整743项Python通过（35.952秒）。C#131项通过。最终构建0警告／0错误，3.18秒；构建与运行时DLL均d9bdebffe0562f9238915475668b8c912a385ca62127d996632b446034c924e9。
- 主GUI13类一次通过，240.381秒、161次MCP、7次已记录原生操作及19次原生夹具状态检查，PID36161退出。覆盖普通火堆、置灰、地图／牌组／选择／奖励覆盖、未知及已消耗选项、单／双牌锻造、烹饪、帐篷、普通挖掘、铃铛及星盘。
- 受保护计数检查共25项：连续刷新、重复、隐藏顶栏／遗物栏／图标、透明、离屏、不可悬停、计数显隐的null对照、未刷新模型值不泄露、实际重画、销毁和下一作用域。80个测试入口在testMode关闭及suite关闭时均拒绝。
- 自然战斗回归通过，84.099秒、46次MCP，PID37571退出。由正常火堆休息、地图旅行、出牌／结束回合完成战斗；获胜play_card的同次事件含Pumpkin Candle 5→4，随后inspect_rewards直接成功。
- 按钮及只读显示回归两类通过，36.271秒、33次MCP、26次原生操作，PID38480退出。不可悬停／离屏HEAL被具体拒绝后直接SMITH及取消，无需先读取；原火堆详情的七种显示／淡出边界保持。

总计15类动作相关场景加1类旧详情显示回归；通过轮次240次MCP，连同旧DLL预期失败共243次MCP、52次已记录原生辅助调用。不把拆开的三组通过测试称为一次套件全绿。每次使用新证据目录，未覆盖旧失败记录；没有重复构建改变最终DLL。

[30份新完整返回](2026-11-06-rest-option-feedback-examples/README.md)为29份full、一份default，带真实调用、来源行与哈希。例：[锻炼](2026-11-06-rest-option-feedback-examples/lift.full.json)、[填火](2026-11-06-rest-option-feedback-examples/kindle.full.json)、[获胜出牌](2026-11-06-rest-option-feedback-examples/combat-victory.full.json)、[无火堆拒绝](2026-11-06-rest-option-feedback-examples/no_rest.full.json)、[直接结束回合](2026-11-06-rest-option-feedback-examples/no_rest_direct_continuation.full.json)。原27份审阅JSON保持原样。

## 验证边界

CLONE、HATCH、多人MEND、第三方选项、真实超时／中途退出和全部遗物组合未新增GUI实测。新取得、移除、显示控件替换及非当前玩家的组合以目标源码、身份筛选和基线单元检查核对，不宣称已穷举。计数事件只表达真实可读标签的变化，不描述悬停正文、内部充能状态或所有视觉特效。

已校验新30份与原27份样本的哈希／来源、378个相对链接、15项动作套件注册、运行时DLL一致及四个自有游戏进程退出，结果见证据根verification.json。未正式安装或推送；独立审阅与合入结果在完成后补齐。
