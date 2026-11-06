# inspect_shop 实际返回示例

基线efdab40，Mod0.73.0／MCP0.75.0／schema42。以下为真实stdio MCP完整公开JSON，没有改写字段或拼接预期值；[manifest](manifest.json)保存调用参数、来源行及SHA-256。文件名描述隔离场景，不为工具增加假商人身份等观察字段。

| 样本 | 调用 |
| --- | --- |
| [inventory.full.json](inventory.full.json) | `inspect_shop({"preset": "full"})` |
| [inventory.default.json](inventory.default.json) | `inspect_shop({"preset": "default"})` |
| [after-card.full.json](after-card.full.json) | `inspect_shop({"preset": "full"})` |
| [closed-first.full.json](closed-first.full.json) | `inspect_shop({"preset": "full"})` |
| [map-covered.full.json](map-covered.full.json) | `inspect_shop({"preset": "full"})` |
| [selection-covered.full.json](selection-covered.full.json) | `inspect_shop({"preset": "full"})` |
| [used-removal.full.json](used-removal.full.json) | `inspect_shop({"preset": "full"})` |
| [courier.full.json](courier.full.json) | `inspect_shop({"preset": "full"})` |
| [courier-restocked.full.json](courier-restocked.full.json) | `inspect_shop({"preset": "full"})` |
| [hidden-price.full.json](hidden-price.full.json) | `inspect_shop({"preset": "full"})` |
| [fake-merchant.full.json](fake-merchant.full.json) | `inspect_shop({"preset": "full"})` |
| [full-potions.full.json](full-potions.full.json) | `inspect_shop({"preset": "full"})` |
| [reward-covered.full.json](reward-covered.full.json) | `inspect_shop({"preset": "full"})` |
| [nested-return.full.json](nested-return.full.json) | `inspect_shop({"preset": "full"})` |
| [parasol-complete.full.json](parasol-complete.full.json) | `inspect_shop({"preset": "full"})` |
| [no-shop.full.json](no-shop.full.json) | `inspect_shop({"preset": "full"})` |

说明及建议见[审阅记录](../2026-11-06-inspect-shop-review.md)。
