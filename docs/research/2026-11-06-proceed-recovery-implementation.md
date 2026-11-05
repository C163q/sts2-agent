# proceed 统一前进入口与拒绝恢复

> 当前状态：实施与验收完成，共1项，已完成1项；729项Python、124项C#、16类普通GUI及两个独立终章流程通过。最终独立审阅通过（Critical0、Important0、Minor1），修复7ca98a9及审阅记录e02e7c8已合入main，无剩余必修项或阻塞。

需求与修复前证据见[审阅](2026-11-06-proceed-review.md)及[开发依据](2026-11-06-proceed-development-notes.md)，执行步骤见[计划](../superpowers/plans/2026-11-06-proceed-recovery.md)。

## 行为与范围

- 奖励、宝箱、火堆、商店、事件、先古之民、占卜和建筑师的前进共用一个目标和原因判断，执行与可用工具列表一致。
- 明确点击前拒绝保留已有许可，并说明应关闭页面、完成选项／对白或使用结算工具。拒绝后可直接继续合法动作；状态过期、已交互、超时与未知结果保持重新观察要求。
- 原生按钮和等待行为保留，包括子奖励返回、父事件恢复、打开地图、换幕及建筑师run_won。零操作参数、default/full和精简回执保持现状。
- 旧终章脚本改为验证终态没有玩法动作，并继续检查没有连续玩法许可；允许当前只读查看工具。

## 实现与验证

基线a8b85aa，Mod0.71.2、MCP0.73.2、schema41。游戏Linux v0.107.1/release59260271，RitsuLib0.6.10；目标程序集data_sts2_linuxbsd_x86_64/sts2.dll已重新核对SHA-256为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03；原生流程依据见开发核验。

[GameAdapter.Proceed.cs](../../src/Sts2Agent/Adapter/GameAdapter.Proceed.cs)承担统一目标判断和执行；旧八个处理器的proceed分支移除，其他动作保留自己的实现。before快照校验先于目标判断；第一次ForceClick前才生成明确未提交证明。事件保留CombatJournalScope停止原因与日志，先古之民／宝箱保留上下文身份校验。

证据根为`.tmp/2026-11-06-proceed-recovery/`。Python新增许可矩阵先失败，旧DLL的GUI也先复现笼统提示和许可丢失；修复后58项相关Python及729项完整Python（38.118秒）、124项C#通过。首次构建暴露拆分后两处变量作用域冲突，修正命名后构建0警告／0错误（2.59秒），首轮日志保留。构建与隔离运行时DLL同为c290e150238ebb92e072a5cdc6aa210778237d2c76deb0a96c6c69a9fe64ca40。

GUI首轮combat通过；reward_skip在proceed调用前被测试断言阻断，原因为inspect_map不返回available_actions，而测试误读开地图前的旧列表。已改为原生get_state核对当前列表，不刷新MCP许可；余下15例单独续跑并全部通过（401.008秒，PID210645已退出）。该失败属于验证器问题，未列为产品故障；不能称为单轮16例全绿。

独立建筑师验证通过（64.026秒，14次MCP、2次原生辅助调用）；正常离开Boss奖励、对白中拒绝后直接继续对白、最终run_won、终态没有连续玩法许可及结算误用后直接继续均已覆盖。

旧verify_run_ending.py的victory_unlock完整流程通过（156.071秒，127次MCP），覆盖胜利首屏、分数、历史、教程、时间线、epoch、解锁和返回主菜单。保留其余检查，终态断言仅改为排除玩法动作，并继续实际验证没有连续玩法许可。

包括旧DLL预期失败和新验证器前提失败在内，总计288次MCP、16次原生辅助调用；分轮结果和所有自有进程退出由verification.json核对，不将失败轮次包装为全绿。两个独立终章实例均使用全新进度，finally清理拥有的游戏与验证器进程组。

[26份修复后的完整返回](2026-11-06-proceed-fixed-examples/README.md)包括25份full与一份default；原23份审阅返回保留旧基线。可对照[商店明确拒绝](2026-11-06-proceed-fixed-examples/shop-rejected.full.json)、[直接关闭商品页](2026-11-06-proceed-fixed-examples/shop-recovered.full.json)和[建筑师终局](2026-11-06-proceed-fixed-examples/run-won.full.json)。

## 验证边界

双Boss、教程、真实超时、对局中途退出、多人和全部事件／遗物组合未穷举。奖励proceed触发父事件Resume分支继续以目标版本源码为依据；Battleworn Dummy样本在战斗结束时已经恢复父事件，后续proceed只验证离开事件。

持续维护文档曾要求所有proceed拒绝后重新观察，现随实现改为明确点击前拒绝可恢复；旧终章断言的临时限制已在完整实测通过后移除，明确现行脚本检查和验证入口。文档差异处理保存在证据根documentation-conflict-report.md。

## 最终审阅

独立只读审阅范围a8b85aa..7ca98a9，Critical0、Important0、Minor1，可合入。未重新构建或运行游戏，使用已有证据核对。

保留的小问题：[原生参数检查](../../src/Sts2Agent/Adapter/RequestDispatcher.cs#L39)会在proceed同时携带过期令牌和非空参数时先返回invalid_request及未提交证明。正常MCP在本地拦截非法参数，后续合法动作仍须通过快照校验，因此不阻断当前玩法修复；该边界暂未调整，未新增用户TODO。

审阅提出的验证边界维持上节范围：多人、第三方Mod、真实超时及全部组合没有扩展实测，可能仍存在未见变体问题；奖励前进触发父事件Resume保留原生流程与源码依据，该特定恢复分支仍有游戏内验证盲区。
