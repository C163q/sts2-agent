# buy_item 开发核验依据

> 当前状态：定稿已实现，当前验收见[实施记录](2026-11-07-shop-purchase-feedback-implementation.md)；以下保留审阅基线。用户决策内容见[审阅与建议](2026-11-07-buy-item-review.md)。

## 基线

- 项目26ad140；Mod0.74.2、MCP0.76.2、schema43。
- 核对日期2026-11-07；Linux游戏v0.107.1/release59260271、RitsuLib0.6.10。
- 目标安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建及隔离运行时Sts2Agent.dll均为da3c5d00ce7c97c1eeead86622a9c4ebd6aff922ee7756347aebb8569ad812fb；不重建、更新版本或正式安装。
- 证据根`.tmp/2026-11-07-buy-item-review/`。

## 问题依据

| 编号 | 优先级 | 核实依据 |
| --- | --- | --- |
| SHOP-BUY-01 | 中 | GameAdapter.Shop.cs的页面／Ready、商品拒绝及原始参数拒绝均没有action_submitted:false；buy_item注册未启用unsubmitted_rejection_unchanged。明确点击前拒绝也清除许可 |
| SHOP-BUY-02 | 中 | 前置拒绝没有public_message，MCP统一替换为illegal_action通用提示。Find／Purchasable将ID、是否显示、价格、金币及交互条件合成bool，不能提供具体原因；ReadItem.enabled、AvailableTools和动作分别组合条件 |
| SHOP-BUY-03 | 中 | purchase_details不接受请求参数；只检查item_id非负，没有Int32上限，也没有与请求item_id相等检查。受控GameTools用0／999／2147483648及success／failure_space／canceled组合共九次响应，均接受并取得shop-2许可；其中六次ID错误。原生适配器当前实际使用请求ID，此证据不是游戏误购 |
| SHOP-BUY-04 | 中 | 变牌Astrolabe购买返回choice_required后，inspect_selection→select_card得到stale_state。gui与remaining两个独立进程均复现；remaining记录buy前后快照仅top_bar变化，金币2099→2044且仍在变化，立即重读后再次stale。ActionSettling.Sample仅在player_ready/action_completed/action_canceled/combat_won等待motionPending，choice_required忽略它；NTopBarGold首段0.25秒及150毫秒等待长于250毫秒静态窗口 |

对照[claim_reward结果读取](../../src/sts2_mcp/output/action_details.py)已经要求ID范围并在注册中传入request校验一致性。buy_item应在完整响应解码时完成相同校验，精简投影和许可续接必须在其后；不能只验证样例或返回体表面字段。

## 代码及原生来源

- [GameAdapter.Shop.cs](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)：参数校验、stale、页面与单品检查后绑定Entry.PurchaseCompleted／Failed；UiChanged后反射原生NMerchantSlot.OnSelected。边界允许选牌或奖励返回，finally解绑，未结束的局部outcome不跨调用保留。已成功完成但没有结果时标canceled。
- [ShopInspection.cs](../../src/Sts2Agent/Observation/ShopInspection.cs)：Find依据当前slot、payload和ID，并要求点击范围；Purchasable检查库存、原生Hitbox、可读价格及EnoughGold。静态读取仍保留显示在视口外的条目；不把点击检查和静态列表裁剪混为一类问题。
- [ShopTransactions](../../src/Sts2Agent/Actions/ShopTransactions.cs)：跟踪原生购买Task，阻止未完成购买被额外操作打断，记录run并清理已完成／更换run的任务；不跟踪某次MCP调用的结果ID或终态。
- [工具注册](../../src/sts2_mcp/tool_registry.py)、[购买结果读取](../../src/sts2_mcp/output/action_details.py)、[解码分派](../../src/sts2_mcp/output/inspection_details.py)：buy_item读取器未传request，购买结果字段可省略，当前没有pending枚举。

原生缓存证据位于`.tmp/2026-10-31-shop/source/`：MerchantEntry、MerchantCardEntry、MerchantRelicEntry、MerchantPotionEntry、MerchantCardRemovalEntry及各NMerchant槽位。目标版本PurchaseStatus新核对于证据根source/PurchaseStatus.cs，未纳入Git。

