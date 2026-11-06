# 商店新预设与购买上下文的实际JSON

Mod0.74.0／MCP0.76.0／schema43。以下为最终DLL的真实stdio MCP完整公开返回，未拼接预期字段；[manifest](manifest.json)记录参数、来源行和SHA-256。display场景来自受保护UI扰动；Calling Bell嵌套商品为测试注入。

| 样本 | 工具与参数 |
| --- | --- |
| [inventory.full.json](inventory.full.json) | `inspect_shop({"preset": "full"})` |
| [inventory.default.json](inventory.default.json) | `inspect_shop({"preset": "default"})` |
| [inventory.summary.json](inventory.summary.json) | `inspect_shop({"preset": "summary"})` |
| [observation.summary.json](observation.summary.json) | `get_observation({"preset": "summary"})` |
| [id-filter.summary.json](id-filter.summary.json) | `inspect_shop({"preset": "summary", "item_ids": [9999, 0]})` |
| [relics.full.json](relics.full.json) | `inspect_shop({"preset": "full", "kinds": ["relic"]})` |
| [empty.full.json](empty.full.json) | `inspect_shop({"preset": "full", "item_ids": [], "kinds": []})` |
| [after-card.full.json](after-card.full.json) | `inspect_shop({"preset": "full"})` |
| [map-covered.full.json](map-covered.full.json) | `inspect_shop({"preset": "full"})` |
| [closed-first.full.json](closed-first.full.json) | `inspect_shop({"preset": "full"})` |
| [used-removal.full.json](used-removal.full.json) | `inspect_shop({"preset": "full"})` |
| [courier-restocked.full.json](courier-restocked.full.json) | `inspect_shop({"preset": "full"})` |
| [fake-merchant.summary.json](fake-merchant.summary.json) | `inspect_shop({"preset": "summary"})` |
| [nested-return.full.json](nested-return.full.json) | `inspect_shop({"preset": "full"})` |
| [parasol-complete.full.json](parasol-complete.full.json) | `inspect_shop({"preset": "full"})` |
| [offscreen.full.json](offscreen.full.json) | `inspect_shop({"preset": "full", "item_ids": [0]})` |
| [price-offscreen.full.json](price-offscreen.full.json) | `inspect_shop({"preset": "full", "item_ids": [0]})` |
| [no-hover-card.full.json](no-hover-card.full.json) | `inspect_shop({"preset": "full", "item_ids": [0]})` |
| [no-hover-relic.full.json](no-hover-relic.full.json) | `inspect_shop({"preset": "full", "item_ids": [7]})` |
| [blocked.summary.json](blocked.summary.json) | `inspect_shop({"preset": "summary"})` |
| [hidden-gold.full.json](hidden-gold.full.json) | `inspect_shop({"preset": "full"})` |
| [hidden-top-bar.full.json](hidden-top-bar.full.json) | `inspect_shop({"preset": "full"})` |

[实施记录](../2026-11-06-shop-inspection-presets-implementation.md)说明验证过程和边界；[原审阅样本](../2026-11-06-inspect-shop-examples/README.md)保持原样。
