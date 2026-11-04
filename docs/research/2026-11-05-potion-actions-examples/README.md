# 修复后的药水与地图返回

这里保存真实 MCP 完整返回，供需要核对字段时查看。处理结果见[用户审阅说明](../2026-11-04-use-potion-review.md)，构建、测试及未验证范围见[开发实施记录](../2026-11-05-potion-actions-implementation.md)。

每份文件保留原参数对应的 full/default 和事件，没有截取或改写。参数、原始来源行号（从 0 开始）及 SHA-256 见[清单](manifest.json)。槽位禁用／隐藏等情况为隔离测试注入，不表示自然游玩的发生频率。

| 情况 | 完整返回 |
| --- | --- |
| 其他槽禁用时，瓶中精灵仍记录使用 | [get_observation → read](journal_boundary-01-get_observation.full.json)、[get_observation → read](journal_boundary-03-get_observation.full.json)、[end_turn → player_ready](journal_boundary-04-end_turn.full.json)、[get_observation → read](journal_boundary-05-get_observation.full.json) |
| 地图为 covered，顶栏仍可读取 | [get_observation → read](map_context-03-get_observation.full.json) |
| 其他槽禁用时正常记录获得药水 | [use_potion → player_ready](obtained_boundary-04-use_potion.full.json) |
| 隐藏药水不记录，恢复后不回放 | [get_observation → read](journal_hidden-01-get_observation.full.json)、[get_observation → read](journal_hidden-03-get_observation.full.json)、[end_turn → player_ready](journal_hidden-04-end_turn.full.json)、[get_observation → read](journal_hidden-06-get_observation.full.json) |
| 具体错误及直接继续操作 | [use_potion → invalid_request](basic-03-use_potion.json)、[use_potion → invalid_request](basic-04-use_potion.json)、[use_potion → invalid_request](basic-05-use_potion.json)、[use_potion → invalid_request](basic-06-use_potion.json)、[use_potion → invalid_request](basic-07-use_potion.json)、[use_potion → illegal_action](basic-10-use_potion.json)、[use_potion → illegal_action](basic-15-use_potion.json)、[use_potion → illegal_action](basic-20-use_potion.json)、[use_potion → illegal_action](basic-25-use_potion.json)、[use_potion → illegal_action](basic-30-use_potion.json)、[end_turn → player_ready](basic-33-end_turn.full.json)、[use_potion → player_ready](basic-35-use_potion.full.json)、[use_potion → player_ready](basic-36-use_potion.full.json) |
| 牌组／牌堆／地图遮挡时拒绝 | [use_potion → illegal_action](covered-06-use_potion.json)、[end_turn → illegal_action](covered-07-end_turn.json)、[use_potion → illegal_action](covered-16-use_potion.json)、[end_turn → illegal_action](covered-17-end_turn.json) |
| 选牌期间误用药后直接继续选牌 | [use_potion → choice_required](skill-03-use_potion.full.json)、[use_potion → illegal_action](skill-05-use_potion.json)、[select_card → player_ready](skill-06-select_card.full.json) |
| 原生取消仍要求读取当前状态 | [use_potion → action_canceled](cancel-03-use_potion.full.json)、[use_potion → observation_required](cancel-04-use_potion.json) |
| 地图上连续用药和丢弃，中间不查看 | [get_observation → read](noncombat_map-01-get_observation.full.json)、[get_observation → read](noncombat_map-08-get_observation.full.json)、[use_potion → action_completed](noncombat_map-10-use_potion.full.json)、[use_potion → action_completed](noncombat_map-11-use_potion.full.json)、[discard_potion → action_completed](noncombat_map-12-discard_potion.full.json)、[get_observation → read](noncombat_map-13-get_observation.full.json) |
| 向商人投掷 | [use_potion → action_completed](merchant-03-use_potion.full.json) |
| 向假商人投掷后进入战斗 | [use_potion → observation_required](fake_merchant-01-use_potion.json)、[use_potion → player_ready](fake_merchant-04-use_potion.full.json) |
| 本槽不能点击、其他槽仍可使用 | [inspect_targets → read](slot_interaction-04-inspect_targets.full.json)、[use_potion → illegal_action](slot_interaction-05-use_potion.json)、[use_potion → player_ready](slot_interaction-06-use_potion.full.json)、[inspect_targets → illegal_action](slot_interaction-10-inspect_targets.json)、[use_potion → player_ready](slot_interaction-11-use_potion.full.json) |

共选取 46 份完整返回；原始报告包括 38 次成功用例，涉及 37 类不同配置。补测会重复部分情形，不把执行次数当作不同场景数。