- NMerchantSlot.OnSelected先ClearHoverTip，再awaitOnTryPurchase，结尾可重新创建悬停。因此已进入原生OnSelected后，即使领取失败，也不能将整次请求当成点击前未交互。
- MerchantEntry.OnTryPurchaseWrapper先核对库存／金币，await获取；成功后清货／送货员补货，awaitAfterItemPurchased，再发PurchaseCompleted。同一Entry复用、payload更换，当前finally解绑引用未见实际错配。
- 卡牌先CardPileCmd.Add，再扣金币；药水先TryToProcure，失败发FailureSpace／Forbidden且不扣钱。遗物先扣金币，再awaitRelicCmd.Obtain，因此子奖励可能在购买Task仍未结束时出现。
- 删牌Wrapper单独实现，awaitDoLocalMerchantCardRemoval处理选择；确认有牌时原生扣款并移除，随后标记Used并最终发购买完成回调，取消不扣钱。当前初次返回及后续selection_option均无purchase_result，属于可选返回设计需要讨论的范围。
- PurchaseStatus仅Success、FailureGold、FailureSpace、FailureForbidden、FailureOutOfStock，当前映射完整。原生Task结果false由UI方法await后丢弃；本地outcome依事件判断，缺少事件且Task完成才归canceled。

OneOffSynchronizer.DoMerchantCardRemoval已核对：先await玩家选牌，card非空时LoseGold、RemoveFromDeck、递增删牌计数。卡牌为空返回false，符合取消不扣钱的实测。

稳定性来源：[ActionSettling](../../src/Sts2Agent/Actions/ActionSettling.cs)、[ActionObservation](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)、[RunUi.ResourceMotionPending](../../src/Sts2Agent/Observation/RunUi.cs)及[ObservationSnapshot](../../src/Sts2Agent/Observation/ObservationSnapshot.cs)。ResourceMotionPending已识别金币_alreadyRunning，但choice_required没有等待该标志；快照将完整顶栏纳入哈希。NTopBarGold.UpdateGoldAnim证据位于原生缓存，先0.25秒Tween再150毫秒延迟，之后逐步改变金币文字。公共期间事件已记录2099→1999扣款，此问题是显示计数变化导致状态令牌失效，不是未记录扣款。

## 验证入口与边界

[专项套件](../../tests/game/data/gui_suite_buy_item_review.json)及[验证器](../../tests/game/verifiers/verify_buy_item_review.py)覆盖十类现有夹具。Courier金币不足由反复原生购买自然到达，没有直接改金币；嵌套Calling Bell、变牌Astrolabe及Cauldron为夹具注入商品，用于购买副流程，不代表普通商店商品配置。

相关Python为shop、opening、closing、shop_presets、gui_suite、resource_events、inventory_events，共50项通过，2.075秒。最终九次受控结果探针位于outcome-probe-isolated.json及probe_outcome_isolated.py，经过真实GameTools，失败／取消对照保留原库存以隔离ID变量；不连接游戏，不能据此证明原生出现错误ID。最初探针另保留，没有覆盖旧证据。

首批gui在变牌场景失败并停止后续假商人，保留原始报告；remaining诊断补测再次遇到stale并在立即重读后再次失败。remaining-settled测试只在记录已确认的stale后，按夹具实际金币等待可见计数到达，再显式观察并继续一次；这是审阅绕过，不能记成产品问题修复。该夹具值只用于测试诊断，不对LLM输出额外信息。

实际三批情况如下：

| 报告目录 | 结果与时间 | 记录内调用 | 自有PID |
| --- | --- | --- | --- |
| gui | 八种通过，choice失败后停止fake；253.715636751秒 | 156次MCP、48条原生操作 | 75715，已退出 |
| remaining | choice诊断及立即重读后仍stale；20.860168791秒 | 13次MCP、3条原生操作、1条差异诊断 | 77042，已退出 |
| remaining-settled | choice及fake两种通过；53.059527783秒；没有触发等待恢复分支 | 27次MCP、4条原生操作 | 77369，已退出 |

合计十种不同场景、十二次场景执行，196次记录内MCP、55条原生操作。不能合称全绿；两次失败证明稳定性缺口仍存在。金币不足由原生购买自然耗金验证；其他用例复现过期／已售ID、已用删牌、价格不可读、关闭、地图／牌组／选择／奖励覆盖的通用拒绝及许可丢失。药水满栏和添水的原生失败保留金币／库存，正常动作许可可续接。

十八份[实际JSON](2026-11-07-buy-item-examples/README.md)保留原始行及SHA-256；初次输入及后续确认／取消缺少purchase_result已分别核对。原生failure_gold／failure_out_of_stock和无选择时canceled映射按源码核对，未新增这些终态的独立GUI；动画失败指状态过期，并未发生错误出牌或误购。

实施修复时，01／02用例要改为准确原因、明确未提交及合法后续操作直接成功；03探针改为拒绝错误ID且不续接；04须移除allow_choice_stale和夹具金币等待，要求初次观察后直接选择成功。审阅中的容忍逻辑不能成为长期回归标准。没有产品代码变更，不运行全量测试或重建。

交付校验核对18份样本的来源／哈希、251条相对链接、50项Python日志、三批报告与三个自有PID退出、DLL一致；最终ID对照探针9例确认现状。产品源码与README相对26ad140未变，主清单保持32/44，buy_item未核销。
