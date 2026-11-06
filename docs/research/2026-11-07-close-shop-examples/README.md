# close_shop 审阅返回示例

十二份真实完整JSON，十一份full、一份default；调用、原始证据行及SHA-256见[manifest](manifest.json)。审阅基线及范围见[开发核验](../2026-11-07-close-shop-development-notes.md)，问题与建议见[审阅](../2026-11-07-close-shop-review.md)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 普通关闭 | [inventory.full.json](inventory.full.json) |
| 重新打开再关闭，default | [inventory.default.json](inventory.default.json) |
| 假商人关闭 | [fake.full.json](fake.full.json) |
| 阳伞自动购物及删牌完成后关闭 | [after-automatic-purchase.full.json](after-automatic-purchase.full.json) |
| 普通删牌取消后关闭 | [after-selection.full.json](after-selection.full.json) |
| 购买子奖励处理后关闭 | [after-rewards.full.json](after-rewards.full.json) |
| 首次未观察 | [no-permission.full.json](no-permission.full.json) |
| 商品页已关闭，重复调用 | [already-closed.full.json](already-closed.full.json) |
| 被拒后，合法open_shop仍要求观察 | [after-rejection.full.json](after-rejection.full.json) |
| 地图覆盖 | [map-covered.full.json](map-covered.full.json) |
| 删牌选择覆盖 | [selection-covered.full.json](selection-covered.full.json) |
| 子奖励覆盖 | [reward-covered.full.json](reward-covered.full.json) |

无商店、牌组和阳伞选择覆盖的公开错误与上述相同，不重复导出；各自原生原因和执行证据保存在报告中。子奖励用夹具注入的召唤铃铛触发，不代表普通商品配置。样本保留当前待修复的错误行为。
