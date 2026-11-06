# 商店购买修复后返回示例

二十份真实完整JSON：十九份full、一份default。调用、原始行与SHA-256见[manifest](manifest.json)，实现及边界见[实施记录](../2026-11-07-shop-purchase-feedback-implementation.md)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 普通卡牌／遗物／药水 | [卡牌](buy-card.full.json)、[遗物](buy-relic.full.json)、[药水default](buy-potion.default.json) |
| 药水满栏／添水限制 | [failure_space](full-potion-failure.full.json)、[failure_forbidden](forbidden-potion-failure.full.json) |
| 送货员的新商品 | [成功](courier-replacement.full.json) |
| 金币不足后直接关闭 | [具体原因](insufficient-gold.full.json)、[关闭成功](close-after-gold.full.json) |
| 无效ID后直接关闭 | [具体原因](unknown-id.full.json)、[关闭成功](close-after-unknown.full.json) |
| 删牌pending／取消／确认 | [启动](removal-start.full.json)、[取消](removal-canceled.full.json)、[确认](removal-confirmed.full.json) |
| 子奖励pending／结束 | [启动](reward-start.full.json)、[结束](reward-finished.full.json) |
| 变牌pending／确认 | [启动](transform-start.full.json)、[确认](transform-confirmed.full.json) |
| 假商人购买 | [成功](fake-purchase.full.json) |
| 价格不可读后直接关闭 | [具体原因](unreadable-price.full.json)、[关闭成功](close-after-price.full.json) |

pending只表示购买流程仍需处理当前输入，扣款时点依原生；后续动作没有购买终态字段，依自己的反馈及事件表达结果。注入Calling Bell、Astrolabe和Cauldron只用于副流程验证，不代表普通商品配置。原[十八份审阅样本](../2026-11-07-buy-item-examples/README.md)保持原样。
