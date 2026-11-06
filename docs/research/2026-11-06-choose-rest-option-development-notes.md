# choose_rest_option 开发核验依据

> 当前状态：现状审阅完成，三项问题待讨论定稿；35项相关Python与12类不同GUI场景完成，未修改玩法实现。用户决策内容见[审阅记录](2026-11-06-choose-rest-option-review.md)。

## 基线与证据

- 项目0e059f5；Mod0.72.0、MCP0.74.0、schema41。
- 核对日期2026-11-06；Linux游戏v0.107.1／release59260271，RitsuLib0.6.10。目标程序集为安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，实测SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时DLL均4464221c7fc4b19d15a44cd9c2efdb71a1c1b7db2b78becde562bd2afa131e34；不重建、更新版本或正式安装。
- 原始证据根`.tmp/2026-11-06-choose-rest-option-review/`，使用独立游戏进程、IPC和测试存档。

## 问题依据

| 编号 | 优先级 | 已核实原因与范围 |
| --- | --- | --- |
| REST-ACTION-01 | 中 | GameAdapter.RestSite.cs的参数／合法性拒绝使用普通FileMailbox.Error，未声明action_submitted:false；ToolSpec未启用unsubmitted_rejection_unchanged。GameSession丢弃旧许可，后续要求许可的合法动作被observation_required拦截 |
| REST-ACTION-02 | 中 | 房间、Ready及单人条件合并为同一消息；目标缺失和Clickable失败也合并。两处未设置public_message，外部error_output替换为通用错误；AvailableTools与执行各自组合Ready/Clickable判断 |
| REST-ACTION-03 | 中 | native_tent实际LIFT和KINDLE均返回events:[]，紧接着的full观察分别显示Girya.counter 0→1、Pumpkin Candle.counter 5→10。RunInventoryJournal记录取得／移除／熔化，但未订阅／采样公开计数变化，transition_details也无相应类型 |

本地参数验证在发送前完成，不消耗许可；省略或错误类型option_id、空白及超长ID、额外参数均已由既有测试覆盖。原生入口仍有自己的参数校验和expected_state比较。状态过期不能按未执行拒绝恢复。

## 现行链路

- [tool_registry.py](../../src/sts2_mcp/tool_registry.py)：choose_rest_option是requires_permission的action，records_events及returns_transition为true，reader为end_turn_details；parser复用rest_option_arguments。支持通用default/full。
- [GameAdapter.RestSite.cs](../../src/Sts2Agent/Adapter/GameAdapter.RestSite.cs)：严格单个option_id，核对expected_state，取得当前房间，Ready与单人校验，按原生ID定位按钮并检查Clickable。首次UiChanged之后ForceClick，以当前run引用和NonCombatBoundary等待。
- [RestSiteInspection.cs](../../src/Sts2Agent/Observation/RestSiteInspection.cs)：Ready核对页面暴露、原生队列、说明／选项动画、执行中按钮及完整选项身份。Clickable核对受支持ID、启用状态、_isUnclickable、目标真实可交互与焦点能力。读取已经取消选项视口筛选，动作保留点击边界。
- [GameAdapter.Resources.cs](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs)：动作作用域包含资源／物品／药水与战斗交接记录；并非直接写固定空事件。
- [GameAdapter.Rewards.cs](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs)、[GameAdapter.ActionObservation.cs](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)：遇到可用选择、奖励或人工边界停止；默认25秒，稳定250毫秒并等待相关动作和UI运动。选择边界不会等待仍需用户输入的父任务结束。
- [action_output.py](../../src/sts2_mcp/output/action_output.py)：完整解码和许可判断后投影actions_only，并保留transition。无此工具专用的顶层执行结果字段。

## 原生流程

核对同一目标程序集的既有定点反编译缓存`.tmp/2026-10-31-rest-site/source/`：

