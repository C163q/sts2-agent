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
| 展示／悬停分离、共用读取及相关场景 | [display_readers](../../tests/game/data/gui_suite_display_readers.json) |
| 原生上下文、媒体故障与跨场景响应 | [native_responses](../../tests/game/data/gui_suite_native_responses.json) |
| 原生测试路由门控 | [native_dispatch](../../tests/game/data/gui_suite_native_dispatch.json) |
| 卡牌 Affliction、附魔、手牌 HUD 与浏览预设 | [card_formats](../../tests/game/data/gui_suite_card_formats.json) |
| 战斗对象静态／完整级别、对象筛选、不可悬停提示及错误续接 | [combatant_presets](../../tests/game/data/gui_suite_combatant_presets.json) |
| 查看错误说明、已有许可保留及零能量出牌拒绝后结束回合 | [inspection_errors](../../tests/game/data/gui_suite_inspection_errors.json) |
| 跨场景上下文、顶栏帮助、UI 来源筛选与摘要 | [ui_context](../../tests/game/data/gui_suite_ui_context.json) |
| 候选升级模式与不支持反馈 | [selection_upgrades](../../tests/game/data/gui_suite_selection_upgrades.json) |
| 生成牌、奖励牌及公开加入去向 | [card_additions](../../tests/game/data/gui_suite_card_additions.json) |
| default 公共空值规则及图片 | [default_presets](../../tests/game/data/gui_suite_default_presets.json) |
| 战斗、顶栏、附魔与观察预设 | [observation_presets](../../tests/game/data/gui_suite_observation_presets.json) |
| 完整候选、附魔、描边及各种选择摘要 | [selection_observations](../../tests/game/data/gui_suite_selection_observations.json) |
| 地图／牌组／牌堆覆盖时的顶栏 | [top_bar_views](../../tests/game/data/gui_suite_top_bar_views.json) |
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
