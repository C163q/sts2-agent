# inspect_shop 开发核验依据

> 当前状态：定稿已实现并完成行为验收，最终审阅／合入见[实施记录](2026-11-06-shop-inspection-presets-implementation.md)；下文保留修复前审阅基线；用户决策内容见[审阅记录](2026-11-06-inspect-shop-review.md)。

## 基线

- 项目efdab40；Mod0.73.0、MCP0.75.0、schema42。
- 核对日期2026-11-06；Linux游戏v0.107.1/release59260271、RitsuLib0.6.10。目标安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，实测SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时DLL均d9bdebffe0562f9238915475668b8c912a385ca62127d996632b446034c924e9，不重建、更新版本或正式安装。
- 原始证据根`.tmp/2026-11-06-inspect-shop-review/`。

## 问题清单

| 编号 | 优先级 | 已核实依据与状态 |
| --- | --- | --- |
| SHOP-INSPECT-01 | 中 | GameAdapter.Shop.cs的房间／暴露／单人拒绝和商品关闭／动画拒绝未设置public_message，MCP以通用错误替换；AvailableTools独立组合相同条件。九类GUI确认，待定稿修复 |
| SHOP-INSPECT-02 | 中 | inspect_shop_details只要求scene:shop及shop自身结构，外层统一scene_context只检查枚举形状。GameTools受控探针的covered、covered+map、covered+deck、hidden均接受完整库存并建立shop-1许可；visible对照也通过。该证据不是实际Mod覆盖穿透 |
| SHOP-INSPECT-03 | 低 | ShopInspection.VisibleSlot使用OnScreen，Synchronize、Read、Find和Purchasable复用，读写职责混在同一可见性函数；价格使用VisibleUi.Number，同样含视口边界。源码确认，未新增离屏GUI扰动 |

只读许可恢复由GameSession.READ_REJECTIONS覆盖：明确读取拒绝及本地参数失败保留旧许可；坏结构导致transport_error会清除。原生购买／开关页面的拒绝策略留待各自工具审阅，不把它们的历史问题计入本查看工具修复。

## 实现入口

- [ShopInspection.cs](../../src/Sts2Agent/Observation/ShopInspection.cs)：Current分普通MerchantRoom与FakeMerchant的NFakeMerchant，外部统一shop；Exposed排除地图／覆盖／过渡。商品页展开且无_inventoryTween时提供库存。详情读取不依赖购买Ready，自动购买／动画中enabled可为false。
- [GameAdapter.Shop.cs](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)：inspect分支返回shopInspection.Read(full:true)，不自行打开页面，不执行按钮动作。与open/close/buy共处一文件，读取拒绝判断与可用列表分散。
- [shop_details.py](../../src/sts2_mcp/output/shop_details.py)：校验各kind完整字段、唯一ID／position、价格／可负担、used服务等；投影丢弃私有字段，未校验screen与内容的关系。
- [public_output.py](../../src/sts2_mcp/output/public_output.py)：商品的hover_tips仍内嵌在card或商品行内，不做全局去重。卡牌正文通过BrowsedCard克隆读取共用格式；商品id只在行外，不能拿来play_card。
- [tool_registry.py](../../src/sts2_mcp/tool_registry.py)：NO_ARGUMENTS及通用default/full，effect:read、requires_permission:false；无专用parser/projector或筛选。

## 目标版本原生证据

缓存`.tmp/2026-10-31-shop/source/`：

- NMerchantInventory.GetAllSlots及Open/Close/BlockInput：库存固定布局，输入阻挡与展开动画是独立条件；BlockInput阻止鼠标及热键并禁用返回，仍可能绘制商品。
- NMerchantSlot.ConnectSignals/OnFocus/OnSelected：鼠标由Hitbox触发，控制器焦点由slot本身FocusEntered触发；不能仅检查Hitbox是否可聚焦就排除整个商品悬停。OnFocus创建说明；是否能买与是否能悬停不同。
- NMerchantCard.UpdateVisual/CreateHoverTip：没货时隐藏slot；库存卡牌是实际CreationResult.Card，价格和特价标签跟原生Entry更新，价格红色反映EnoughGold；右键／控制器预览可打开卡牌详情。购买后卡牌飞向Deck，原slot清空／补货。
- NMerchantRelic/NMerchantPotion.CreateHoverTip：取实际商品模型的悬停说明。NMerchantCardRemoval.UpdateVisual：Used后隐藏价格、Hitbox忽略鼠标、slot不接受控制器焦点，已用服务没有悬停正文是正确边界。
- MerchantEntry/MerchantCardEntry/MerchantCardRemovalEntry、TheCourier、LordsParasol及FakeMerchant：原生购买、补货、服务使用和自动购买规则；不提前生成新库存或根据假商人隐藏身份添加观察字段。

