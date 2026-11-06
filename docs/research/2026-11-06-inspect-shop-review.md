# inspect_shop 核验与参数建议

> 当前状态：定稿已实现、验收并通过独立审阅，功能82c5dc4已合入main；[实施记录](2026-11-06-shop-inspection-presets-implementation.md)及新JSON另列，原审阅样本保持原样。工具清单30/44，无阻塞。

流程见[工具清单](2026-11-02-mcp-tool-review.md)；源码、问题编号及验证依据见[开发核验](2026-11-06-inspect-shop-development-notes.md)。本页负责实际表现和待决定的设计。

## 审阅基线的优先问题

| 问题 | 影响 | 建议与证据状态 |
| --- | --- | --- |
| 商店关闭、覆盖或不在商店均只报“操作不可用” | 无法判断应打开商店、关闭地图／牌组，还是完成选择／奖励 | 公开固定具体原因，并让详情与可用列表共用；九类GUI确认，尚未修复 |
| 商品详情与screen矛盾的响应仍能通过校验 | 标为covered／hidden却含完整商品的响应仍被接受，并生成后续许可 | 先校验scene、screen与商店详情，再投影／筛选；四种受控坏响应已确认，不能据此声称真实游戏会穿透覆盖页 |
| 商品读取仍按视口截断 | 商品整体离屏会被丢弃；价格标签离屏时变成未知 | 取消读取的离屏筛选，保留商品页展开、真实隐藏／透明／裁剪和缺货判定；源码确认，尚未新增离屏GUI复现 |

只读恢复已实测正确：已有许可时，明确拒绝后可直接打开商店、关闭地图／牌组、取消删牌、结束子奖励或继续战斗；首次失败不生成许可。本地参数错误也保留许可。无需为该工具另做一套拒绝恢复。

另有一项边界待核验：full目前直接提供所有在列商品的说明，对“商品可见但当前无法悬停”的状态没有专门处理。普通买不起的商品仍可悬停，不能因为enabled:false就删掉说明；原生商品还可以通过控制器聚焦。建议在拆分读取判断时核对两种入口，确实无法查看时保留静态信息并给note。此处尚无本轮GUI复现，与上表已确认问题区分。

## 审阅基线的参数与内容

仅支持preset:default/full，默认default，无操作参数或筛选。必须先打开商品页。full包含同次scene、screen和shop，不附送金币、药水槽或available_actions。

shop包含status、view、items及open/back/proceed。items沿用原生布局顺序：每件有id、kind、position、price、affordable、enabled；卡牌另有on_sale和完整card，其他商品使用name及正文／悬停解释。商品ID位于外层，供buy_item使用，card内没有手牌ID。

- 卡牌正文和解释由详情提供，基础观察继续保持无正文的牌面格式。
- 遗物／药水正文和解释在商品行内，不与已持有遗物／药水混淆。
- 可用删牌服务提供正文；已使用服务仍显示打叉条目，used:true、enabled:false、price/affordable:null，没有悬停正文。
- 没有补货时，已买走的普通商品从items消失；送货员补货时同一position换新id。
- price取实际标签；价格不可读时保留未知。affordable表示金币足够，不保证有药水空槽或能绕过添水。
- 重复读取后，金币、库存及商店RNG与读取前一致，已由游戏夹具对比确认。

原生商品页是固定布局，没有遗漏的滚动商品列表。完整库存读取与实际点击范围分开：读取不必按屏幕坐标删商品，点击仍核对可交互性。

## 审阅时的参数分析

以下保留审阅时的参数分析；最终接口以输出定稿及实施记录为准。

- summary保留商品ID、种类、位置、价格、可负担／可点击、特价及删牌使用状态。卡牌沿用共用卡牌摘要；遗物／药水／服务保留名称，省略正文和悬停解释。
- item_ids按外层整数ID筛选，省略或null为全部，[]为空；去重并保持原生顺序，找不到的ID合并到errors，仍返回其他有效商品。完整响应先校验再筛选。
- 可选kinds按card/relic/potion/card_removal分类。若同时支持两种筛选，应取交集；也可先只提供item_ids，减少参数。
- 当前金币建议必加，药水槽也有直接购买用途；牌组数量可辅助删牌选择。建议复用现有静态顶栏字段与药水槽格式，不引入另一套购买状态推断。

建议default/full/summary都增加top_bar，复用现有摘要顶栏的gold、potion_slots、deck_count、relic_count，避免维护另一套字段。药水槽沿用现有名称／空槽与UI提示格式，遗物详情继续由inspect_relics提供。另一种方式是把gold等放在顶层，返回更扁平，但复用既有顶栏入口更一致。

筛选后的商品继续携带原有id和position，不需要再增加结果位置映射。共享解释如果提取到顶层，宜按item_ids关联；目前解释内嵌于各商品，是否提取与去重可作为小范围整理的一部分。

原生还支持右键查看商品卡牌及升级预览，审阅基线的inspect_shop没有对应参数。该能力已进入用户TODO；若增加view_upgrades，需要设计真实预览与页面返回方式，不能只计算升级结果却声称UI已切换。源码依据见开发核验，未加入用户TODO。

