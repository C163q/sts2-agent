# proceed典型完整返回

23份真实stdio MCP完整structuredContent，22份full、一份default，均无图片。包含拒绝后关闭商店被要求观察的close_shop回执，其余为proceed。参数、来源与SHA-256见[manifest.json](manifest.json)。

场景含义、问题和证据范围见[审阅记录](../2026-11-06-proceed-review.md)。终章使用全新进度独立进程；resumed-event样本是在战斗已自动恢复父事件后离开，不冒充由奖励页proceed触发恢复的实测。错误样本保留修复前笼统原因和许可丢失行为。

| 完整 JSON | 场景 | 工具 |
| --- | --- | --- |
| [reward-skip.full.json](reward-skip.full.json) | 奖励页Skip打开地图 | `proceed` |
| [reward-empty.default.json](reward-empty.default.json) | 奖励领完后Proceed，default | `proceed` |
| [nested-return.full.json](nested-return.full.json) | 子奖励返回父页面 | `proceed` |
| [treasure-skip.full.json](treasure-skip.full.json) | 宝箱Skip放弃遗物 | `proceed` |
| [treasure-collected.full.json](treasure-collected.full.json) | 宝箱领取后前进 | `proceed` |
| [rest.full.json](rest.full.json) | 休息后离开火堆 | `proceed` |
| [tent.full.json](tent.full.json) | 帐篷仍有选项时离开 | `proceed` |
| [shop.full.json](shop.full.json) | 关闭商品页后离开商店 | `proceed` |
| [event.full.json](event.full.json) | 普通事件完成后前进 | `proceed` |
| [ancient.full.json](ancient.full.json) | 先古之民完成后前进 | `proceed` |
| [divination.full.json](divination.full.json) | 占卜完成后前进，无附图 | `proceed` |
| [next-act.full.json](next-act.full.json) | Boss奖励前进至下一幕MapRoom | `proceed` |
| [resumed-event.full.json](resumed-event.full.json) | 已自动恢复的父事件前进 | `proceed` |
| [architect-entry.full.json](architect-entry.full.json) | 第三幕Boss奖励进入建筑师 | `proceed` |
| [run-won.full.json](run-won.full.json) | 建筑师最后前进，run_won | `proceed` |
| [combat-rejected.full.json](combat-rejected.full.json) | 战斗中没有前进按钮 | `proceed` |
| [shop-rejected.full.json](shop-rejected.full.json) | 商品页未关闭的拒绝 | `proceed` |
| [rest-rejected.full.json](rest-rejected.full.json) | 火堆尚未操作的拒绝 | `proceed` |
| [ancient-rejected.full.json](ancient-rejected.full.json) | 先古之民尚未完成的拒绝 | `proceed` |
| [divination-rejected.full.json](divination-rejected.full.json) | 占卜尚未完成的拒绝 | `proceed` |
| [dialogue-rejected.full.json](dialogue-rejected.full.json) | 建筑师还应推进对白时拒绝proceed | `proceed` |
| [result-rejected.full.json](result-rejected.full.json) | 结算页应使用run_result_option | `proceed` |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后合法关闭商店被要求观察 | `close_shop` |