商品卡牌预览另外核对`.tmp/2026-11-01-run-resource-events/source/NInspectCardScreen.cs`的Open/ToggleShowUpgrade/SetCard：NMerchantCard.OnPreview打开该原生页面，升级复选框按MaxUpgradeLevel显示，克隆上处理升级／降级对照。当前inspect_shop不接受view_upgrades；打开原生大图会改变页面边界，不能直接把该参数当纯投影加入。这是候选能力，非现有接口错误。

暂需额外核对的悬停边界：ReadItem(full:true)直接读取所有在列商品的说明，没有专门区分可见但无法悬停的状态。原生slot同时支持鼠标Hitbox和父Control焦点，普通买不起的商品仍可查看；输入阻挡或两种入口都不可用时如何沿用静态数据加note，需实现前进一步核验，尚无本轮GUI复现。

## 验证与证据

专用[审阅器](../../tests/game/verifiers/verify_shop_inspection_review.py)和[九场景套件](../../tests/game/data/gui_suite_shop_inspection_review.json)使用真实stdio MCP，记录原生错误／执行事实；check_test_shop对比资源、库存及商店RNG。已有21项相关Python通过（1.627秒）。

受控上下文探针使用真实GameTools和ShopClient，但构造矛盾响应，不发送真实玩法动作。五组输入／返回及许可结果见证据根context-probe.json。

九类GUI一次通过，195.499秒、107次MCP及14次已记录原生夹具检查，PID55407已退出；最终运行时DLL与基线一致。包含no_shop、basic、remove、courier、hidden_price、fake、full、nested、parasol。详情实际返回scene/screen/shop，没有金币／药水栏／available_actions，summary当前本地拒绝。

closed首次失败不生成许可，已有许可时可直接open_shop。地图／牌组／选牌／子奖励覆盖拒绝后直接close_map、close_card_view、selection_option(cancel)、proceed均通过；战斗中误用后end_turn也能直接继续。本地参数错误及不支持summary保留已有许可。重复详情与fixture完整状态对比相等，商店RNG不变。

[16份实际JSON](2026-11-06-inspect-shop-examples/README.md)为15份full、一份default，保存原调用、证据行与哈希。对购买消失、补货换ID、used服务、价格未知、假商人、满药水和自动购买／嵌套覆盖均作断言。Calling Bell是隔离夹具注入的非普通商店商品，不能据此宣称正常库存会出现该遗物。

未修改生产源码，不构建或重跑完整Python／C#；离屏、不可悬停、过渡／真实超时、多人与全部特殊遗物组合未新增实测。

最终校验16份样本的来源与SHA-256、234个相对链接、九例套件注册、运行时DLL一致、PID55407退出及清单29/44；结果保存于证据根verification.json。持续维护的商店指南补充当前返回范围和已确认限制，待定建议未写成现有参数。

## 建议实现范围

先集中InspectionUnavailableReason供详情和available_actions使用，校验外部scene/screen/shop一致性，再将完整商品可读列表与Purchasable/Find的点击边界拆开。不要把详情重新绑到购买Ready；已用服务的真实悬停禁用、价格未知和库存补货身份保留。

新预设／筛选可遵循既有Python投影层，item_ids对应行ID，kinds按现有kind枚举组合；full完整校验后再处理，[]不能掩盖坏数据。顶栏复用top_bar_summary，卡牌summary复用card_summary；需要统一解释时，item_ids提供稳定关联，不使用筛选后位置。

可见但不能悬停的静态保留规则须按NMerchantSlot的双入口设计：slot.FocusMode与Hitbox鼠标入口均需核对；输入阻挡不是商品没货，不应把显示商品整项丢弃。是否抽取共享解释到顶层、是否增加kinds尚未定稿。