## 场景与典型JSON

[16份实际完整返回](2026-11-06-inspect-shop-examples/README.md)包含15份full、一份default，调用与来源见manifest。相同公开错误不逐场景重复导出。

| 场景 | 当前返回及样本 |
| --- | --- |
| 普通库存 | [full](2026-11-06-inspect-shop-examples/inventory.full.json)、[default](2026-11-06-inspect-shop-examples/inventory.default.json)；14件商品，包含完整正文及各行内嵌的悬停解释 |
| 普通购买后 | [买走一张牌](2026-11-06-inspect-shop-examples/after-card.full.json)后剩13项，原ID从列表消失 |
| 送货员补货 | [购买前](2026-11-06-inspect-shop-examples/courier.full.json)、[补货后](2026-11-06-inspect-shop-examples/courier-restocked.full.json)；相同position使用新id，补入卡不继承旧特价 |
| 删牌服务 | [已使用](2026-11-06-inspect-shop-examples/used-removal.full.json)保留used条目，full价格为空且没有悬停说明；选择期间[详情拒绝](2026-11-06-inspect-shop-examples/selection-covered.full.json)，可直接取消 |
| 价格不可读 | [隐藏价格](2026-11-06-inspect-shop-examples/hidden-price.full.json)的商品仍保留正文，price/affordable:null、enabled:false |
| 药水栏满 | [详情](2026-11-06-inspect-shop-examples/full-potions.full.json)仍可能enabled:true；购买失败后商品与金币不变。现有详情看不到已持有药水和空槽 |
| 假商人商品 | [JSON](2026-11-06-inspect-shop-examples/fake-merchant.full.json)统一scene:shop，仅列实际遗物商品，没有额外身份标记 |
| 子奖励返回 | [覆盖时拒绝](2026-11-06-inspect-shop-examples/reward-covered.full.json)，结束子奖励后[恢复库存](2026-11-06-inspect-shop-examples/nested-return.full.json)；此夹具注入普通商店不会出售的召唤铃铛，只用于后续流程边界 |
| 领主阳伞自动购买 | 免费删牌选择时拒绝详情；确认后[只剩已使用服务](2026-11-06-inspect-shop-examples/parasol-complete.full.json) |
| 关闭／地图覆盖／无商店 | [首次读取失败](2026-11-06-inspect-shop-examples/closed-first.full.json)不生成许可；[地图覆盖](2026-11-06-inspect-shop-examples/map-covered.full.json)及[无商店](2026-11-06-inspect-shop-examples/no-shop.full.json)保留已有许可但说明笼统 |

21项相关Python及九类GUI通过，107次真实MCP、14次原生夹具检查；不重建Mod。离屏与不可悬停扰动、真实过渡／超时、其他自动购买组合、多人与第三方商品未新增GUI实测。原生悬停边界仍须在实现前核对，尤其是商品slot自身也能接收控制器焦点，不能只按鼠标Hitbox禁用判定说明不可读。

## 输出定稿

三项优先问题均修复：公开具体原因并共用可用性判断；完整校验scene:shop、screen:{status:visible}及库存状态；商品／价格读取取消视口过滤，实际点击继续检查可交互范围。只读拒绝沿用已有许可恢复。

支持default/full/summary及item_ids、kinds。item_ids为当前外层商品整数ID（0到2147483647），kinds为card/relic/potion/card_removal；两项均省略或null取全部、[]为空，去重并保持原生顺序，组合取交集。找不到的ID相对完整当前商品列表判断，合并为errors:[{code:item_ids_not_found,item_ids:[...]}]；有效ID仅被kinds排除时不报缺失。非法分类为invalid_request，所有输出参数留在MCP本地。

summary的shop主体与get_observation.summary.shop共用同一静态入口：商品购买字段保留，卡牌使用共用摘要，其他商品保留名称和已用状态，省略description、hover_tips及悬停note。筛选保留页面back/open/proceed等公共字段，[]仍返回items:[]。full/default完整说明继续保留在商品／card行内，不增加共享提示重排。

所有预设增加同次快照的top_bar，使用共用摘要顶栏入口，含gold、potion_slots、deck_count、relic_count；药水保留名称、空槽及实际UI提示，不附送已持有遗物正文。完整校验后再精简与筛选，空筛选也拒绝坏响应。

确实不可悬停的商品保留静态信息，notes.hover_tips_unavailable.sources使用shop.items.<原ID>，筛选同步裁剪，summary省略。卡牌正文已直接画在商品卡面，full/default仍保留正文，只有额外hover_tips为null；其他未用商品description:null、hover_tips:[]。已用删牌服务维持无说明字段。鼠标与slot控制器焦点分别判断，单纯点击禁用或金币不足不能等同不可悬停。

升级预览只进入用户TODO：后续统一设计inspect_shop、inspect_selection等工具的原生右键详情／升级对照及实际UI响应，本阶段不实现。
