# 商店

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持单人正常商店和假商人，使用同一组工具操作原生界面。

含 null 的字段说明与示例按 full 表达；默认输出的空值处理见[公共预设](mcp.md#输出预设)。

页面主体的展示进度见[共用展示状态](observation.md#页面主体的展示状态)，按钮启用状态按当前操作条件判断。

## 打开、观察与详情

基础观察的商人界面返回 `scene: "shop"`，`shop.view: "merchant"`，`shop.items: null`；商品页尚未打开时不读取库存。`open_shop()` 点击当前商人，打开商品页；`close_shop()` 点击商品页左侧返回按钮。两者都返回[精简动作回执](mcp.md#动作返回格式)，可以按[MCP 许可规则](mcp.md#调用和错误语义)从满足续接条件的成功结果继续操作，不自动前进。

打开与关闭分别检查当前页面和按钮，拒绝时说明原因并提示对应工具：

| 操作 | 主要拒绝条件 |
| --- | --- |
| open_shop | 商品页已打开、页面覆盖、待处理选择、活动或动画尚未结束 |
| close_shop | 商品页已关闭、页面覆盖、待处理选择或奖励、活动尚未结束 |

两者的检查分别由 `OpenUnavailableReason`、`CloseUnavailableReason` 集中维护，与按钮 enabled、available_actions 和实际执行共用。原生点击、对局／持有者复核及动画等待由 `ShopViewRequest` 处理；购买走独立流程，详情使用独立可读性判断。

有效快照下的明确点击前拒绝保留已有许可，并返回 `recovery:choose_legal_action`，可直接改用当前合法操作。点击后失败、过期或未知结果按[公共恢复规则](mcp.md#调用和错误语义)重新读取。开关页面的验证范围见[打开商店](../research/2026-11-07-shop-opening-recovery-implementation.md)与[关闭商店](../research/2026-11-07-shop-closing-recovery-implementation.md)记录。

商品页的基础观察包含所有当前已展示商品（含视口外位置），卡牌采用无正文的共用 face 格式，提供名称、牌型、稀有度、实际外观卡池、显示费用及允许读取的外观，不附送效果解释。遗物和药水只提供可见名称。示例为字段节选：

```json
{
  "scene": "shop",
  "shop": {
    "status": "visible",
    "view": "inventory",
    "items": [
      {
        "id": 0,
        "kind": "card",
        "position": "character_card:0",
        "price": 75,
        "affordable": true,
        "enabled": true,
        "card": {
          "name": "Break",
          "type": "Attack",
          "rarity": "uncommon",
          "visual_card_pool": "ironclad",
          "energy_cost": "1",
          "star_cost": null
        },
        "on_sale": false
      }
    ],
    "open": null,
    "back": {"enabled": true},
    "proceed": null
  }
}
```

get_observation 的 summary 使用[共用卡牌摘要规则](observation.md#mcp-输出预设)精简商品卡牌，商品 ID 与购买字段保持在外层。full/default 继续提供稀有度与卡池，均不附送正文；完整效果由 inspect_shop 提供。

示例节选一项商品。`kind` 为 `card`、`relic`、`potion` 或 `card_removal`；`position` 表示原生布局中的类别和从 0 开始的槽位。正常布局通常有 5 张角色牌、2 张无色牌、3 个遗物、3 瓶药水及删牌服务，但接口按真实界面读取，不固定数量。

`inspect_shop({preset?, item_ids?, kinds?})`在已打开的商品页返回同次scene、screen、shop和摘要top_bar。top_bar复用[摘要顶栏](observation.md#mcp-输出预设)，包含gold、potion_slots、deck_count、relic_count；所有预设使用相同字段范围，未知值按各自null规则处理。药水槽保留名称、空槽和实际UI提示，遗物详情通过inspect_relics查看。

| 参数／预设 | 内容 |
| --- | --- |
| default | 默认；完整说明，按公共规则省略普通null |
| full | 完整说明和普通null；卡牌description／hover_tips在card内，其他商品说明在商品行内 |
| summary | 与get_observation.summary.shop共用静态格式；保留购买字段、名称和共用卡牌摘要，省略正文、悬停解释及不可悬停note |
| item_ids | 外层商品整数ID列表；省略或null全部，[]为空，去重并保持原生顺序 |
| kinds | card/relic/potion/card_removal分类列表；省略或null全部，[]为空，与item_ids取交集 |

找不到的ID相对完整当前列表判断，合并为errors:[{code:"item_ids_not_found",item_ids:[...]}]，仍返回其他有效条目；有效ID仅被kinds排除时不报缺失。筛选保留页面按钮与顶栏，商品自身的id/position仍可用于定位。所有响应先完整校验再精简／筛选，空筛选也拒绝坏结构。

商品和价格读取取消视口截断，保留真实隐藏、透明、裁剪与缺货边界；点击继续核对实际可交互范围。页面可读性独立于购买Ready，自动交易的输入阻挡期间可读取静态库存，enabled为false。详情和available_actions共用InspectionUnavailableReason，错误说明区分无商店、关闭、覆盖与动画；明确只读拒绝保留已有许可，首次失败不生成许可。

悬停能力分别核对原生Hitbox鼠标入口与slot控制器有效焦点；买不起或只禁用点击仍可保留说明。确实不可悬停时，卡牌保留直接画在牌面的正文，full为hover_tips:null；其他未用商品为description:null、hover_tips:[]，full/default均附notes.hover_tips_unavailable.sources:["shop.items.<原ID>"]。筛选同步裁剪note，summary省略该note。已用删牌服务维持无说明字段。

详情为只读操作，成功后可直接购买。关闭时先open_shop，地图／牌组覆盖先关闭相应页面，选牌／奖励覆盖先处理当前输入。原生右键详情和升级对照列在[用户后续待办](TODO.md)，当前工具不提供view_upgrades。

地图、选牌、奖励或其他界面覆盖时，`shop.status: "covered"`，`view/items/open/back/proceed` 均为 `null`；不会穿透读取或购买。原生展开/收回动画期间 `view` 为 `opening` / `closing`，不输出商品和可用按钮。

## 购买与补货

`buy_item({"item_id":0})` 点击一件当前观察中的商品。`item_id` 必须为非负整数；工具检查快照、当前商品、价格与原生交互状态。每次购买后根据回执决定下一项；药水槽位通过独立药水工具操作。

`price` 来自屏幕显示，已包含原生折扣；价格不可读时 `price/affordable` 为 `null`，该项不可购买。`affordable` 表示当前金币是否足够，`enabled` 还要求界面和交易流程就绪。基础观察不推测剩余空间是否足够；满药水栏仍可尝试原生购买，失败时商品及金币保留，结果例如：

```json
{
  "purchase_result": {"item_id":10,"status":"failure_space"},
  "transition": {"stop_reason":"action_completed","complete":true,"events":[]}
}
```

这同样是完整结果的节选。`purchase_result` 包含请求的item_id及status：success、failure_space、failure_forbidden、failure_gold、failure_out_of_stock、canceled或pending。购买尚未结束而进入受支持的选牌／奖励输入时返回pending，继续使用当前页面工具；扣款时点由原生流程决定。后续动作提供自己的回执和期间事件，不携带购买终态。

购买页面、单品拒绝及商品enabled／available_actions使用共用检查；无效或已替换ID、已用删牌、不可交互、价格不可读、金币不足及覆盖各有具体提示。明确点击前拒绝保留已有许可，可直接纠正或选择其他合法操作；进入原生点击后，领取失败通过purchase_result表达。读取完整响应时先检查结果ID在Int32非负范围内且与请求一致，再精简及续接；错误响应清除许可。

schema 44 及以上的正常完成与已识别输入边界包含purchase_result；超时、中断、人工处理或胜负终局等购买状态未知的边界可省略，旧schema维持可省略结果的兼容读取。choice_required在金币计数动画结束后再经过稳定间隔返回，仍允许父购买／卡牌任务暂停等待玩家。实现入口、验证及边界见[购买反馈修复](../research/2026-11-07-shop-purchase-feedback-implementation.md)。

没有补货效果时，买完的条目从 `items` 消失；删牌成功后仍保留打叉条目，`used: true`、`enabled: false`、`price/affordable: null`，不输出隐藏价格和悬停说明。“送货员”补货后同一 `position` 会出现新的 `id`，必须使用新观察中的 ID，不能按位置重复购买旧商品。卡牌补货后的特价标记遵循原生规则。

## 删牌、自动购买与前进

购买删牌服务会打开原生牌组选择，继续使用 `inspect_selection`、`select_card`、`selection_option`。普通删牌可取消，取消不扣钱，也不使用服务；选择后须确认，成功删除后才扣钱并标记已使用。不能用 `close_shop` 绕过选牌页。

“领主阳伞”由游戏自动展开商品页，免费尝试购买初始商品，最后进入不可取消的免费删牌。接口跟踪该原生任务；自动购买或原生药水瞄准期间不接受额外商店动作，遇到选择或奖励立即返回，后续复用对应工具。送货员补入的新货不再由阳伞循环购买；药水满栏时原生领取可失败。接口不自行重演阳伞效果。

`proceed()` 只在商品页已关闭、商店原生前进按钮可用时点击，通常打开地图；旅行使用 travel_to_node。地图查看与关闭使用 `inspect_map()` / `close_map()`。

## 添水

在商店可用 `inspect_relics()` 查看已持有遗物的说明，包括添水。添水（Sozu）通过原生 `ShouldProcurePotion` 禁止持有者获得药水。普通购买会返回 `purchase_result.status: "failure_forbidden"`，不扣金币，商品保留。阳伞免费购买也不能绕过限制：药水不会入栏，未领取商品保留；其他购买及最后删牌照常进行。

大锅等打开的药水奖励使用原生奖励流程。与满栏拒绝不同，添水阻止获取时，本版本仍会消耗被点击的药水奖励行，返回 `reward_result.status: "not_obtained"`，药水不会入栏。详情见[奖励结果](rewards.md#领取与后续选择)。`enabled` 表示当前可以点击尝试，获取结果通过 reward_result 表达。添水本身不禁止使用或丢弃已持有的药水。

## 恶臭药水与假商人

恶臭药水仅在商品页关闭、商人可以作为原生目标时使用；打开商品页后不可投掷。相关可见药水槽位增加 `usable_here` 布尔提示，实际播放弹跳动画时可出现 `bouncing: true`；不据此附送药水效果。通过 `inspect_potions()` 查看效果，`inspect_targets({"potion_slot":0})` 查询目标，再用 `use_potion({"potion_slot":0,"target_id":"merchant"})` 投掷。

本版本对普通商人投掷会获得药水定义的金币；对假商人投掷会触发事件战斗，工具等待新战斗的可行动边界。假商人提供的货物、价格、原生补货和折扣规则直接沿用游戏；观察不额外标注隐藏身份。该事件其余通用选项不在本接口范围。

## 验证入口

商店采样见 [ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs)，开关页面与购买分别见 [GameAdapter.Shop](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)和 [GameAdapter.Purchase](../../src/Sts2Agent/Adapter/GameAdapter.Purchase.cs)，公开结果见 [shop_details](../../src/sts2_mcp/output/shop_details.py)。

按[隔离运行指南](roundtrip.md)准备独立实例，然后分别运行：

```sh
python3 scripts/run_roundtrip.py --windowed --shop-scenario basic
```

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_shop --scenario basic --report .tmp/shop-check/basic.json
```

报告和截图目录必须全新，只能对新建隔离实例运行。源码证据、已验证场景和限制见[商店核对记录](../research/2026-10-31-shop.md)。
