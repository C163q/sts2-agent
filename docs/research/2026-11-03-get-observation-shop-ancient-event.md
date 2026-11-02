# get_observation 商店、先古之民与普通事件核验

> 当前状态：10–12 组现状核验完成，16 类夹具的 82 份完整 full 样本已保存；进入 summary 设计讨论，尚未定稿或修改工具行为。其余 5 组（13–17）待选，get_observation 整体未核销。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)，分组见[观察场景目录](2026-11-02-get-observation-review.md)。本轮只展示 10–12 组的现状和完整 `preset:"full"`，不提前修改工具参数或 summary；inspect_shop、inspect_ancient、inspect_event 用于核对基础观察与详情的区别，不在本轮核销。13 组占卜、14 组确认框及 01–04 组选择／战斗沿用各自核验范围。

## 基线与证据

- 核对日期：2026-11-03，项目基线 `4c0831f`，MCP `0.50.3`、Mod `0.49.2`、schema `31`。
- 目标游戏 Linux `v0.107.1`、release `59260271`，RitsuLib `0.6.10`。游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 构建产物与隔离运行时 Mod DLL 的 SHA-256 同为 `1d1a7e8c180bbb05b15f3ee8a5dbbf098485685dda393466eb3e5356e6d403ed`。本轮不重新构建或安装正式 Mod；不修改正式存档。
- 原生读取：[ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs)、[AncientInspection](../../src/Sts2Agent/Observation/AncientInspection.cs)、[EventInspection](../../src/Sts2Agent/Observation/EventInspection.cs)。场景优先级及基础观察见 [GameAdapter.Observe](../../src/Sts2Agent/Adapter/GameAdapter.cs)，动作与详情可用性见 [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- 公开字段与校验：[game_output.py](../../src/sts2_mcp/output/game_output.py)、[shop_details.py](../../src/sts2_mcp/output/shop_details.py)、[ancient_details.py](../../src/sts2_mcp/output/ancient_details.py)、[event_details.py](../../src/sts2_mcp/output/event_details.py)。各项 full 保留基础观察空值，不等于自动调用 inspect_* 或展开悬停。
- 目标程序集新反编译证据位于 `.tmp/2026-11-03-observation-interactions-review/source/`：NMerchantInventory、NMerchantRoom、NFakeMerchant、MerchantEntry、MerchantCardEntry、MerchantCardRemovalEntry、TheCourier、NAncientEventLayout、NAncientDialogueLine、NEventLayout、NEventOptionButton、EventOption、EventModel、AncientEventModel、AbyssalBaths、SelfHelpBook、BattlewornDummy、BrainLeech、Trial。源码及游戏资产不纳入 Git。
- 隔离 GUI 的真实 stdio MCP 返回、相邻截图、采样脚本和核对结果保存在 `.tmp/2026-11-03-observation-interactions-review/`。测试夹具预置了金币、牌组、药水、遗物和目标房间，数值不代表正常开局。截图与观察是相邻调用，不是同帧原子采样。

## 10：商店

| 字段／状态 | 当前含义 |
| --- | --- |
| scene | shop；普通商店与尚未揭露的假商人使用同一类型，不提前揭示身份 |
| shop.status | visible／covered；被地图、选牌、奖励覆盖时 view、items、open、back、proceed 均为 null |
| view:merchant | 商品页未打开，items:null；open 是可点击商人入口，proceed 是离开房间按钮 |
| view:inventory | 商品页已打开，items 为当前展示的商品，back 为返回商人按钮；open/proceed:null |
| view:opening/closing | 原生商品页动画中，items 和按钮不可用；稳定动作通常等待其结束 |
| items[].id | 当前商品身份的整数 ID，不等于数组下标；同槽补货分配新 ID，其他未变商品保留 ID |
| kind | card、relic、potion、card_removal |
| position | 原生类别与槽位，如 character_card:0、relic:0；用于识别补货前后的同一位置，不能代替购买 ID |
| price／affordable／enabled | 可见标价／当前金币够不够／是否能执行购买；enabled 还受动画、锁定和父流程限制 |
| card | name、type、rarity、visual_card_pool、energy_cost、star_cost；商品 ID 在外层，不另造卡牌 ID |
| on_sale | 卡牌的实际打折标识；price 已是当前价格，非卡牌没有此字段 |
| name | 遗物、药水及删牌服务的已展示名称；基础观察不附效果正文 |
| used | 仅删牌服务使用，true 后该项仍保留，但 price/affordable:null、enabled:false |

shop.view 表示商店内部页面阶段，screen.view 继续用于地图、牌组等覆盖页。正常布局通常有 14 项，但不固定数量。已售出且不补货的卡牌、遗物和药水从 items 消失；不制造 sold_out 对象。删牌服务已用项保留，不能把它和普通售罄混为一谈。The Courier 的同槽补货使用新 ID；旧购买 ID 不再对应新商品。

`affordable:true` 或 `enabled:true` 不保证药水能放进栏位：原生购买会返回 `purchase_result.status:failure_space/failure_forbidden` 等，商品和金币可能保持不变。get_observation 只描述此刻静态页面，不重复 purchase_result 或 transition，也不从满栏预先隐藏商品。

删牌进入选择时，shop 保留 covered 状态，selection 为当前可浏览候选。取消整个选择返回原库存而不花费；确认后返回库存，删牌项变 used。买遗物引发的选牌或嵌套奖励同样覆盖库存，不能穿透购买。测试中的 Calling Bell 是受门控夹具放入普通商店，用于验证嵌套界面，不表示正常商店会出售它。

`inspect_shop` 必须在商品页已打开时使用：卡牌增加正文与 hover_tips，遗物、药水、未用删牌服务增加说明与 hover_tips；读取不自动开店。基础观察 full 仍只有上述商品卡牌摘要，不包含正文、费用颜色、描边、已有附魔字段；不能声称与手牌 full 或当前手牌 summary 的完整字段一致。后续如统一摘要，需要另外核对商店卡面的实际显示及可读字段。

对照本轮库存截图可以确认，商品卡牌的正文直接显示在画面上，而当前基础观察 full 没有返回。这是现有数据范围与静态可见信息之间需要讨论的差异；并非需要悬停才能看到。建议后续先决定 full/default 是否补齐这些已展开正文，再决定 summary 是否保留，而不是将当前缺失当作既定摘要原则。本轮只记录，不修改行为。

商店、普通事件和先古选项是固定布局；[完整可浏览内容审查](2026-11-02-browsable-content-audit.md)已经核对这几类页面没有被遗漏的滚动列表。当前源码的 OnScreen 不能仅因名字就视为无用截断：未开商品页、遮盖、动画离场和隐藏节点仍应排除。原生布局与当前版本的实际阅读范围见该审查。

现行操作说明见[商店接口](../development/shop.md)。

## 11：先古之民

| 字段／状态 | 当前含义 |
| --- | --- |
| scene | ancient；选牌／地图覆盖可能保持此底层场景，弹出奖励或进入战斗则优先使用对应场景 |
| status | visible／covered；covered 时除 status 外全部为 null |
| name／epithet／description | 先古名称／已显示的称号／当前已显示说明；无显示内容时 null，不补尚未出现的后文 |
| dialogue | 当前画面可读的已展示对话，每项 speaker、text；不是全部剧情，也不是只返回最新一行 |
| options | 已显示馈赠，每项 id、title、description、enabled；基础观察已经含选项正文 |
| continue | 当前推进对话入口的 text、enabled；不是选择馈赠或离开房间 |
| proceed | 当前原生前进入口的 text、enabled；与 continue 分离 |

NAncientEventLayout 预创建对话节点后逐行显示并自动移动内容。已显示旧对话可以变淡或移出可读区域；未来未显示的节点仍不能读取。名称横幅和称号也可能随原生入场、覆盖动画出现或隐藏。工具保留这些实际可见性，不以“模型里已有对话／称号”补齐。

continue.text:null 表示原生没有显示推进按钮文字，不等于该入口不可用；以 enabled 和 available_actions 为准。

推进对话阶段可能已经有部分选项进入画面，但它们仍 disabled；应按 continue／available_actions 判断交互，不因有 options 就直接选择。对话结束后再启用原生馈赠。选项数量不固定为三个：隔离夹具使用 DebugOption 替换第一个馈赠来稳定复现流程，其余候选仍由原生生成；不把夹具的具体遗物组合当作正常随机生成结果。

馈赠可能立即修改生命或遗物，也可能进入卡牌包、移除／附魔／变牌及结果确认，或者嵌套奖励。这些页面使用已有 selection/rewards 契约，先古之民页面为 covered；不能提前展示结果或自动选取。完成后重新读取原生对话／说明和 proceed，不假定必定恢复相同字段值。

`inspect_ancient` 主要增加各选项的额外 hover_tips，不推进对话；选项的 title、description 本就属于静态可见正文。当前 summary 仍沿用 default 的房间主体，顶栏和选牌使用共用摘要，尚未在本轮定稿先古内容的删减。

现行操作说明见[先古之民接口](../development/ancients.md)。

## 12：普通事件

| 字段／状态 | 当前含义 |
| --- | --- |
| scene | event；问号仅是地图节点图标，具体界面可能改用 shop、combat、rewards 等场景 |
| status | visible／covered；覆盖时 name、description、options、proceed 均为 null |
| name／description | 当前已展示名称与完整正文；正文渐显未完成时 description:null，不预读未来页面 |
| options | 当前页面已展示选项，包括锁定项；每项 id、title、description、enabled、lethal_warning |
| id | 绑定原生选项身份的整数，不等于选项序号；翻页后可能全部变化，应使用当前返回值 |
| enabled | 合并原生锁定、重复选择及当前流程就绪条件；false 不一定只有一个原因 |
| lethal_warning | 原生危险红框是否显示；false 不等于自动证明安全，true 也不预判复活后的最终结果 |
| proceed | 事件确已结束后新增的原生离开按钮；普通“继续”“离开”“战斗”仍可能是 options 中的一项 |

基础观察提供当前正文和选项效果，不是程序再生成的文字摘要。动态数值、费用与后续页面来自原生事件及英语格式化；不能仅保留标题、凭旧选项 ID 操作，或把所有事件的 Continue 都改成同一个 proceed。

通用读取仅适用于目标游戏程序集中的 Default／Combat 布局事件；先古之民、建筑师和专属界面分别处理。Self-Help Book 的锁定项仍展示 title／description；inspect_event 只对当前原生可悬停的选项补 hover_tips，锁定项不伪造悬停帮助。

选择之后可以出现新一页事件，也可以由卡牌选择、奖励、确认框或战斗接管。选牌与奖励覆盖时 event 为 covered；战斗时 scene:combat，父事件的文字不穿透显示。Battleworn Dummy 可在战斗后恢复父事件，并在事件流程里发放药水奖励；战胜后不能一律理解成已离开问号房或可以直接选地图。

Trial 第二次拒绝进入 screen.view:confirmation，此时基础观察已有 confirmation 的标题、正文与按钮，底层 event 覆盖；本轮只收录进入和取消返回的边界，字段设计留给第 14 组。Crystal Sphere 的专属棋盘及图像归第 13 组，不把它混入通用 event 文本摘要。未知专属布局和第三方 Mod 事件没有由这些样本自动取得支持。

现行说明见[事件接口](../development/events.md)，选牌另见[已完成的选择核验](2026-11-02-get-observation-selections.md)。

## 待讨论的 summary

本轮不新增参数、不删字段，当前 summary 继续对三个房间主体使用 default；顶栏按独立组件精简，选择页复用卡牌摘要。设计时需要分别考虑：

- 商店是否仅精简 card 的 rarity、visual_card_pool，以及是否需要按商品 ID／类型筛选；保留 item.id 与可执行性，不把商品身份替换成手牌身份。
- 先古和事件的 description 本就是决策所需的已展开正文，进一步删减会损失选择后果。对话、称号、页面标题与空列表是否保留，待明确取舍。
- covered、未开店、锁定选项、已用删牌以及不可读价格的语义不同；不能统一用一个“无内容”表示。
- get_observation 不回放动作事件。本轮的完整 full 样本不附 transition、purchase_result 或先前奖励结果。

## 完整 full 样本

所有文件均为真实 `get_observation({"preset":"full"})` 的完整 structuredContent：不删 null、不截断列表、不更名、不改写数值及 ID，不添加解释字段。采样时逐次核对文字 JSON 与 structuredContent 一致；每份样本均有相邻截图，完整路径与调用下标见本地 samples-manifest.json。下表“来源”为证据根目录下的 `<批次>/<用例>/evidence.json` 和从 0 开始的数组下标；完整截图路径见 manifest。

### 10：商店样本

| 分支／状态 | 完整 full JSON | 来源／下标 |
| --- | --- | --- |
| 普通库存与售出：初始画面 | [shop-basic-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-initial.full.json) | `gui/shop_basic`：0 |
| 普通库存与售出：商品页 | [shop-basic-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-inventory.full.json) | `gui/shop_basic`：3 |
| 普通库存与售出：地图覆盖 | [shop-basic-map.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-map.full.json) | `gui/shop_basic`：7 |
| 普通库存与售出：买牌后 | [shop-basic-after-card.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-after-card.full.json) | `gui/shop_basic`：12 |
| 普通库存与售出：买遗物后 | [shop-basic-after-relic.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-after-relic.full.json) | `gui/shop_basic`：15 |
| 普通库存与售出：买药水后 | [shop-basic-after-potion.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-after-potion.full.json) | `gui/shop_basic`：18 |
| 普通库存与售出：返回商人 | [shop-basic-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-merchant-returned.full.json) | `gui/shop_basic`：21 |
| 普通库存与售出：前进后地图 | [shop-basic-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-basic-proceeded.full.json) | `gui/shop_basic`：24 |
| 删牌服务：初始画面 | [shop-remove-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-initial.full.json) | `gui/shop_remove`：0 |
| 删牌服务：商品页 | [shop-remove-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-inventory.full.json) | `gui/shop_remove`：3 |
| 删牌服务：删牌候选 | [shop-remove-removal-choice.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-removal-choice.full.json) | `gui/shop_remove`：7 |
| 删牌服务：取消删牌 | [shop-remove-removal-canceled.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-removal-canceled.full.json) | `gui/shop_remove`：10 |
| 删牌服务：删牌确认预览 | [shop-remove-removal-preview.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-removal-preview.full.json) | `gui/shop_remove`：15 |
| 删牌服务：删牌已用 | [shop-remove-removal-used.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-removal-used.full.json) | `gui/shop_remove`：18 |
| 删牌服务：返回商人 | [shop-remove-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-merchant-returned.full.json) | `gui/shop_remove`：21 |
| 删牌服务：前进后地图 | [shop-remove-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-remove-proceeded.full.json) | `gui/shop_remove`：24 |
| The Courier 补货：初始画面 | [shop-courier-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-courier-initial.full.json) | `gui/shop_courier`：0 |
| The Courier 补货：商品页 | [shop-courier-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-courier-inventory.full.json) | `gui/shop_courier`：3 |
| The Courier 补货：同槽补货 | [shop-courier-restocked.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-courier-restocked.full.json) | `gui/shop_courier`：7 |
| The Courier 补货：返回商人 | [shop-courier-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-courier-merchant-returned.full.json) | `gui/shop_courier`：10 |
| The Courier 补货：前进后地图 | [shop-courier-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-courier-proceeded.full.json) | `gui/shop_courier`：13 |
| 药水满栏：初始画面 | [shop-full-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-full-initial.full.json) | `gui/shop_full`：0 |
| 药水满栏：商品页 | [shop-full-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-full-inventory.full.json) | `gui/shop_full`：3 |
| 药水满栏：满栏购买拒绝后 | [shop-full-potion-refused.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-full-potion-refused.full.json) | `gui/shop_full`：7 |
| 药水满栏：返回商人 | [shop-full-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-full-merchant-returned.full.json) | `gui/shop_full`：10 |
| 药水满栏：前进后地图 | [shop-full-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-full-proceeded.full.json) | `gui/shop_full`：13 |
| 尚未揭露的假商人：初始画面 | [shop-fake-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-fake-initial.full.json) | `gui/shop_fake`：0 |
| 尚未揭露的假商人：商品页 | [shop-fake-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-fake-inventory.full.json) | `gui/shop_fake`：3 |
| 尚未揭露的假商人：购买后剩余库存 | [shop-fake-after-purchase.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-fake-after-purchase.full.json) | `gui/shop_fake`：7 |
| 尚未揭露的假商人：返回商人 | [shop-fake-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-fake-merchant-returned.full.json) | `gui/shop_fake`：10 |
| 尚未揭露的假商人：前进后地图 | [shop-fake-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-fake-proceeded.full.json) | `gui/shop_fake`：13 |
| 购买后嵌套奖励：初始画面 | [shop-nested-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-initial.full.json) | `gui/shop_nested`：0 |
| 购买后嵌套奖励：商品页 | [shop-nested-inventory.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-inventory.full.json) | `gui/shop_nested`：3 |
| 购买后嵌套奖励：嵌套奖励覆盖 | [shop-nested-nested-rewards.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-nested-rewards.full.json) | `gui/shop_nested`：7 |
| 购买后嵌套奖励：子流程返回 | [shop-nested-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-returned.full.json) | `gui/shop_nested`：15 |
| 购买后嵌套奖励：返回商人 | [shop-nested-merchant-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-merchant-returned.full.json) | `gui/shop_nested`：18 |
| 购买后嵌套奖励：前进后地图 | [shop-nested-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/shop-nested-proceeded.full.json) | `gui/shop_nested`：21 |

### 11：先古之民样本

| 分支／状态 | 完整 full JSON | 来源／下标 |
| --- | --- | --- |
| 长对话与普通馈赠：初始画面 | [ancient-dialogue-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-initial.full.json) | `gui-remaining/ancient_dialogue`：0 |
| 长对话与普通馈赠：推进对话 1 次后 | [ancient-dialogue-dialogue-1.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-dialogue-1.full.json) | `gui-remaining/ancient_dialogue`：3 |
| 长对话与普通馈赠：推进对话 2 次后 | [ancient-dialogue-dialogue-2.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-dialogue-2.full.json) | `gui-remaining/ancient_dialogue`：6 |
| 长对话与普通馈赠：地图覆盖 | [ancient-dialogue-map.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-map.full.json) | `gui-remaining/ancient_dialogue`：10 |
| 长对话与普通馈赠：牌组覆盖 | [ancient-dialogue-deck.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-deck.full.json) | `gui-remaining/ancient_dialogue`：14 |
| 长对话与普通馈赠：关闭浏览后选项就绪 | [ancient-dialogue-ready-after-browsing.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-ready-after-browsing.full.json) | `gui-remaining/ancient_dialogue`：19 |
| 长对话与普通馈赠：选择馈赠后 | [ancient-dialogue-after-choice.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-after-choice.full.json) | `gui-remaining/ancient_dialogue`：22 |
| 长对话与普通馈赠：前进后地图 | [ancient-dialogue-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-dialogue-proceeded.full.json) | `gui-remaining/ancient_dialogue`：25 |
| 卡牌包馈赠：初始画面 | [ancient-bundle-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-initial.full.json) | `gui-final/ancient_bundle`：0 |
| 卡牌包馈赠：馈赠选项就绪 | [ancient-bundle-choices-ready.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-choices-ready.full.json) | `gui-final/ancient_bundle`：6 |
| 卡牌包馈赠：选择馈赠后 | [ancient-bundle-after-choice.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-after-choice.full.json) | `gui-final/ancient_bundle`：10 |
| 卡牌包馈赠：卡牌包预览 | [ancient-bundle-bundle-preview.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-bundle-preview.full.json) | `gui-final/ancient_bundle`：13 |
| 卡牌包馈赠：子流程返回 | [ancient-bundle-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-returned.full.json) | `gui-final/ancient_bundle`：16 |
| 卡牌包馈赠：前进后地图 | [ancient-bundle-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-bundle-proceeded.full.json) | `gui-final/ancient_bundle`：19 |
| 馈赠后嵌套奖励：初始画面 | [ancient-nested-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-nested-initial.full.json) | `gui-final/ancient_nested`：0 |
| 馈赠后嵌套奖励：馈赠选项就绪 | [ancient-nested-choices-ready.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-nested-choices-ready.full.json) | `gui-final/ancient_nested`：6 |
| 馈赠后嵌套奖励：选择馈赠后 | [ancient-nested-after-choice.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-nested-after-choice.full.json) | `gui-final/ancient_nested`：10 |
| 馈赠后嵌套奖励：子流程返回 | [ancient-nested-returned.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-nested-returned.full.json) | `gui-final/ancient_nested`：18 |
| 馈赠后嵌套奖励：前进后地图 | [ancient-nested-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/ancient-nested-proceeded.full.json) | `gui-final/ancient_nested`：21 |

### 12：普通事件样本

| 分支／状态 | 完整 full JSON | 来源／下标 |
| --- | --- | --- |
| 深渊浴场翻页：初始画面 | [event-basic-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-basic-initial.full.json) | `gui-final/event_basic`：0 |
| 深渊浴场翻页：地图覆盖 | [event-basic-map.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-basic-map.full.json) | `gui-final/event_basic`：4 |
| 深渊浴场翻页：首项选择后新页面 | [event-basic-after-first-choice.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-basic-after-first-choice.full.json) | `gui-final/event_basic`：9 |
| 深渊浴场翻页：事件完成 | [event-basic-finished.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-basic-finished.full.json) | `gui-final/event_basic`：12 |
| 深渊浴场翻页：前进后地图 | [event-basic-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-basic-proceeded.full.json) | `gui-final/event_basic`：15 |
| 自助指南锁定项：初始画面 | [event-locked-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-locked-initial.full.json) | `gui-final/event_locked`：0 |
| 深渊浴场致死警告：初始画面 | [event-death-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-death-initial.full.json) | `gui-final/event_death`：0 |
| 升级选择：初始画面 | [event-upgrade-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-upgrade-initial.full.json) | `gui-final/event_upgrade`：0 |
| 升级选择：升级候选 | [event-upgrade-selection.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-upgrade-selection.full.json) | `gui-final/event_upgrade`：4 |
| 升级选择：升级比较 | [event-upgrade-upgrade-preview.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-upgrade-upgrade-preview.full.json) | `gui-final/event_upgrade`：7 |
| 升级选择：事件完成 | [event-upgrade-finished.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-upgrade-finished.full.json) | `gui-final/event_upgrade`：10 |
| 升级选择：前进后地图 | [event-upgrade-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-upgrade-proceeded.full.json) | `gui-final/event_upgrade`：13 |
| 事件奖励：初始画面 | [event-reward-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-reward-initial.full.json) | `gui-final/event_reward`：0 |
| 事件奖励：奖励覆盖事件 | [event-reward-rewards.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-reward-rewards.full.json) | `gui-final/event_reward`：4 |
| 事件奖励：事件完成 | [event-reward-finished.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-reward-finished.full.json) | `gui-final/event_reward`：10 |
| 事件奖励：前进后地图 | [event-reward-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-reward-proceeded.full.json) | `gui-final/event_reward`：13 |
| 战斗后恢复事件：初始画面 | [event-dummy1-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-initial.full.json) | `gui-final/event_dummy1`：0 |
| 战斗后恢复事件：进入战斗 | [event-dummy1-combat.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-combat.full.json) | `gui-final/event_dummy1`：4 |
| 战斗后恢复事件：战斗刚结束 | [event-dummy1-combat-ended.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-combat-ended.full.json) | `gui-final/event_dummy1`：9 |
| 战斗后恢复事件：战后药水奖励 | [event-dummy1-post-combat-rewards.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-post-combat-rewards.full.json) | `gui-final/event_dummy1`：12 |
| 战斗后恢复事件：恢复父事件 | [event-dummy1-resumed.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-resumed.full.json) | `gui-final/event_dummy1`：16 |
| 战斗后恢复事件：前进后地图 | [event-dummy1-proceeded.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-dummy1-proceeded.full.json) | `gui-final/event_dummy1`：19 |
| Trial 确认框边界：初始画面 | [event-trial-initial.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-trial-initial.full.json) | `gui-final/event_trial`：0 |
| Trial 确认框边界：第一次拒绝 | [event-trial-declined.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-trial-declined.full.json) | `gui-final/event_trial`：4 |
| Trial 确认框边界：第二次拒绝的确认框 | [event-trial-confirmation.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-trial-confirmation.full.json) | `gui-final/event_trial`：7 |
| Trial 确认框边界：取消确认后返回 | [event-trial-confirmation-canceled.full.json](2026-11-03-get-observation-shop-ancient-event-examples/event-trial-confirmation-canceled.full.json) | `gui-final/event_trial`：10 |

## 实际验证结果

- 16 类夹具分三批完成：gui 的六类商店、gui-remaining 的长对话、gui-final 的其余两类先古及七类事件；各通过用例都完成局间清理。前两批整体报告仍为 failed，仅最后一批九类的报告整体 passed，不将它们描述为一次全套通过。
- 通过用例共 276 次真实 MCP 调用，另有 1 次受门控的文件测试入口 prepare_test_event_victory，只用于把隔离战斗中的怪物生命设为可击杀并加入原生 Thunderclap，后续击杀仍经公开出牌工具；不属于公开工具功能。
- 82 份导出 JSON 与其原始 structuredContent 逐对象一致，均通过当前 observation_details 校验；全部相邻截图存在，MCP 文字 JSON 与 structuredContent 逐次一致。source manifest 与核对统计位于本地证据目录。
- Mod DLL 未变，三个自有 GUI PID 145144、146260、146594 均已退出；未安装正式 Mod。

## 验证边界与下一步

- 本轮只收录当前稳定交互页及实际遇到的只读过渡状态。商店 opening/closing、不可读价格、金币不足、Sozu 禁药水、Lord's Parasol 等其他组合仍以实现和目标源码为依据，没有新采所有分支。
- 先古之民的其他移除、多附魔、变牌与结果确认结构已由[选牌阶段](2026-11-02-get-observation-selections.md)核验；此轮不重跑所有遗物和角色的组合。对话夹具选择一段原生长对话，DebugOption 仅替换首项馈赠，未伪造工具返回。
- 普通事件示例覆盖通用字段及不同后续交互，不穷举目标版本全部事件、文本和随机分支。致死警告页仅采样，没有执行致死动作；确认框仅取消，未结束测试对局。建筑师、未知专属布局和第三方事件另行处理。
- full 不自动读取悬停内容或未来选项。卡牌奖励必须先打开候选，宝箱必须先显示遗物，未展开内容不由本轮样本补齐。新摘要设计还须遵循[可见信息边界](../observation.md)。
- 采样脚本的两次失败均保留：首批在先古之民关闭牌组后误选 disabled 选项；第二批在初始只读过渡页错误断言已可选择。修正仅针对脚本按已有 available_actions 有界等待，不改变生产代码、不自动重发失败动作。详情见本地 `.tmp/2026-11-03-observation-interactions-review-report.md`。
- 没有修改生产代码、参数或预设，没有重新运行 Python／C# 全套测试、构建或正式安装。下一步依据这些 full 样本讨论 10–12 组 summary 及必要的信息补齐，确认后才实现；13–17 组继续待选，get_observation 整体不核销。
