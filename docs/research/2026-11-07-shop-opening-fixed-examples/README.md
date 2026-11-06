# 商店打开修复后返回示例

十五份真实完整返回：十四份full、一份default。调用、原始证据行及SHA-256见[manifest](manifest.json)，实现和验证范围见[实施记录](../2026-11-07-shop-opening-recovery-implementation.md)。图像块均为零。

| 场景 | 返回 |
| --- | --- |
| 普通打开与default重新打开 | [full](inventory.full.json)、[default](inventory.default.json) |
| 已打开被拒，直接合法关闭 | [具体原因](already-open.full.json)、[关闭成功](close-after-rejection.full.json) |
| 地图／牌组覆盖 | [地图](map-covered.full.json)、[牌组](deck-covered.full.json) |
| 删牌选择中误用，直接取消 | [具体原因](selection-covered.full.json)、[取消成功](cancel-after-rejection.full.json) |
| 战斗中误用，直接结束回合 | [无商店](no-shop.full.json)、[结束回合成功](turn-after-rejection.full.json) |
| 假商人打开 | [full](fake.full.json) |
| 阳伞自动购物的删牌选择，直接选牌 | [具体原因](parasol-selection.full.json)、[选牌成功](parasol-select-after-rejection.full.json) |
| 阳伞流程结束后重新打开 | [full](parasol-reopen.full.json) |
| 首次没有观察许可 | [仍须观察](no-permission.full.json) |

修复前[十份审阅样本](../2026-11-07-open-shop-examples/README.md)保持原样，记录原问题，不代表当前错误契约。
