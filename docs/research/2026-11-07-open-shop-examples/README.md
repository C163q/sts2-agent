# open_shop 审阅返回示例

基线与验证范围见[开发核验](../2026-11-07-open-shop-development-notes.md)，问题及建议见[审阅](../2026-11-07-open-shop-review.md)。

十份实际完整JSON：九份full、一份default；其中merchant为打开前get_observation对照，其余为open_shop或拒绝后的操作。样例保留审阅基线的错误行为，尚未修复。调用、原始证据行及SHA-256见[manifest](manifest.json)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 打开前的商人，尚未返回库存 | [merchant.full.json](merchant.full.json) |
| 普通打开 | [inventory.full.json](inventory.full.json) |
| 重新打开，default | [inventory.default.json](inventory.default.json) |
| 假商人 | [fake.full.json](fake.full.json) |
| 阳伞自动购物及删牌完成后，关闭并重新打开 | [parasol-reopen.full.json](parasol-reopen.full.json) |
| 首次未观察 | [no-permission.full.json](no-permission.full.json) |
| 商品页已打开，重复调用 | [already-open.full.json](already-open.full.json) |
| 重复打开被拒后，合法close_shop仍要求观察 | [after-rejection.full.json](after-rejection.full.json) |
| 地图覆盖 | [map-covered.full.json](map-covered.full.json) |
| 删牌选择覆盖 | [selection-covered.full.json](selection-covered.full.json) |

无商店、牌组覆盖及自动购物的选择覆盖使用相同公开错误，不重复导出；各自原生原因和执行证据保存在原始报告中。
