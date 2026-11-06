# close_shop 开发核验依据

> 当前状态：定稿已实现，当前验收见[实施记录](2026-11-07-shop-closing-recovery-implementation.md)；以下保留审阅基线。用户决策说明见[审阅与建议](2026-11-07-close-shop-review.md)。

## 基线

- 项目dfffbef；Mod0.74.1、MCP0.76.1、schema43。
- 核对日期2026-11-07；Linux游戏v0.107.1/release59260271、RitsuLib0.6.10。
- 目标安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，实测SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03，与引用的原生反编译证据基线相同。
- 构建与隔离运行时Sts2Agent.dll均为09a61eedf19dcf26669a476bbca8174d613aa71484130ad7793b8b3ff535e788；未重建、更新版本或正式安装。
- 证据根`.tmp/2026-11-07-close-shop-review/`；仅新增审阅文档、测试和样本。

## 问题依据

| 编号 | 优先级 | 已核实依据 |
| --- | --- | --- |
| SHOP-CLOSE-01 | 中 | GameAdapter.Shop.cs的页面／Ready及按钮拒绝用FileMailbox.Error，没有action_submitted:false；close_shop注册也没有unsubmitted_rejection_unchanged。GameSession先清旧许可，无法将其恢复为明确未交互拒绝 |
| SHOP-CLOSE-02 | 中 | 页面／按钮拒绝没有public_message，公开错误被替换为固定illegal_action；AvailableTools与执行分别组合IsOpen、Ready和Back.IsEnabled。需共用关闭条件并公开具体原因 |

stale先于商店状态检查，不属于可恢复旧许可的拒绝。MCP本地非法参数未发原生请求，已有许可保留。原始接口多余参数当前也没有明确未提交证明，可随本工具的拒绝协议一并补齐。

## 当前调用与原生流程

- [GameAdapter.Shop.cs](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)：close_shop仍在购买共用分支；没有slot时不实际订阅购买事件，但仍经过这些局部变量、回调定义及finally。UiChanged后Back.ForceClick；ActionObservation以当前run未替换及NonCombatBoundary等待，没有打开分支新增的Owner一致性条件。
- [ShopInspection.cs](../../src/Sts2Agent/Observation/ShopInspection.cs)：Ready排除覆盖、动画、瞄准、交易／遗物任务、卡牌／资源运动、队列及输入阻挡；已打开时要求Back.IsEnabled。页面只在返回按钮OnScreen时输出shop.back，实际动作以原生启用状态检查。当前未确认因此出现的正常可用操作错误，不把该差异直接列为缺陷。
- [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：商品页打开、Ready且返回按钮启用时列close_shop，当前组合与执行相符；尚未发现单独漏项。建议与具体诊断一起集中检查。
- [工具注册](../../src/sts2_mcp/tool_registry.py)、[GameSession](../../src/sts2_mcp/game_session.py)、[错误输出](../../src/sts2_mcp/output/error_output.py)：close_shop为带期间事件的动作，需已有许可；成功完整校验后投影精简回执。未提交拒绝协议及共用页面／活动检查可复用[打开商店修复](2026-11-07-shop-opening-recovery-implementation.md)。

目标原生源码：`.tmp/2026-10-31-shop/source/`内NMerchantInventory、NMerchantRoom、NFakeMerchant；NBackButton位于`.tmp/2026-11-06-shop-inspection-presets/NBackButton.cs`，ForceClick位于`.tmp/2026-11-03-architecture-refactor/NClickableControl.cs`。

- NMerchantInventory._Ready将Back.Released连接到Close；Close停止商人指向效果、杀旧库存Tween并启动收回动画，背景0.8秒／商品位置0.5秒；切换MouseFilter、禁用返回按钮、清最后焦点、IsOpen=false、更新活动画面并发InventoryClosed。
- 普通／假商人的InventoryClosed回调恢复商人和前进按钮。Close本身不调用Purchase、地图打开或旅行。
- NBackButton启用／禁用时以0.35秒Tween滑入／滑出，_isEnabled同步更新；Hotkeys为cancel、pauseAndBack、back三个原生快捷键。按钮视口位置、启用和动画各有实际含义，不能仅凭移动中的坐标推断整次动作是否合法。
- ForceClick跳过hover/focus/pause检查，因此适配器前置检查仍必要。NonCombatBoundary与ActionObservation等待库存Tween及稳定快照，沿用25秒默认超时。

共用PageUnavailableReason目前用opening布尔值区分打开／详情的提示，接入关闭后应改为清晰的用途参数，保持已有打开和详情诊断；无需扩大到其他房间。关闭分支单独整理可避免与购买监听职责继续混杂。

## 验证

[专项套件](../../tests/game/data/gui_suite_close_shop_review.json)与[验证器](../../tests/game/verifiers/verify_close_shop_review.py)覆盖无商店、普通／假商人、删牌、购买子奖励和阳伞。子奖励夹具向商店注入召唤铃铛以触发该边界，并非普通商店的商品配置。实际记录公开JSON、原生错误及执行证据；关闭后直接原生读回只用于核验页面和资源，不为MCP会话刷新许可，因此后续open_shop／proceed可验证真正直接续接。

审阅时的验证器固定上述错误现状，原始报告保留；当前验证器已按定稿改为具体原因、未提交证明与合法后续操作直接成功，修复结果另存实施记录。六类GUI在单一自有游戏进程全部通过，158.587145418秒，83次真实MCP及35次直接原生操作；PID63320已退出。报告位于gui/report.json及各audit/evidence.json。正常关闭后立即核对merchant／items:null，金币、牌组数、持有遗物及药水名称／空位不变；假商人恶臭药水的usable_here恢复可用属于原生画面规则，不作为资源变化。相关Python为test_shop、test_shop_opening、test_shop_presets、test_gui_suite，共33项通过，1.867秒；没有产品改动，不运行全量测试或构建。

[十二份实际返回](2026-11-07-close-shop-examples/README.md)保留十一份full、一份default，按manifest核对原始行与SHA-256。两项问题在页面已关闭、地图／牌组覆盖、删牌／子奖励／阳伞选择及无商店等分支复现，拒绝期间ui_interaction_started/action_submission_observed均为false，前后snapshot_id一致。真实中途动画、无run、多人与未知异常只核对源码，未新增GUI扰动。

交付校验已确认十二份样本来源／哈希、234条相对链接、测试日志、PID退出及DLL一致；相对基线dfffbef，产品源码与README未变。工具清单仍为31/44，close_shop保留设计讨论状态。
