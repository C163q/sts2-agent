# inspect_deck 完整返回示例

对应[场景核验与候选设计](../2026-11-04-inspect-deck-review.md)。共 27 份完整公开 JSON：26 份真实 stdio MCP 返回，1 份按契约整理的空牌组。不是从长列表中截取几张牌后称为完整返回。

调用参数、证据文件及从 0 开始的条目位置、内容校验值和版本基线统一见 [manifest.json](manifest.json)。source 位于仓库根目录下的 `.tmp/2026-11-04-inspect-deck-review/`，不纳入 Git；导出的 JSON 则保留在本目录。全部原有 null、空列表、错误和上下文字段均保留，不拼装未实际返回的房间内容。

| 场景／用途 | 完整返回 |
| --- | --- |
| 战斗首次打开，full | [combat.full.json](combat.full.json) |
| 同页 default | [combat.default.json](combat.default.json) |
| 同页 summary | [combat.summary.json](combat.summary.json) |
| 开启升级预览，full | [upgraded.full.json](upgraded.full.json) |
| 获得顺序／类型／费用／名称降序 | [获得](sort-obtained.full.json)、[类型](sort-type.full.json)、[费用](sort-cost.full.json)、[名称](sort-name.full.json) |
| 战斗地图上叠加牌组 | [deck-over-map.full.json](deck-over-map.full.json) |
| 牌组打开时的基础观察，显示尚未提供牌组内容的现状 | [covered-observation.full.json](covered-observation.full.json) |
| 事件／火堆／宝箱中的牌组 | [事件](event.full.json)、[火堆](rest.full.json)、[宝箱](treasure.full.json) |
| 奖励／商店／先古之民中的牌组 | [奖励](rewards.full.json)、[商店](shop.full.json)、[先古之民](ancient.full.json) |
| 占卜中的牌组；scene 仍为 event | [divination.full.json](divination.full.json) |
| 建筑师对话背景中的牌组 | [epilogue.full.json](epilogue.full.json) |
| 主菜单拒绝 | [error-main-menu.full.json](error-main-menu.full.json) |
| 选牌覆盖时拒绝打开牌组 | [error-selection.full.json](error-selection.full.json) |
| 上述拒绝后直接执行已知按钮，被要求重新观察；此文件是 selection_option 返回 | [error-after-rejection.full.json](error-after-rejection.full.json) |
| descending 缺少 sort_by；请求在本地拒绝 | [error-sort.full.json](error-sort.full.json) |
| 当前未支持 card_ids；请求在本地拒绝 | [error-unsupported-filter.full.json](error-unsupported-filter.full.json) |
| 事件打开牌组前的完整基础观察 | [event-before.full.json](event-before.full.json) |
| 关闭牌组后的返回；可与上项对照房间内容丢失 | [event-closed.full.json](event-closed.full.json) |
| 关闭牌组露出地图，但关闭返回缺少 map 数据 | [closed-to-map.full.json](closed-to-map.full.json) |
| 空牌组的成功结构；**实现整理，非 GUI 样本** | [constructed-empty.full.json](constructed-empty.full.json) |

四份降序排序样本都沿用先前开启的升级预览；不会因请求省略 view_upgrades 就恢复 false。后续关闭并从地图重新打开的牌组则恢复新页默认值。所有游戏样本都来自现有隔离测试夹具，永久牌组均为 10 张；不代表自然开局配置或长列表的新一轮验证。

普通卡牌的三种内容层级可直接比较前三份文件。以 Strike 为例，full 保留 star_cost／enchantment／affliction 的 null，default 去掉这些普通空值但保留正文；summary 为 id、name、type、energy_cost。附魔或 Affliction 实际存在时共享摘要也会保留，但这些新采样永久牌组没有该内容，不能据此声称实测了所有外观变体。

采样报告的失败与补采情况见主审阅记录；不要将来自前两批的有效单次返回误标为整批验证通过。参数错误、主菜单拒绝及选牌覆盖拒绝是预期样本，不是实现已修复的证据。
