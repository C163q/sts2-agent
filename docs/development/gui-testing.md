# 复用进程的图形测试

图形套件在一个独立游戏窗口中运行多个测试局，默认每个用例新开一局，同例步骤显式共享该局。步骤通过真实 stdio MCP 和原生游戏操作验证；测试设施不属于公开玩法工具。当前版本及依赖见[项目 README](../../README.md#当前版本与前提)。

## 准备与执行

先按[构建与准备指南](roundtrip.md#前提与构建)编译并准备隔离运行时。更新 `.tmp/roundtrip/runtime/` 前停止使用它的旧测试实例；此操作不安装正式 Mod，正式游戏无须退出。

在仓库根目录使用已安装[MCP 依赖](mcp.md#安装与游戏前提)的 Python 执行：

```sh
.tmp/mcp-venv/bin/python scripts/gui_suite.py --output .tmp/gui-suite-example
```

`--output` 必须尚不存在。默认使用 [gui_suite_smoke.json](../../tests/game/data/gui_suite_smoke.json)，当前用例和步骤以该清单为准。失败立即停止，不自动重试动作；保留现场证据后关闭本次拥有的进程。

专项清单通过 `--suite` 指定，例如：

```sh
.tmp/mcp-venv/bin/python scripts/gui_suite.py --suite tests/game/data/gui_suite_selection_upgrades.json --output .tmp/gui-selection-upgrades
```

| 专项 | 清单 |
| --- | --- |
| 架构组合回归与四项契约样例采集 | [architecture_refactor](../../tests/game/data/gui_suite_architecture_refactor.json) |
| 药水静态／完整预设、原槽位筛选与显示边界 | [potion_inspection](../../tests/game/data/gui_suite_potion_inspection.json) |
| 遗物静态图标状态、原下标对照、错误续接及专项验证 | [relic_inspection](../../tests/game/data/gui_suite_relic_inspection.json) |
| 展示／悬停分离、共用读取及相关场景 | [display_readers](../../tests/game/data/gui_suite_display_readers.json) |
| 原生上下文、媒体故障与跨场景响应 | [native_responses](../../tests/game/data/gui_suite_native_responses.json) |
| 原生测试路由门控 | [native_dispatch](../../tests/game/data/gui_suite_native_dispatch.json) |
| 手牌的牌堆计数与 HUD 标签／隐藏边界 | [hand_pile_counts](../../tests/game/data/gui_suite_hand_pile_counts.json) |
| 结束回合拒绝恢复、已有牌可见移动、洗牌隐私与自动出牌 | [turn_transitions](../../tests/game/data/gui_suite_turn_transitions.json) |
| 单张出牌回执、拒绝恢复及原生连续出牌行为调研 | [play_card_review](../../tests/game/data/gui_suite_play_card_review.json) |
| 公开批量出牌、逐张结果、原生选择续接与跨局清理 | [play_cards](../../tests/game/data/gui_suite_play_cards.json) |
| 药水明确拒绝恢复、单槽交互、自动用药／获得事件与地图覆盖 | [potion_recovery](../../tests/game/data/gui_suite_potion_recovery.json)；[验证记录](../research/2026-11-05-potion-actions-implementation.md) |
| 丢弃药水的槽位、自动药水、奖励腾槽、错误续接及覆盖边界 | [discard_potion_review](../../tests/game/data/gui_suite_discard_potion_review.json)；[核验记录](../research/2026-11-05-discard-potion-development-notes.md) |
| 丢弃请求状态、选牌排队、防重复、后续事件及局间清理 | [potion_discard_queue](../../tests/game/data/gui_suite_potion_discard_queue.json) |
| 药水使用回执、选择／战斗外边界、拒绝恢复与跨槽事件核验 | [use_potion_review](../../tests/game/data/gui_suite_use_potion_review.json)；现状证据及已知缺口见[审阅记录](../research/2026-11-04-use-potion-review.md) |
| 卡牌 Affliction、附魔、手牌 HUD 与浏览预设 | [card_formats](../../tests/game/data/gui_suite_card_formats.json) |
| 战斗对象静态／完整级别、对象筛选、不可悬停提示及错误续接 | [combatant_presets](../../tests/game/data/gui_suite_combatant_presets.json) |
| 查看错误说明、已有许可保留及零能量出牌拒绝后结束回合 | [inspection_errors](../../tests/game/data/gui_suite_inspection_errors.json) |
| 跨场景上下文、顶栏帮助、UI 来源筛选与摘要 | [ui_context](../../tests/game/data/gui_suite_ui_context.json) |
| 候选升级模式与不支持反馈 | [selection_upgrades](../../tests/game/data/gui_suite_selection_upgrades.json) |
| 选牌查看的具体拒绝、安全续接、覆盖边界及卡包／结果说明 | [selection_review](../../tests/game/data/gui_suite_selection_review.json)；[核验与实施](../research/2026-11-05-selection-inspection-implementation.md) |
| 点击候选的选中／取消、替换、自动提交、预览、未知身份、滚动及拒绝恢复 | [select_card_review](../../tests/game/data/gui_suite_select_card_review.json)；[实施与验证](../research/2026-11-05-selection-feedback-implementation.md) |
| 选择按钮的确认、返回、放弃、跳过、整包、奖励替代及明确拒绝后续接 | [selection_option_review](../../tests/game/data/gui_suite_selection_option_review.json)；[审阅](../research/2026-11-05-selection-option-review.md)。grid_manual 包含双重门控的禁用按钮／过期优先检查，人工扰动只用于验证拒绝，不代表自然游玩出现过同类静止按钮 |
| 奖励预设与 ID 筛选、基础观察对照、拒绝续接及旧领取流程 | [reward_inspection_review](../../tests/game/data/gui_suite_reward_inspection_review.json)；[实施与验证](../research/2026-11-05-reward-inspection-presets-implementation.md) |
| 开箱／分步领取、空箱、输入边界与拒绝恢复现状 | [loot_treasure_review](../../tests/game/data/gui_suite_loot_treasure_review.json)；[开发依据](../research/2026-11-06-loot-treasure-development-notes.md)。当前保留拒绝后许可丢失与笼统原因的基线断言 |
| 宝箱预设、空值、覆盖拒绝、纯读取续接与显示／悬停边界 | [treasure_inspection_review](../../tests/game/data/gui_suite_treasure_inspection_review.json)；[实施验证](../research/2026-11-06-treasure-inspection-presets-implementation.md)。显示扰动双重门控，finally 和局间重置恢复 |
| 领取结果、满槽、互斥、嵌套、追回、拒绝续接与滚动失败边界 | [claim_reward_review](../../tests/game/data/gui_suite_claim_reward_review.json)；[修复记录](../research/2026-11-05-claim-reward-recovery-implementation.md)。滚动失败使用双重门控的原生按钮禁用扰动，finally 与局间重置恢复 |
| 地图旅行的到达回执、拒绝续接、滚动后失败与赐福鹿角 | [travel_review](../../tests/game/data/gui_suite_travel_review.json)；[修复与验证](../research/2026-11-05-travel-recovery-implementation.md) |
| 地图关闭的最小结果、具体拒绝与许可续接、占卜无图像依赖及旧独立检查 | [close_map_review](../../tests/game/data/gui_suite_close_map_review.json)；[关闭结果实施](../research/2026-11-05-close-map-results-implementation.md)。combat 的第二步在同一就绪战斗中运行旧独立验证器 |
| 地图分类、深度裁剪、飞鞋、幕起点、双 Boss、覆盖隐藏及拒绝续接 | [map_summary](../../tests/game/data/gui_suite_map_summary.json)；[地图交付](../research/2026-11-05-map-summary-implementation.md) |
| 原生眼睛切换、紧凑结果、重复目标、保留选择／预览及拒绝后续接 | [selection_view_review](../../tests/game/data/gui_suite_selection_view_review.json)；[审阅与定稿](../research/2026-11-05-selection-view-review.md)。grid 用例包含双重门控的隐藏／禁用眼睛检查，扰动后恢复按钮和快照，不代表自然游玩出现了此种状态 |
| 生成牌、奖励牌及公开加入去向 | [card_additions](../../tests/game/data/gui_suite_card_additions.json) |
| default 公共空值规则及图片 | [default_presets](../../tests/game/data/gui_suite_default_presets.json) |
| 战斗、顶栏、附魔与观察预设 | [observation_presets](../../tests/game/data/gui_suite_observation_presets.json) |
| 完整候选、附魔、描边及各种选择摘要 | [selection_observations](../../tests/game/data/gui_suite_selection_observations.json) |
| 地图／牌组／牌堆覆盖时的顶栏 | [top_bar_views](../../tests/game/data/gui_suite_top_bar_views.json) |
| 卡牌浏览关闭的具体拒绝、许可续接与最小返回 | [card_view_close](../../tests/game/data/gui_suite_card_view_close.json) |
| 牌堆筛选、静态观察、空堆反馈和拒绝续接 | [pile_inspection](../../tests/game/data/gui_suite_pile_inspection.json) |
| 牌组筛选、静态观察、升级排序、最小关闭和拒绝续接 | [deck_inspection](../../tests/game/data/gui_suite_deck_inspection.json) |
| 可浏览奖励、历史及原生滚动容器 | [browsable_content](../../tests/game/data/gui_suite_browsable_content.json) |

套件各自拥有 IPC、日志、截图和测试存档，使用已准备的运行时，不使用 Steam、正式存档或 `.tmp/live/ipc`。同一套件的新局共享测试进度和进程缓存，不能替代要求全新进程／进度的结算解锁或 `--check-*` 检查；这些场景按[单实例指南](roundtrip.md)执行。

## 清单与同局步骤

清单格式示例：

```json
[
  {
    "name": "combat_chain",
    "scenarios": {"play": "armaments_free", "potion": "skill"},
    "steps": [
      {"name": "actions", "verifier": "verify_action_observations.py", "args": []},
      {"name": "next_turn", "verifier": "verify_suite_continuation.py", "args": []}
    ]
  },
  {
    "name": "smith",
    "scenarios": {"rest": "smith"},
    "steps": [
      {"name": "upgrade", "verifier": "verify_rest_site.py", "args": ["--scenario", "smith"]}
    ]
  }
]
```

每个顶层用例配置场景并创建一次新局；步骤连续执行，不重建或重置状态。各步骤默认新连 MCP 并先取得自己的许可。编排器核对同局步骤的 PID、会话及局身份，下一用例须有新的局身份。

- `scenarios` 使用[场景白名单](../../tests/game/data/test_scenarios.json)，对应 `run_roundtrip.py --<名称>-scenario`；`ending` 拒绝用于复用套件。
- 用例名唯一，不能为保留名 `game`；每例步骤名也须唯一。用例和步骤名只接受字母、数字、下划线及连字符。
- `verifier` 和允许的场景组合由 [suite.py 的 SUPPORTED_VERIFIERS 与 load_cases](../../tests/game/suite.py)校验；不能仅把旧脚本写进清单就认定支持进程复用。
- `args` 只接受 `[]` 或 `["--scenario", "场景名"]`；`--scenario` 是验证器的断言分支，须配合对应夹具。报告和 IPC 路径由套件管理；成功步骤必须产生非空 JSON 证据。

修改场景或验证器时，同步上述注册表、清单及测试。完整组合不在文档重复维护；优先复用已有清单，特殊组合查看验证器及夹具源码。

## 生命周期与证据

套件通过 `STS2_AGENT_TEST_MODE=1` 与 `STS2_AGENT_TEST_SUITE=1` 双重门控提供仅文件 IPC 可用的 `configure_test_run`、`reset_test_run`、`get_test_session`。前两项需要最新状态令牌，配置只允许在没有对局的主菜单执行。

局间使用原生 `NGame.ReturnToMainMenu`／`RunManager.CleanUp`，等待夹具任务结束、释放引用并移除专用补丁。无法确认清理完成时将进程标为不可复用并关闭；不直接重写玩家状态伪造新局。这不是正常游玩的“放弃对局”工具。

| 输出 | 内容 |
| --- | --- |
| `report.json` | 总结果、PID／会话、局身份、耗时及本次测试 Mod 的 SHA-256 |
| `suite.json` | 本次采用的清单副本 |
| `game/` | 自有进程的 IPC、完整日志与测试存档 |
| `<用例>/<步骤>/` | `verifier.log`、`evidence.json`、配置、截图及该步骤游戏日志 |

不得删除失败目录后原地重跑覆盖证据；每次使用新目录，启动失败也保留日志。套件只关闭自己启动的 PID；验证器超时则清理其进程组中的 MCP 子进程。

历史执行数量、阶段耗时和样本见[套件验证记录](../research/2026-11-01-gui-suite.md)及各专项记录；清单列出用例不表示当前代码已运行通过。

## 浏览覆盖顶栏

[top_bar_views 清单](../../tests/game/data/gui_suite_top_bar_views.json)检查覆盖页、选择、换幕及弹窗下的实际顶栏。`check_test_top_bar` 只在双重门控下开放，测试隐藏／透明／离屏、标签来源与隐藏数字，UI 扰动在 finally 中恢复；证据见[顶栏核验](../research/2026-11-02-top-bar-visibility.md)。

## 可浏览列表与滚动内容

[browsable_content 清单](../../tests/game/data/gui_suite_browsable_content.json)检查完整列表、画外奖励定位、滚动不截断及隐藏／透明／内层裁剪／水平越界边界。读取不改变滚动位置，原生检查结束须恢复 UI；证据见[浏览内容审查](../research/2026-11-02-browsable-content-audit.md)。

当前游戏基线禁用 View Run。历史页测试仅在双重门控下生成隔离历史、实例化原生 `NRunHistory` 并加入标记内容，不改变正常入口，也不代表正常游玩可点击该页。`verify_run_result_observation.py --scenario history` 复用此夹具；死亡与完整胜利解锁流程仍独立启动，范围见[结算观察验证](../research/2026-11-03-result-observation-implementation.md)。


native_responses 的媒体故障夹具仅在 testMode 与 suite 同时开启时可用，局间重置会清除故障。它检查默认文件媒体、显式无图请求、图像失败时动作回执仍成功，以及实际 UI 已变化但旧文件媒体生成失败时的执行事实。注入故障不代表自然游戏已出现相同故障；完整结算仍须使用独立进度实例。

`display_readers` 的不可悬停遗物通过双重测试门控夹具关闭鼠标与控制器入口，恢复后继续原生页面读取；这是人为注入的验证条件，不表示已观察到自然游玩中的同类遗物。

架构组合的验证证据与适用范围见[验收记录](../research/2026-11-04-refactor-stage-7.md)，筛选、上下文和不可悬停的完整公开返回见[JSON 样例](../research/2026-11-04-refactor-contract-examples/README.md)。
