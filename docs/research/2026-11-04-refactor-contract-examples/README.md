# 架构重构的真实工具返回样例

本目录收录第 7 阶段组合 GUI 中实际 MCP `structuredContent` 的 **26 份完整公开 JSON**，仅统一缩进，未人工增删返回字段。text 内容与 structuredContent 在验证器中核对一致。每份样例的实际请求、源证据位置／条目下标、源文件与样例 SHA-256、测试 Mod 哈希见 [manifest.json](manifest.json)；总体结果和限制见[验收记录](../2026-11-04-refactor-stage-7.md)。

## 测试条件

- 使用隔离存档及 IPC，中文 UI、英语工具输出；样例来自测试夹具，不是玩家存档或自然对局回放。
- 战斗样例由 basic／skill 夹具启动，再通过原生获取流程添加 Anchor、Lantern、Pen Nib。未筛选遗物顺序为 Burning Blood、Anchor、Lantern、Pen Nib，对应位置 0–3。
- 不可悬停样例由双重门控测试接口暂时关闭 Pen Nib holder 的鼠标与控制器焦点入口；保留图标和 0 计数。采集后恢复入口，再读取地图与牌组覆盖下的详情。没有据此声称自然游玩存在这一状态。
- 选牌样例来自火堆选择锻造、切换原生升级显示和选中卡牌后的比较。比较页本身没有升级复选框，再请求 view_upgrades 会成功返回当前数据及 `upgrade_view_unavailable`，对应错误保留在完整样例中。
- `full` 文件保留其工具范围内的空值；名称带 `default/summary` 的文件保留对应实际预设。各调用独立采样，完整上下文来自各自快照。

## 四项接口调整

| 调整 | 重点样例 | 核对方式 |
| --- | --- | --- |
| 筛选引用原列表 | [Lantern 筛选](relics.filtered.full.json) | 只返回一个遗物，顶层与提示仍引用原位置 2 |
| null 全部、[] 为空 | 下表五组筛选样例 | null 与同工具未筛选 full 完整相同；[] 只清空选择的内容，保留上下文及工具要求的其他字段 |
| 详情补上下文 | [手牌](hand.full.json)、[目标](targets.full.json)、[地图下药水](potions.map-context.default.json)、[遗物](relics.full.json) | 四个原缺口均含 scene/screen；地图下 room scene 与 screen.view 各自表达 |
| 不可悬停保留静态数据 | [full](relics.hover-unavailable.full.json)、[default](relics.hover-unavailable.default.json)、[summary](relics.hover-unavailable.summary.json)、[筛选后 full](relics.hover-unavailable-filtered.full.json) | full 正文为 null；default 省略普通 null；summary 无正文／提示／缺失 note；筛选后 note 仍用 relics.3，与结果映射 [0,3] 对照 |

| 工具／参数 | 未筛选 full | null | [] |
| --- | --- | --- | --- |
| inspect_relics.relic_indices | [完整](relics.full.json) | [全部](relics.filter-null.full.json) | [空](relics.filter-empty.full.json) |
| inspect_hand.card_ids | [完整](hand.full.json) | [全部](hand.filter-null.full.json) | [空](hand.filter-empty.full.json) |
| inspect_ui.sources | [完整](ui.full.json) | [全部](ui.filter-null.full.json) | [空](ui.filter-empty.full.json) |
| inspect_combatants.sources | [完整](combatants.full.json) | [全部](combatants.filter-null.full.json) | [空](combatants.filter-empty.full.json) |
| inspect_selection.card_ids | [完整](selection.full.json) | [全部](selection.filter-null.full.json) | [空](selection.filter-empty.full.json) |

另含[战斗基础观察](observation.combat.full.json)、[地图下遗物](relics.map-context.default.json)、[地图下 UI](ui.map-context.default.json)和[锻造比较完整数据](selection.upgrade-comparison.full.json)。所有文件都属于 manifest 中同一次通过的组合运行及同一 Mod 构建。

## 证据与重现范围

源记录在项目根目录下 `.tmp/2026-11-04-refactor-stage-7/gui/`，不纳入 Git；已提交的 JSON 与 manifest 保留返回内容及出处。可按[图形测试指南](../../development/gui-testing.md)运行 `gui_suite_architecture_refactor.json` 重新采集相同场景。新的会话、卡牌控制 ID 或 UI 时间可能不同，不承诺逐字节重现历史值；字段语义以[当前接口指南](../../development/README.md)为准。
