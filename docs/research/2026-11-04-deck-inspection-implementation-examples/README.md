# 牌组改造后的真实返回

14 份完整 JSON 均来自真实 stdio MCP。调用参数、来源条目和校验值见 [manifest](manifest.json)，核对基线及验证范围见[实施记录](../2026-11-04-deck-inspection-implementation.md)。源证据保存在仓库根目录的 `.tmp/2026-11-04-deck-implementation/gui/`，不纳入 Git。

| 场景 | 完整返回 |
| --- | --- |
| 已打开牌组的基础观察 | [full](observation.full.json)、[default](observation.default.json)、[summary](observation.summary.json) |
| 开启升级、按费用降序的基础摘要 | [observation-upgraded.summary.json](observation-upgraded.summary.json) |
| 专用详情仍提供正文与共享解释 | [inspect.full.json](inspect.full.json) |
| 有效、重复及无效 ID 混合筛选 | [完整](filtered.full.json)、[摘要](filtered.summary.json) |
| 空筛选；原页面仍保留完整列表 | [empty.summary.json](empty.summary.json) |
| 关闭牌组回到战斗 | [closed-visible.full.json](closed-visible.full.json) |
| 关闭上层牌组回到地图 | [closed-to-map.full.json](closed-to-map.full.json) |
| 事件／建筑师背景中的牌组 | [事件](event-observation.full.json)、[建筑师](epilogue-observation.full.json) |
| 锻造选牌时拒绝打开牌组，保留旧许可 | [selection-rejected.full.json](selection-rejected.full.json) |
| 不补观察，直接取消选牌成功；此文件为 selection_option 回执 | [selection-continued.full.json](selection-continued.full.json) |

基础观察的 full/default 卡牌分别是 face_full／face_default，均没有正文和悬停解释；summary 再省略稀有度、卡池等。sort.by／descending 与 view_upgrades 表示当前页面设置，不因输出筛选或省略参数而重置。

样本来自现有隔离游戏夹具，永久牌组均为 10 张，不能当作长牌组或全部附魔外观的新实测。关闭结果的 full 指调用参数，返回内容始终是 actions_only。采样后补充的矛盾保证校验和普通 CLI 禁用棋盘图像，不改变本目录中这些成功返回。