- NRestSiteButton.OnRelease/SelectOption：实际按钮释放调用原生ChooseLocalOption；设置_executingOption，禁用所有选项，await同步器；成功才调用AfterSelectingOption，取消则恢复选项。
- RestSiteSynchronizer.ChooseOption：await OnSelect；false不消耗；成功后按Hook.ShouldDisableRemainingRestSiteOptions清空全部或只移除当前选项。原生索引由当前Option对象取得，不使用外部数组位置。
- SmithRestSiteOption与CookRestSiteOption：原生CardSelectorPrefs允许取消并要求手动确认；空结果false。Smith确认升级并执行后续Hook；Cook确认移除两张，再增加最大生命9。
- HealRestSiteOption：原生恢复后执行Hook及OfferCustom，允许追加奖励；不能由后续奖励跳过撤销已发生的恢复。
- LiftRestSiteOption直接增加Girya.TimesLifted；KindleRestSiteOption调用PumpkinCandle.Rekindle。CloneRestSiteOption复制带Clone附魔的卡并公开预览；HatchRestSiteOption取得Byrdpip。
- RestSiteOption.Generate注明可推进RNG，只用于原生创建火堆；本轮不为读取或验证重新生成选项。MEND需要多人目标流程，当前Supported不包含它；所有第三方ID也不按名称猜测可执行性。

## 验证记录

专用GUI审阅器[verify_choose_rest_option_review.py](../../tests/game/verifiers/verify_choose_rest_option_review.py)记录真实stdio MCP响应、原生错误与执行事实；成功流程复用[verify_rest_site.py](../../tests/game/verifiers/verify_rest_site.py)。[套件](../../tests/game/data/gui_suite_choose_rest_option_review.json)包含五个错误／边界场景及七个原生效果流程。

首轮no_rest通过；basic中脚本错误地预期close_map也需要许可，实际关闭成功。根因为关闭视图和只读工具requires_permission:false；修正脚本的恢复断言后另起新目录验证剩余场景。失败证据保留gui/，不将测试前提错误算作玩法故障。

35项相关Python通过（1.700秒），模块为test_rest_site、test_rest_site_presets、test_gui_suite和test_resource_events。未修改生产源码，不重建或重跑完整Python／C#。

首轮gui耗时42.134秒，14次MCP，no_rest通过、basic因上述脚本前提错误中断；PID15655已退出。修正后gui-remaining的11类场景全部通过，204.812秒、159次MCP、19项原生夹具状态检查及4次过期令牌原生调用，PID16275已退出。合计12类不同场景、173次MCP包含首轮失败现场，不称为单轮全绿。

basic确认本地参数错误可直接继续、地图／牌组覆盖拒绝后可直接关闭、大小写错误／未知ID／已消耗选项拒绝的当前行为。disabled验证SMITH与COOK，selection验证误用后取消被观察前置拦截，rewards验证追加奖励上误用后proceed被拦截。七个原生流程验证单／双牌锻造、烹饪、帐篷、普通挖掘、召唤铃铛和星盘。

锻造打开时events为空；确认逐牌card_upgraded。烹饪确认两项card_removed、max_hp_changed 80→89及hp_changed 30→39。普通挖掘relic_obtained，召唤铃铛另有诅咒card_added到deck，星盘进入选择时只取得遗物，确认才逐项移除／加入。LIFT/KINDLE计数证据为native_tent/flow/evidence.json中相邻公开get_observation的top_bar.relics，与空事件回执共同确认反馈缺口。

[27份完整样本](2026-11-06-choose-rest-option-examples/README.md)为26份full、一份default，附来源行、真实调用参数和哈希。CLONE、HATCH、多人MEND、第三方选项、真实超时／中断仅保留已列源码或未验证边界。

最终校验27项样本哈希及来源一致、244个相对链接、12例套件注册、运行时DLL一致、两个自有进程退出以及清单28/44，结果保存于证据根verification.json。持续维护的火堆指南补充当前拒绝／计数反馈限制，不将待定建议写成已实现行为。

## 建议重构范围

REST-ACTION-01/02可集中火堆动作的页面／目标拒绝原因，再由可用列表、enabled和执行复用；保留独立读取判断，避免以动作Ready阻塞只读详情。点击前使用既有RejectedBeforeSubmission并注册相应ToolSpec规则；UiChanged之后不得发未交互证明。

REST-ACTION-03应另在共用遗物事件记录中设计，避免只按LIFT/KINDLE的名字推断效果。建议候选类型relic_counter_changed，以与现有relic事件一致的身份及before/after表达，数据取实际显示标签。需核对刷新时机、从无计数到有计数、动作期间隐藏／物品取得移除、重复采样及其他动作的同类变化；本轮尚未确认事件字段或实现授权。
