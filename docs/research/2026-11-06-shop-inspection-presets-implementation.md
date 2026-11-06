# 商店详情预设、购买上下文与读取边界

> 当前状态：实现、验收及独立审阅完成，共1项，已完成1项；功能82c5dc4已合入main，无剩余必修项或阻塞。

要求见[输出定稿](2026-11-06-inspect-shop-review.md#输出定稿)，步骤见[实施计划](../superpowers/plans/2026-11-06-shop-inspection-presets.md)。原[开发审阅](2026-11-06-inspect-shop-development-notes.md)及16份旧JSON保留原基线。

## 实现与职责

- inspect_shop支持default/full/summary、item_ids及kinds，后两项取交集；省略／null为全部，[]为空。缺失ID相对完整当前列表判断，去重归并，保留原生顺序。输出参数留在Python，本次原生inspect_shop仍无参数。
- shop_summary是详情摘要与get_observation.summary.shop的共同入口，卡牌沿用card_summary。完整说明保持行内，summary省略正文／悬停解释；两种工具的基础信息格式相同，分别取各自调用时的快照。
- 全预设增加摘要top_bar，使用同次原生快照和共用顶栏入口，包含gold/potion_slots/deck_count/relic_count；隐藏值保持未知。schema43要求购买顶栏字段及完整四项，旧schema兼容部分旧响应。
- InspectionUnavailableReason由详情与available_actions共用，区分无商店、关闭、覆盖及动画。读取独立于交易Ready；纯读取拒绝沿用已有许可规则，坏上下文或内容会清除许可。
- DisplayedSlot与真实点击边界分开，读取商品和价格不按视口裁剪，保留实际显隐／透明／裁剪／缺货检查。点击继续要求实际可交互范围。NativeVisual来源核对原生protected Visual属性，避免只看空容器或价格就公开隐藏商品。
- 鼠标与控制器能力分别核对实际有效输入属性，考虑库存输入阻挡。单纯禁用点击／买不起仍能查看；确实不可悬停时保留静态数据和按原ID关联的note。卡牌正文已直接绘制，只有额外hover_tips为null；其他未用商品description:null、hover_tips:[]，已用服务维持无说明字段。筛选裁剪关联note，summary省略。
- 右键详情和升级对照仅加入用户TODO，后续连同inspect_selection及实际UI响应统一设计。本阶段没有新增view_upgrades或打开右键页面。

主要入口：[ShopInspection.cs](../../src/Sts2Agent/Observation/ShopInspection.cs)、[读取适配](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)、[完整校验／共用摘要](../../src/sts2_mcp/output/shop_details.py)、[本地参数／投影](../../src/sts2_mcp/output/shop_presets.py)、[共用顶栏](../../src/sts2_mcp/output/top_bar_summary.py)。现行契约见[商店](../development/shop.md#打开观察与详情)。

## 基线与原生证据

基线94057b6；核验跨2026-11-06至07，Linux游戏v0.107.1/release59260271、RitsuLib0.6.10。目标安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。最终Mod0.74.0、MCP0.76.0、schema43；证据根`.tmp/2026-11-06-shop-inspection-presets/`。

原生商店流程沿用开发审阅引用的NMerchantSlot/NMerchantInventory及各商品类型源码。ConnectSignals直接订阅Hitbox.MouseEntered和slot.FocusEntered，不能以Hitbox.IsEnabled代替悬停能力。商品卡面正文可直接阅读，既有hidden_price场景截图确认该显示方式。

另外从当前GodotSharp.dll定点反编译Godot.Control，核对GetFocusModeWithOverride/GetMouseFilterWithOverride及递归输入覆盖；从当前游戏程序集核对NBackButton.OnEnable/OnDisable的0.35秒_moveTween。源文件保存在证据根，不纳入Git。

## 失败验证与修正

新增8项Python方法先在旧实现出现40个失败、1个错误，涉及不支持预设／筛选和缺少新字段／校验；旧DLL的no_shop新GUI断言在笼统错误处预期失败（15.775秒、1次MCP，PID7828退出）。

实现后32项相关Python通过（2.109秒）；初次完整751项Python通过（41.576秒）。四次构建均0警告／0错误，日志分别build.log（6.51秒）、build-final.log（4.08秒）、build-focus-fixture.log（3.98秒）、build-verified.log（4.09秒）。

首轮新GUI在controller_only处失败（24.227秒、39次MCP，DLL81096b0c79513782a2a637d2da030098ff53342567accd4a5577714db59f1be3）：手动遍历祖先将递归Disabled视为不可覆盖，判断过严。加强夹具，明确设置局部Enabled并记录原生有效焦点All后，focus-red仍失败（23.101秒、39次MCP，DLL2595473465ce53ea29627613d701a4298208a319d7ae2d1f6bbc6301c1ad0e63），证实是实现问题；随后改用原生有效输入getter。

修正后controller_only、mouse_only及click_disabled均通过；gui-verified在blocked的两次摘要比较处失败（25.469秒、53次MCP）。差异仅为back:{enabled:false}到省略：原生禁用按钮以0.35秒动画移出视口，两次调用跨过显示边界。这是比较前提问题，不改读取行为；测试改为有限等待实际back状态后再比较，保留失败记录。最终DLL未因此再次构建。

## 最终验收

- 最终DLL与隔离运行时均163a3ee0db90a7ef238c80c05320e5c756ffeb0ccd89fc0bb791138e106ad209。
- 最终完整Python751项通过（38.003秒），C#131项通过。历史冻结JSON未改写，仅对获批新增顶栏和新summary覆盖调整旧测试的预期副本／目录断言。
- 十类专项GUI一次通过，242.195秒、213次MCP及66次原生辅助调用，PID19199退出。含九类原审阅场景及display的16组显示／焦点／顶栏扰动；81个测试入口的testMode关闭／suite关闭门控均拒绝。
- 旧verify_shop的basic/courier/remove三类回归通过，100.806秒、77次MCP及8次夹具检查，PID19972退出；额外覆盖普通遗物／药水购买及旧选择流程。
- 受控GameTools探针重新核验：visible对照通过，四组矛盾screen均transport_error且不生成许可。它不是对实际游戏覆盖穿透的复现。

通过轮次共290次MCP；所有GUI轮次包括旧DLL RED及两个焦点失败、按钮动画比较失败，共422次MCP、128次已记录原生辅助调用。全部六个自有游戏进程退出。没有覆盖失败目录，也不将分组验证描述成单轮全绿。

[22份最终实际JSON](2026-11-06-shop-presets-examples/README.md)为16份full、1份default及5份summary，含[详情摘要](2026-11-06-shop-presets-examples/inventory.summary.json)、[基础观察摘要](2026-11-06-shop-presets-examples/observation.summary.json)、[按ID筛选](2026-11-06-shop-presets-examples/id-filter.summary.json)、[不可悬停卡牌](2026-11-06-shop-presets-examples/no-hover-card.full.json)、[未知金币](2026-11-06-shop-presets-examples/hidden-gold.full.json)和[整栏隐藏](2026-11-06-shop-presets-examples/hidden-top-bar.full.json)。完整调用／来源／哈希见manifest。

## 文档与边界

商店、MCP、观察边界及GUI指南同步为当前格式；用户TODO将商店改进核销，并新增明确要求的统一右键／升级预览待办。完整说明保持行内，未增加无关的共享解释重排。

未新增多人、第三方商品、真实超时、并发人工干预、全部折扣／自动购买组合实测；Calling Bell为受控嵌套商品，不能据此推断普通商店库存。界面遮挡遵循现有几何及原生层级，不承诺任意Mod图层的逐像素判断。右键升级只留待后续。

已校验新22份及原16份样本的来源／SHA-256、449个相对链接、十例套件注册、运行时DLL一致、六个自有进程退出及TODO3/8／工具清单30/44，证据根verification.json保存结果。未正式安装或推送。

## 最终独立审阅与合入

唯一独立只读审阅94057b6..82c5dc4：Critical0／Important0／Minor0，可合入。额外核验38份样本哈希／来源、最终十例专项与三例旧回归报告及DLL一致，未改文件／Git、启动游戏或重跑完整测试。未发现需要扩大的职责混杂或实质重复。功能已快进合入main，工具清单核销30/44。

审阅唯一Declined to judge为原生右键详情／升级预览。最终裁定：按用户明确要求仅记录TODO，不纳入本轮实现；代价是相关工具暂不能提供这项升级对照，留待跨工具和UI设计时处理。没有暂缓的Minor事项。

本计划独有工作区归档到证据根inline-workspace，经逐文件SHA-256验证后移除原目录，未改动其他任务目录。合入后证据校验通过，不为提交或快进合入重建DLL。
