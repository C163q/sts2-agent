# buy_item 审阅返回示例

十八份真实完整JSON：十七份full、一份default。调用、原始证据行及SHA-256见[manifest](manifest.json)，核验范围与失败说明见[开发依据](../2026-11-07-buy-item-development-notes.md)，问题和候选设计见[审阅](../2026-11-07-buy-item-review.md)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 普通卡牌／遗物／药水购买 | [卡牌full](buy-card.full.json)、[遗物full](buy-relic.full.json)、[药水default](buy-potion.default.json) |
| 药水满栏，原生领取失败 | [failure_space](full-potion-failure.full.json) |
| 添水阻止获得药水 | [failure_forbidden](forbidden-potion-failure.full.json) |
| 送货员补货后用新ID购买 | [新商品](courier-replacement.full.json) |
| 金币不足被拒，随后关闭被要求观察 | [当前通用错误](insufficient-gold.full.json)、[后续操作](after-gold-rejection.full.json) |
| 删牌启动／取消／确认 | [启动](removal-start.full.json)、[取消](removal-canceled.full.json)、[确认](removal-confirmed.full.json) |
| 遗物子奖励及结束 | [初次返回](reward-start.full.json)、[结束子奖励](reward-finished.full.json) |
| 遗物变牌及确认 | [初次返回](transform-start.full.json)、[确认](transform-confirmed.full.json) |
| 购买变牌后，观察再选牌仍过期 | [首批失败](transform-stale.full.json) |
| 假商人购买 | [full](fake-purchase.full.json) |
| 无效商品ID | [通用错误](unknown-id.full.json) |

删除、奖励和变牌的后续返回没有purchase_result，这是当前行为；pending只是候选方案。变牌首批及诊断批次失败，最终补测正常完成，不能据此声称稳定性问题已修复。Calling Bell、Astrolabe和Cauldron为测试夹具注入，验证购买副流程，不代表普通商品配置。
