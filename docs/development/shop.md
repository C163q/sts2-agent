# 商店

适用于 Mod `0.26.0`、MCP `0.22.0`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。当前支持实际单人，正常商店和假商人使用同一组工具；工具操作原生界面，不直接改金币或发放商品。

## 打开、观察与详情

先调用 `get_observation()`。商人界面返回 `scene: "shop"`，`shop.view: "merchant"`，`shop.items: null`；商品页尚未打开时不读取库存。`open_shop()` 点击当前商人，打开商品页；`close_shop()` 点击商品页左侧返回按钮。两者都返回完整观察和 `transition`，可以按[MCP 许可规则](mcp.md#调用和错误语义)从成功完整结果继续操作，不自动前进。

商品页的基础观察包含所有当前可见商品，卡牌按牌组 `summary` 规则提供名称、牌型、稀有度、实际外观卡池、能量和星星费用，不附送正文。遗物和药水只提供可见名称。示例为字段节选：

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
  },
  "available_actions": ["buy_item", "close_shop"]
}
```

`items` 的示例只保留一项，不代表完整库存。`kind` 为 `card`、`relic`、`potion` 或 `card_removal`；`position` 表示原生布局中的类别和从 0 开始的槽位。正常布局通常有 5 张角色牌、2 张无色牌、3 个遗物、3 瓶药水及删牌服务，但接口按真实界面读取，不固定数量。

`inspect_shop()` 在商品页已打开时，一次返回全部当前商品的完整说明。卡牌在 `card` 内增加 `description`、`hover_tips`；遗物、药水和可用删牌服务在商品对象上增加这两个字段。关闭时调用会拒绝，不代为打开。详情只读，不消耗随机数，不授予新动作许可。

地图、选牌、奖励或其他界面覆盖时，`shop.status: "covered"`，`view/items/open/back/proceed` 均为 `null`；不会穿透读取或购买。原生展开/收回动画期间 `view` 为 `opening` / `closing`，不输出商品和可用按钮。

## 购买与补货

`buy_item({"item_id":0})` 点击一件当前观察中的商品。`item_id` 必须为非负整数；工具检查快照、当前商品、价格与原生交互状态。购买顺序自行决定，不连买其他商品，也不自动使用或丢弃药水。

`price` 来自屏幕显示，已包含原生折扣；价格不可读时 `price/affordable` 为 `null`，该项不可购买。`affordable` 表示当前金币是否足够，`enabled` 还要求界面和交易流程就绪。基础观察不推测剩余空间是否足够；满药水栏仍可尝试原生购买，失败时商品及金币保留，结果例如：

```json
{
  "purchase_result": {"item_id":10,"status":"failure_space"},
  "transition": {"stop_reason":"action_completed","complete":true,"events":[]}
}
```

这同样是完整结果的节选。`purchase_result` 仅在本次请求中已得到原生结果时存在，状态可以是 `success`、`failure_space`、`failure_forbidden`、`failure_gold`、`failure_out_of_stock` 或 `canceled`。遇到选牌/奖励时先返回，不等待依赖后续输入的父任务。

没有补货效果时，买完的条目从 `items` 消失；删牌成功后仍保留打叉条目，`used: true`、`enabled: false`、`price/affordable: null`，不输出隐藏价格和悬停说明。“送货员”补货后同一 `position` 会出现新的 `id`，必须使用新观察中的 ID，不能按位置重复购买旧商品。卡牌补货后的特价标记遵循原生规则。

## 删牌、自动购买与前进

购买删牌服务会打开原生牌组选择，继续使用 `inspect_selection`、`select_card`、`selection_option`。普通删牌可取消，取消不扣钱，也不使用服务；选择后须确认，成功删除后才扣钱并标记已使用。不能用 `close_shop` 绕过选牌页。

“领主阳伞”由游戏自动展开商品页，免费尝试购买初始商品，最后进入不可取消的免费删牌。接口跟踪该原生任务；自动购买或原生药水瞄准期间不接受额外商店动作，遇到选择或奖励立即返回，后续复用对应工具。送货员补入的新货不再由阳伞循环购买；药水满栏时原生领取可失败。接口不自行重演阳伞效果。

`proceed()` 只在商品页已关闭、商店原生前进按钮可用时点击，通常打开地图，不选择节点。`inspect_map()` / `close_map()` 沿用现有地图查看；不旅行。

## 添水

在商店可用 `inspect_relics()` 查看已持有遗物的说明，包括添水。添水（Sozu）通过原生 `ShouldProcurePotion` 禁止持有者获得药水。普通购买会返回 `purchase_result.status: "failure_forbidden"`，不扣金币，商品保留。阳伞免费购买也不能绕过限制：药水不会入栏，未领取商品保留；其他购买及最后删牌照常进行。

大锅等打开的药水奖励使用原生奖励流程。与满栏拒绝不同，添水阻止获取时，本版本仍会消耗被点击的药水奖励行，返回 `reward_result.status: "not_obtained"`，药水不会入栏。详情见[奖励结果](rewards.md#领取与后续选择)。接口不补发药水、不替玩家改写遗物效果；`enabled` 表示可以点击尝试，不保证能获得物品。添水本身不禁止使用或丢弃已持有的药水。

## 恶臭药水与假商人

恶臭药水仅在商品页关闭、商人可以作为原生目标时使用；打开商品页后不可投掷。相关可见药水槽位增加 `usable_here` 布尔提示，实际播放弹跳动画时可出现 `bouncing: true`；不据此附送药水效果。通过 `inspect_potions()` 查看效果，`inspect_targets({"potion_slot":0})` 查询目标，再用 `use_potion({"potion_slot":0,"target_id":"merchant"})` 投掷。

本版本对普通商人投掷会获得药水定义的金币；对假商人投掷会触发事件战斗，工具等待新战斗的可行动边界。假商人提供的货物、价格、原生补货和折扣规则直接沿用游戏；观察不额外标注隐藏身份。该事件其余通用选项不在本接口范围。

## 验证入口

按[隔离运行指南](roundtrip.md)准备独立实例，然后分别运行：

```sh
python3 scripts/run_roundtrip.py --windowed --shop-scenario basic
```

```sh
.tmp/mcp-venv/bin/python scripts/verify_shop.py --scenario basic --report .tmp/shop-check/basic.json
```

报告和截图目录必须全新，只能对新建隔离实例运行。源码证据、已验证场景和限制见[商店核对记录](../research/2026-10-31-shop.md)。
