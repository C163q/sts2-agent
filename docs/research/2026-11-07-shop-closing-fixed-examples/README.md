# 商店关闭修复后返回示例

十五份真实完整JSON：十四份full、一份default。调用、原始证据行及SHA-256见[manifest](manifest.json)，实现和边界见[实施记录](../2026-11-07-shop-closing-recovery-implementation.md)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 普通关闭、default重新关闭 | [full](inventory.full.json)、[default](inventory.default.json) |
| 假商人关闭 | [full](fake.full.json) |
| 阳伞流程结束后关闭 | [full](after-automatic-purchase.full.json) |
| 页面已关闭被拒，直接重新打开 | [具体原因](already-closed.full.json)、[打开成功](open-after-rejection.full.json) |
| 地图／牌组覆盖 | [地图](map-covered.full.json)、[牌组](deck-covered.full.json) |
| 删牌选择覆盖，直接取消 | [具体原因](selection-covered.full.json)、[取消成功](cancel-after-rejection.full.json) |
| 子奖励覆盖，直接继续奖励 | [具体原因](reward-covered.full.json)、[前进成功](proceed-after-rejection.full.json) |
| 战斗中误用，直接结束回合 | [无商店](no-shop.full.json)、[结束回合成功](turn-after-rejection.full.json) |
| 阳伞的删牌选择覆盖 | [具体原因](parasol-selection.full.json) |

首次无许可仍要求观察，修复前[十二份审阅样本](../2026-11-07-close-shop-examples/README.md)保留了相同错误结构及旧问题。子奖励由测试夹具注入召唤铃铛触发，属于流程边界验证。
