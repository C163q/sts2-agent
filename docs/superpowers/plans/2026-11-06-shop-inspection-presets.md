# 商店详情预设与购买上下文实施计划

> 当前状态：完成，共1项，已完成1项；行为验收及最终独立审阅通过，功能82c5dc4已合入main，无剩余必修事项或阻塞。
> 使用superpowers:executing-plans在当前会话完成，最后一次独立审阅，不按步骤派发代理。

**目标：** 修复inspect_shop诊断、上下文及读取边界，提供共享summary、item_ids/kinds筛选及购买顶栏。
**架构：** ShopInspection集中可读性和商品显示／点击／悬停边界；基础观察和详情summary复用shop_summary及卡牌／顶栏格式；完整响应校验后本地筛选。保持行内完整说明，升级预览只记用户TODO。
**规格：** [输出定稿](../../research/2026-11-06-inspect-shop-review.md#输出定稿)。
**技术：** C#／Godot、Python MCP、unittest、隔离GUI。

## 约束

- 保留只读许可规则；具体拒绝与available_actions共用，读取不依赖交易Ready。
- item_ids/kinds省略或null为全部，[]为空；组合取交集，ID缺失按完整当前列表判断并合并item_ids_not_found。非法kind是参数错误。原生不接收输出参数。
- default/full/summary都返回共用摘要top_bar，保留gold/potion_slots/deck_count/relic_count，所有预设使用同次快照；隐藏值不从模型补齐。
- inspect_shop.summary.shop与get_observation.summary.shop使用同一函数，卡牌沿用card_summary，省略全部悬停说明／note。full/default说明保持行内。
- 商品和价格读取取消视口截断；点击保持OnScreen合法性。隐藏／透明／裁剪和已售出判定保留。
- 鼠标Hitbox与slot控制器焦点分别核验。买不起／单纯点击禁用仍可悬停；确实不可悬停时保留静态字段和shop.items.<id>来源note。卡牌直接显示正文，保留正文，仅hover_tips:null；其他未用商品description:null、hover_tips:[]。已用删牌服务维持无说明字段。
- 升级预览不实现，TODO记录跨inspect_shop、inspect_selection和真实UI响应的后续设计。
- Mod0.74.0、MCP0.76.0、schema43；旧schema测试数据兼容，新schema要求top_bar字段及完整购买上下文。
- 验证后自动提交、合入main、删除临时分支，不正式安装或推送。

## 审阅重点

- 覆盖、关闭／打开动画和交易输入阻挡时读取与点击边界分离，拒绝后保留已有许可。
- ID与分类组合、两种空筛选、被分类排除的有效ID不能误报缺失，错误与note关联稳定。
- 视口外商品／价格仍读取，真正隐藏／透明／裁剪排除，取得／补货ID不复用。
- 仅鼠标／仅控制器／点击禁用／完全不可悬停的差异及卡面正文静态可读；输入阻挡时保留静态列表。
- 顶栏部分／全部隐藏、nullable说明及坏响应不能被summary或空筛选掩盖，读取不改变RNG／资源。

### Task 1: 商店详情与共用静态格式

**文件：** ShopInspection.cs、GameAdapter.Shop.cs、AvailableTools.cs；output/shop_details.py及新shop_presets.py、top_bar_summary.py、observation_presets.py；tool_registry.py、版本／schema；新tests/python/test_shop_presets.py，现有商店GUI审阅器与受保护ShopDisplayFixture，相关持续文档和新JSON样本。

**接口：**
- ShopInspection.InspectionUnavailableReason(Context?)、DisplayedSlot(slot)、Visual(slot)、CanHover(context,slot)、Inspect()；Purchasable/Find保留实际点击边界。
- shop_summary(value)给基础观察和详情summary共用；shop_inspection_arguments、shop_preset；top_bar_summary从共用已投影形状取四项。

- [x] Step 1：写Python真实GameTools覆盖预设、双筛选、错误归并、上下文与不可悬停证明、顶栏和许可；改GUI断言并先跑旧实现，确认预期失败。
- [x] Step 2：实现集中读取／显示／悬停判断、原生同次顶栏和本地参数／投影／校验；加入受保护显示夹具，并核对目标原生API。
- [x] Step 3：相关Python及编译／C#通过，准备隔离运行时，完成商店九类流程和显示／焦点／顶栏边界GUI；保留失败现场。
- [x] Step 4：完整Python、适用C#通过；同步文档、TODO已有覆盖与用户新增项、实际JSON和来源／哈希、相对链接、进程及运行时校验。
- [x] Step 5：验证后提交；task-done运行证据校验脚本，不重复已通过的完整测试或GUI。

## 最终收尾

- [x] 一次最终独立审阅；必要的重要修复做失败→通过验证，记录裁定／未验证范围；归档并校验本计划独有工作区，再合入main并删除临时分支。

命令：Python相关100秒、完整180秒有限超时；dotnet build90秒、C#45秒；GUI各套件420秒。证据根.tmp/2026-11-06-shop-inspection-presets/，最后verify_delivery.py校验实跑结果及样本；不为提交或快进合入重建DLL。
