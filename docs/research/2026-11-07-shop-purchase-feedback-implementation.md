# 商店购买反馈、恢复与选择稳定性实施记录

> 当前状态：实现和全部约定验收完成，等待独立审阅与合入。暂无阻塞。

依据[输出定稿](2026-11-07-buy-item-review.md#输出定稿)及[计划](../superpowers/plans/2026-11-07-shop-purchase-feedback.md)。旧问题及目标原生证据见[审阅开发依据](2026-11-07-buy-item-development-notes.md)。

## 实现

- PurchaseUnavailableReason集中购买页面／活动检查，ItemUnavailableReason集中已用删牌、库存、交互、价格及金币原因；执行、商品enabled、available_actions复用。Find只定位当前ID与payload，操作合法性随后单独核对，读取仍保留显示在视口外的条目。
- 明确交互前拒绝公开原因及action_submitted:false，注册现有MCP恢复协议；旧许可可用于直接纠正或其他合法动作，首次无许可／stale／已交互／未知结果仍不恢复。
- 新GameAdapter.Purchase.cs集中同一个Entry的绑定／解绑及原生OnSelected等待。PurchaseOutcome按已知事件、完成的Task和受支持输入决定结果：已知事件优先，成功完成无事件为canceled，未完成且等待输入为pending，故障／取消Task不编造结果。原生Task取消中断等待。
- purchase_details在完整状态校验后核对结果ID非负Int32且与请求相同，再精简及续接；pending要求受支持的可见选择或奖励边界。schema44的action_completed／choice_required应有结果，超时／中断／人工及胜负终局等其他购买状态未知边界可省略，旧schema保留省略兼容。
- RunUi.GoldMotionPending复用于常规资源等待及choice_required的独立等待标志；ActionSettling在该计数仍运行时重置稳定区间，结束后再等250毫秒。原有一般视觉motion仍可在选择边界暂停，不等待需要玩家输入的整个父购买／卡牌任务。
- 参数仍为item_id和default/full，工具说明简化；后续选择／奖励动作继续自己的回执／事件，不跨调用携带购买终态。没有新增游戏测试入口，双重门控保持81。

关键代码：[购买检查](../../src/Sts2Agent/Observation/ShopInspection.cs)、[购买过程](../../src/Sts2Agent/Adapter/GameAdapter.Purchase.cs)、[结果分类](../../src/Sts2Agent/Actions/PurchaseOutcome.cs)、[稳定等待](../../src/Sts2Agent/Actions/ActionSettling.cs)、[金币检测](../../src/Sts2Agent/Observation/RunUi.cs)、[结果解码](../../src/sts2_mcp/output/action_details.py)和[注册](../../src/sts2_mcp/tool_registry.py)。

## 基线与证据

- 任务基线d8f4a80；Mod0.74.2→0.75.0、MCP0.76.2→0.77.0，schema43→44。
- Linux游戏v0.107.1/release59260271、RitsuLib0.6.10；目标程序集及原生源码SHA-256、位置沿用审阅开发依据。
- 原始证据根`.tmp/2026-11-07-shop-purchase-feedback/`。
- 完整专项／回归候选DLL为8ad4af3299464e8d78bf9a6adb3b9c03cf817a9ef6c6ee59d1a0ddf6be609a2c；最后只校对一处新提示的英文单复数，最终构建／隔离运行时DLL为6d3c607f414e71fef8c3b5c9ab0ec556ef0e7b74404a44fda5191e87de8007a1。源码差异仅该提示常量，copyedit.diff保留对照，未正式安装或推送。

## 验证

1. 新Python八项RED，18个子用例失败，0.177秒；C#新API尚未存在时CS2001编译RED。旧DLL的gui-red在无商店恢复断言失败，gui-gold-red先在已知关闭状态拒绝失败，未到金币检查；gui-gold-isolated-red隔离时序后准确复现同次显示2099而应为1999。PID82580／83713／84980均已退出，三份报告保留，使用旧DLL da3c5d00ce7c97c1eeead86622a9c4ebd6aff922ee7756347aebb8569ad812fb。
2. 针对性45项Python通过，2.099秒；首次全量767项通过，38.777秒；新增时序测试模式后窄范围20项通过，1.198秒。139项C#通过；候选构建6.17秒，文案校对后的最终构建4.19秒，两次均零警告／错误。
3. 十类购买专项一次通过，283.260477222秒，PID85453已退出；没有stale容忍、显式恢复重试或夹具金币等待。变牌直接根据同次原生响应检查显示金币等于调用前可见金币减价格，然后立即观察／选牌。删牌／子奖励／变牌返回pending，后续确认／取消不携带购买终态；已售／已替换／已用、价格、覆盖和金币拒绝均可直接续接。
4. 十类回归全部通过，305.527590828秒，PID86151已退出；包括3次直接变牌时序、开关商店、普通／送货员／删牌、16组详情显示与双81入口门控、战斗暂停父任务选择。
5. 专项145次MCP／50条原生操作，回归249次MCP／69条原生操作、8次夹具检查及3条建局记录；绿色共394次MCP／119条原生操作。三次RED分别3／4／6次MCP及1／1／0条原生操作，保留失败报告，不合称全绿。
6. 九例隔离响应探针保留三个正确ID结果及许可，六个错配／越界结果均transport_error且许可为空；结果位于outcome-probe-isolated.json，不连接游戏。原探针目录没有改写。

入口：[Python协议](../../tests/python/test_purchase_feedback.py)、[C#分类与等待](../../tests/csharp/Sts2Agent.Checks/PurchaseFeedbackChecks.cs)、[十类GUI](../../tests/game/data/gui_suite_buy_item_review.json)及[验证器](../../tests/game/verifiers/verify_buy_item_review.py)。

[二十份修复后完整JSON](2026-11-07-shop-purchase-fixed-examples/README.md)附请求、来源行及SHA-256；旧十八份保持原样。新时序检查没有额外读取／等待来掩盖问题，原生响应元数据中的native_gold只用于测试核验，没有增加对LLM返回的字段。

## 边界

多人、第三方商店、全部获取／价格修改组合、真实超时、中途退出及任意人工并发不新增穷举。原生failure_gold／failure_out_of_stock及无选择时canceled的独立终态GUI仍只核对源码，MCP及C#覆盖匹配／错误ID、pending、缺结果、取消／故障和未知边界。pending不是跨调用购买历史；后续操作语义依各自工具，不以编译通过代替原生行为验证。

持续文档同步购买原因／pending／schema语义和共用金币等待；TODO只更新原有两项的处理明细。核对发现原头部覆盖工具数比明细少计两项，现去掉该重复统计，明细已列33个工具，条目仍为8项／3项完成；核销数量仅在工具审阅清单维护。

最终DLL另补跑正常购买及变牌时序两类加载／行为检查，全部通过：67.436906905秒，38次MCP／16条原生操作，PID90407已退出。不把候选DLL的二十类通过记录改称最终DLL全量运行。文案没有改变购买逻辑，C#检查无需重复；Python最终另有终局校验变更，按下一段重新验证。

终局缺省结果补测RED：run_won／run_lost缺少购买结果时旧校验错误给transport_error；改为仅正常action_completed及choice_required强制结果，终局仍保留回执且不授权继续。该变更仅Python，Mod DLL未改，新增协议单测RED两个子用例（0.024秒）→八项协议GREEN（0.176秒），最终全量767项再次通过（39.791秒）；原GUI均使用相同Mod购买逻辑，正常输入校验未放宽。

绿色GUI记录合计432次MCP／135条原生操作，另8次库存夹具检查及3条建局记录；候选／最终DLL分开保留。交付脚本核对38份新旧样本来源／哈希、433条相对链接、全部日志、六个自有PID退出、版本与schema及双81门控，均通过。
