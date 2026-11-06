# open_shop 开发核验依据

> 当前状态：审阅完成，尚未修改工具行为；问题等待定稿。用户决策说明见[审阅与建议](2026-11-07-open-shop-review.md)。

## 基线

- 项目00fe109；Mod0.74.0、MCP0.76.0、schema43。
- 核对日期2026-11-07；Linux游戏v0.107.1/release59260271，RitsuLib0.6.10。
- 安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，实测SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03，与现有原生反编译证据基线一致。
- 构建和隔离运行时Sts2Agent.dll均为163a3ee0db90a7ef238c80c05320e5c756ffeb0ccd89fc0bb791138e106ad209；没有重建、修改版本或正式安装。
- 原始证据根`.tmp/2026-11-07-open-shop-review/`；新增审阅验证器、套件与文档，不修改玩法实现。

## 问题依据

| 编号 | 优先级 | 依据与范围 |
| --- | --- | --- |
| SHOP-OPEN-01 | 中 | GameAdapter.Shop.cs的动作拒绝返回FileMailbox.Error，没有action_submitted:false；注册表open_shop也未声明unsubmitted_rejection_unchanged。GameSession.execute先清许可，不能把这些拒绝识别为未交互。GUI确认ui_interaction_started:false，但合法close_shop、end_turn、selection_option/select_card随后仍得到observation_required |
| SHOP-OPEN-02 | 中 | 房间／Ready拒绝及按钮拒绝均没有public_message；MCP error_output将内部原因替换为固定illegal_action。GUI确认无商店、已打开、地图／牌组覆盖及删牌选择对外相同。AvailableTools另行组合Ready、IsOpen和按钮条件，建议共用具体原因入口 |

stale_state在动作条件之前校验，不能并入保留旧许可的拒绝。MCP本地参数错误没有发送原生请求，已经保留许可。首次未观察直接调用时的observation_required符合现行契约。

## 实现及原生证据

- [GameAdapter.Shop.cs](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)：检查expected_state、当前商店／单人／Ready与按钮；UiChanged后Merchant.ForceClick；ActionObservation以NonCombatBoundary等待。open_shop没有商品购买监听，purchase_result不出现。
- [ShopInspection.cs](../../src/Sts2Agent/Observation/ShopInspection.cs)：Current支持MerchantRoom与FakeMerchant；Exposed拒绝覆盖；Ready检查展开动画、瞄准、交易／遗物任务、卡牌／资源运动、动作队列和输入阻挡。MerchantShown的视口检查用于实际点击商人，不是静态列表读取截断。
- [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：Ready、商品页关闭、商人启用且显示时列出open_shop，与执行当前条件相符，暂未发现列表漏项；重复组合应随具体诊断共用。
- [注册表](../../src/sts2_mcp/tool_registry.py)、[GameSession](../../src/sts2_mcp/game_session.py)、[错误投影](../../src/sts2_mcp/output/error_output.py)：权限要求、动作事件、拒绝证据与公开消息链路。
- [公共动作等待](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)、[非战斗边界](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs)：等待原生就绪及稳定观察，默认25秒；完整观察校验后投影精简回执。未对超时做新增真实扰动。

现有目标版本源码位于`.tmp/2026-10-31-shop/source/`：

- NMerchantButton.OnRelease：普通活着玩家发出MerchantOpened；死亡玩家只触发对白，瞄准时走原生瞄准流程。本项目只支持实际单人，并以Ready排除正在瞄准。
- NMerchantRoom.OpenInventory、NFakeMerchant.OpenInventory：商品页尚未打开时禁用前进，调用Inventory.Open并禁用商人；InventoryClosed再恢复对应按钮。
- NMerchantInventory.Open/DoOpenAnimation：标记商店教学已见、启动展开动画、启用可用返回按钮、更新活动画面和对白；不调用Purchase。背景与库存位置动画由_inventoryTween标识，最长1秒。
- 原生ForceClick位于`.tmp/2026-11-03-architecture-refactor/NClickableControl.cs`：直接OnRelease及Released，跳过hover/focus/pause检查，因此适配器自身的动作合法性检查仍然必要。

## 验证入口与边界

[GUI套件](../../tests/game/data/gui_suite_open_shop_review.json)及[验证器](../../tests/game/verifiers/verify_open_shop_review.py)使用真实MCP，记录公开JSON、原生错误、执行证据及图像数量。用例覆盖无商店、普通商店、假商人、删牌选择和领主阳伞；普通商店还核验地图／牌组覆盖、本地参数错误、full/default、重新打开及立即观察。

该验证器固定审阅基线的两项错误现状，属于复现证据；实施修复时须同步改为准确原因、点击前拒绝证明与合法后续操作直接成功，不能把旧错误断言当作目标接口。

Python相关测试为test_shop、test_shop_presets、test_gui_suite，共29项通过，2.287秒。五类GUI在一个自有进程内全部通过，套件131.761764163秒，69次MCP、9次直接原生检查。报告位于gui/report.json，过程及公开／原生返回保存在各audit/evidence.json；进程PID26588已退出。

普通商店、假商人、删牌商店的首次打开前后，完整player、金币、牌组数量、持有遗物和药水槽名称／空位一致。初次尝试比较整个top_bar时，假商人的恶臭药水usable_here从true变为false；这是商品页打开后不能投掷的已有UI规则，不是资源变化。证据按资源字段分别核对，没有将整个top_bar错误声明为不变。

[十份导出](2026-11-07-open-shop-examples/README.md)为九份full和一份default；按manifest逐份核对原始报告行与SHA-256。未运行全量Python或C#、没有编译；本轮没有产品代码变更。
