# 复用进程的图形测试

图形套件通过一个独立的游戏窗口运行多个测试局，省去逐例重新启动游戏与加载资源的开销。默认每个用例新开一局；同一用例的多个步骤显式共享该局。步骤仍经过真实 stdio MCP 与原生游戏操作，原有断言保留。结算、历史、解锁和 `--check-*` 内嵌检查继续单独启动。

## 准备与执行

先按[构建与准备指南](roundtrip.md#前提与构建)构建 Mod，并运行 `prepare_roundtrip.py` 更新隔离运行时。此步骤不安装或更新正式游戏中的 Mod。停止使用同一隔离运行时的旧测试实例后再更新运行时；正式游戏无须退出。

在仓库根目录，使用已安装 [MCP 依赖](mcp.md#安装与游戏前提)的 Python 执行：

```sh
.tmp/mcp-venv/bin/python scripts/gui_suite.py --output .tmp/gui-suite-example
```

`--output` 必须尚不存在。默认清单是 [gui_suite_smoke.json](../../tests/game/data/gui_suite_smoke.json)：跨幕进入先古之民后的状态稳定、对话和选牌，详情或页面操作后直接行动，连续动作与同局续接、连续选牌、未结束选牌的清理、锻造、商店、奖励，以及附加奖励宝箱后接普通宝箱。最后两例检查测试补丁是否跨局残留。失败立即停止后续步骤和用例，保留证据，再关闭本次拥有的游戏进程；不会在失败现场自动重试动作。

每个套件有独立的 IPC、日志、截图和测试存档目录。游戏资产和 Mod 来自 `.tmp/roundtrip/runtime/`，不使用 Steam、正式存档或 `.tmp/live/ipc`。同一套件内的新局共享测试进度和进程缓存，不能替代要求全新进度或全新进程的测试。

## 清单与同局步骤

通过 `--suite <JSON 文件>` 指定清单。例如：

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

每个顶层用例配置场景并创建一次新局。它的所有步骤连续执行，不重建局，也不重置玩家状态；各步骤默认重新连接 MCP，先取得自己的观察许可。编排器检查同局步骤前后的 PID、游戏会话和局身份完全相同，下一用例则必须具有新的局身份。

`scenarios` 使用 [场景白名单](../../tests/game/data/test_scenarios.json)中的名称，与原 `run_roundtrip.py --<名称>-scenario` 对应；`ending` 明确拒绝。参数 `--scenario` 是验证脚本选择断言分支的参数，应与对应夹具一致。每个步骤必须有独立名称；用例名不能为保留的 `game`。`args` 目前只接受空列表或 `["--scenario", "场景名"]`，报告和 IPC 路径由框架管理；不会将 `--help` 的零退出视为完成测试，成功步骤必须产生非空 JSON 证据。

允许的验证器包括 `verify_action_observations.py`、`verify_kill_settling.py`、`verify_action_stability.py`、`verify_rest_site.py`、`verify_shop.py`、`verify_rewards.py`、`verify_treasure.py`，以及同局续接/保留选择的两个专用验证器。`verify_kill_settling.py --scenario energy` 配合 `play:energy_chain`，验证 `Bash → Dominate` 耗尽能量后，手牌描边完成渐隐且无需重新观察即可结束回合。`verify_selection_scene.py` 校验基础观察与选牌详情的场景一致性，场景参数为 `ancient_bundle`、`rest_smith`、`combat_discovery`、`event_deck` 或 `shop_remove`，分别配合 `ancient:bundle`、`rest:smith`、`play:discovery`、`selection:deck`、`shop:remove`。清单不接受尚未接入的脚本；不能把旧脚本简单加入清单后假定它支持复用。

`verify_action_stability.py` 的 `--scenario` 与 `play` 场景使用同名值：`anger`、`turbo`、`blade_dance`、`pommel_strike`、`bloodletting`、`gather_light`、`preview_draw`、`preview_messy`。前六项执行原生卡牌；后两项用防御触发测试夹具预置的原生抽牌堆预览，分别覆盖普通和七张牌的散列布局。验证器在动作返回后 0、0.25、0.75、1.5、3.5 秒采样底层观察，要求令牌始终等于回执令牌，并在不刷新 MCP 许可的情况下继续出牌；同时保留外部动作导致过期的反例检查。

`verify_observation_sources.py` 全程不调用 `get_observation`，验证成功详情和页面操作可以提供下一动作的状态：`--scenario map` 配合 `navigation:basic`，检查地图详情直接旅行及非法节点拒绝；`views` 配合 `play:pommel_strike`，检查关闭牌组/牌堆后直接结束回合及详情后出牌；`selection` 配合 `play:discovery`，检查切回选择后直接提交，以及查看战场时拒绝选择隐藏候选。三项均纳入默认冒烟集。

`verify_ancient_stability.py` 的 `travel` 和 `travel_action` 均配合 `navigation:boss1`，经过原生跨幕和地图旅行；前者从 `inspect_ancient` 续接，后者用原始回执中的夹具选项 ID 检查动作许可续接。两者保存旅行返回的精确状态，再采样九秒且不刷新 MCP 许可，要求令牌始终不变并能直接领取佩尔之血；同时检查外部操作使旧令牌过期、覆盖页及重复领取被拒绝。`direct` 配合 `ancient:tooth`，用于已构造房间的详情续接对照。`verify_ancients.py` 支持复用局及其 `ancient` 同名场景，对话和佩尔之牙多选纳入默认集。

`verify_map_presets.py` 逐项对照同一原生全图，检查默认结果兼容、`selectable` 优先、前瞻节点与子图边界连线，再直接选路或关闭地图后结束回合，全程不调用 `get_observation`。`flight` 配合 `navigation:basic`，检查无连线的飞鞋候选并纳入默认集；`combat` 配合 `navigation:combat`，先经原生选路进入战斗，再检查零候选；`entry` 配合 `navigation:boss1` 检查新幕未进入节点；`double` 配合 `navigation:double` 检查第二 Boss。验证器自行保存地图截图，参数不改变原生地图显示范围。

`verify_reward_alternatives.py` 的 `paels_wing`、`driftwood` 分别配合同名 `reward` 场景，并纳入默认集。通过真实遗物获取和奖励生成 hook，检查基础观察与详情中的献祭/重掷按钮、实际效果、候选刷新及旧 ID 拒绝；献祭两次后还保留原许可直接前进，重掷后检查跳过再打开不会恢复次数。动作后在数秒内只读采样，诊断读取不刷新 MCP 许可。两者分别测试，不代表双遗物组合已验证。

`verify_power_text.py` 配合 `turn:thieving_hopper`，验证原生偷窃草蜢从计数 5 到 1 的动态说明及最终逃跑，保存首回合完整 MCP 回执 `hopper-first-end-turn.json`。计数 5、4、1 时在独立实例内切换语言并触发原生悬停，保存中英文提示截图；测试专用入口不属于公开 MCP 工具，验证后恢复原语言。此场景纳入默认冒烟集；模板范围与限制见[状态说明验证](../research/2026-11-01-power-descriptions.md)。

`verify_hand_presets.py` 验证完整输出兼容、摘要字段、共享提示裁剪、重复及无效 ID、空筛选、读取前后 UI 令牌不变，以及读取后直接出牌/结束回合。`basic`、`stars`、`x_cost`、`card_names` 配合同名 `play` 场景；`selection` 配合 `play:armaments_free`，检查查看战场时保留导航说明、已离手的武装 ID 不再命中。`enchantments` 配合 `play:enchantments`，检查 Sharp、禁用 Swift、无数字 Clone、普通同名副本及第六张 `Defend+` 的 Spiral；另执行 18 项嵌入可见性、显示计数、置灰和身份边界检查。`basic` 与 `enchantments` 纳入默认集。附魔范围见[卡面附魔记录](../research/2026-11-01-card-enchantments.md)，Spiral 与安装版本核对见 [r9 记录](../research/2026-11-02-r9-enchantments.md)，参数范围见[手牌参数验证记录](../research/2026-11-01-hand-presets.md)。

`verify_selection_presets.py` 对照默认完整、显式完整和摘要结果，核对读取前后原生状态相同，并从摘要直接选择或确认。`hand_upgrade` 配合 `play:armaments_free`，包含眼睛隐藏与返回后查看，纳入默认集。其他场景：`discovery` 配合 `play:discovery`，`smith` 配合 `rest:smith`，`ancient_multi/ancient_transform/ancient_bundle/ancient_pandora` 分别配合 `ancient:multi/transform/bundle/pandora`，`paels_wing/driftwood` 配合同名 `reward` 场景，`grid/combat_pile/deck/hand` 分别配合 `selection:grid_scroll/combat_pile/deck/retain_one`。覆盖包内卡牌、各类预览、随机结果空值及奖励替代按钮；范围和证据见[选择预设验证记录](../research/2026-11-01-selection-presets.md)。

`verify_inventory_events.py` 验证物品与永久牌组的真实 MCP 回执。`smith/cook` 配合 `rest:smith/cook`，`upgrade/transform/enchant/remove` 配合同名 `event` 场景，`shop/reward/ancient` 配合各自 `basic` 场景，`rescue` 配合 `event:rescue`，`temporary` 配合 `play:armaments`。`visibility` 配合 `play:basic`，执行隐藏遗物／药水栏、隐藏后恢复不补发、永久附魔附加／清除、升级／降级及订阅释放检查，仅通过测试模式文件接口运行。`temporary` 验证战斗临时升级不被标记为永久变化；随机变牌只记录真正公开的入组结果。`enchant` 和 `visibility` 纳入默认集。范围与证据见[第二阶段记录](../research/2026-11-01-inventory-events.md)。

`verify_combat_resources.py` 核对能量／星星的公开端点、原生通知与实际数字刷新、精简回执及入战后直接续接。`spend/gain/turbo/stars/star_spend/choice` 配合 `play:basic/bloodletting/turbo/gather_light/star_spend/armaments`；`visibility` 配合 `play:basic`，执行局部标签隐藏、地图和战斗 UI 遮挡、滚动动画取消、恢复基线与订阅释放的测试模式检查；`reveal_visibility` 同样使用 `play:basic`，检查首次星星布局、隐藏、离屏和裁剪取消，以及后续公开基线。`fake_merchant` 配合 `shop:fake`，检查药水入战日志与随后出牌／结束回合；`selection_entry` 配合 `selection:combat_entry`，检查选择完成后父流程进入战斗的停止原因及抽牌日志。后两者纳入默认集。范围与证据见[第三阶段记录](../research/2026-11-01-combat-resource-events.md)。

## 生命周期与证据

`verify_companions.py` 的 `osty/blade/first` 分别配合 `play:companions_osty/companions_blade/companions_first`，验证奥斯提的友方身份、原生攻击、死亡与再召唤、成长，以及君王之剑的铸造、手牌外预览、攻击来源和公转期间令牌稳定。`checks/blade_checks` 分别使用前两个场景，经双重门控文件入口检查共享格挡、部分／完全格挡及伤害溢出、隐藏生命不补发、多剑身份、可悬停边界、消耗移除，并对照中英文原生悬停卡牌预览。独立夹具用原生命令构造初始场景，不修改正式存档；具体证据见[奥斯提与君王之剑记录](../research/2026-11-02-companions.md)。

`verify_permanent_cards.py` 的 `genetic/cost/enchant` 对应 `play:permanent_genetic/permanent_cost/permanent_enchant`，验证永久变量、基础能量费用及附魔数量变化的真实 MCP 回执和直接续接。遗传算法使用正常出牌，并打开永久牌组核对成长；费用及附魔场景用测试夹具回调调用原生修改入口，不声称游戏存在对应可叠加玩法。`checks` 配合 `play:permanent_genetic`，检查预览／临时值排除、隐藏取消、身份延后、升级抑制、异常释放和共享上限。默认清单包含遗传算法成长；范围和证据见[第五阶段记录](../research/2026-11-01-permanent-card-events.md)。

`verify_combat_handoff.py` 的 `play/selection/choice` 分别配合 `play:handoff_play/handoff_selection/handoff_choice`，`turn` 配合 `turn:handoff`，验证动作完成或选牌恢复后原生房间替换、新首回合日志、选择暂停与直接续接。`checks` 配合 `play:basic`，验证连续两次替换、旧订阅释放、ID 与手牌对应、同场回合不重建、隐藏标记、共享上限及异常释放。默认清单包含 `play`。夹具通过原生房间 API 构造交接，不代表某张原生卡牌具有换战斗效果；见[第七阶段记录](../research/2026-11-01-combat-handoff.md)。

`verify_damage_attribution.py` 的 `card/aoe/aoe_lethal/doom/potion` 配合 `play:minion_<场景>`，验证首领与随从的真实命中、致命来源和关联清理；`potion` 另需 `potion:basic`。`fog_natural/fog_thorns/fog_card/fog_cleanup` 配合同名 `play` 场景，分别验证活雾自然召唤后自爆、反伤击杀、玩家直接击杀和首领死亡清理。各活雾用例核对 `death_blow` 图标／数字与中英文原生悬停截图。`revival` 配合 `turn:revive`，通过原生死亡、重接、重复通知和新日志检查同一实例的生命周期。默认清单包含 `card`、`fog_natural` 和 `fog_thorns`；夹具与归因边界见[死亡来源核查](../research/2026-11-01-death-attribution.md)。

`verify_kill_settling.py --scenario phase` 同时配置 `turn:revive` 与 `play:kill_chain`，以原生复活战斗和 1 HP 目标检查死亡后的动作续接；只配置前者时，普通 Strike 不会击杀满血目标。

`verify_orb_events.py` 的 `play/checks` 均配合 `play:orbs`：前者通过真实 MCP 验证双重释放、扩槽、生成及无需额外观察的连续出牌；后者通过测试模式文件入口验证满槽自动激发、缩槽丢弃、隐藏／覆盖／离屏取消、不补发、入场连续操作、缓冲上限及作用域释放。`chain` 配合 `play:orb_chain`，通过原生 Tempest 在两槽位中生成三个球，验证连续生成及满槽激发。默认清单包含 `play`；原生边界检查会扰动隔离实例的 UI，不对外提供工具。见[第六阶段记录](../research/2026-11-01-orb-events.md)。

`verify_capacity.py` 验证最大能量、蜡制遗物熔化与充能球：`resources` 配合 `play:basic`，运行仅文件可用的原生容量／熔化嵌入检查；`wax_melt` 配合 `play:wax_melt`，验证真实 MCP 出牌回执及直接结束回合；`orbs` 和 `orb_visibility` 配合 `play:orbs`，使用故障机器人验证球序、激发、增槽、生成、暗球增长及图像／标签可见性。充能球游玩及熔化回执已纳入默认清单。夹具仅通过原生命令准备场景，图像扰动及无通知重绘仅用于隔离检查。范围与证据见[第四阶段记录](../research/2026-11-01-capacity-and-orbs.md)。

`verify_resource_events.py` 核对 HP、最大生命与金币事件能按捕获顺序还原实际顶栏变化，并检查精简回执及直接续接。场景对应：`event/rescue` 使用 `event:basic/rescue`，`rest/cook` 使用 `rest:basic/cook`，`shop` 使用 `shop:basic`，`reward` 使用 `reward:skip`，`ancient` 使用 `ancient:basic`，`potion_rest/potion_combat` 使用 `potion:noncombat_rest/fruit_combat`，`combat/visibility` 使用 `play:basic`，`entry` 使用 `navigation:combat`，`masks` 使用 `selection:deck`。`visibility` 执行嵌入可见性、持续隐藏、恢复基线与释放检查；`masks` 在保留原生选择页时打开原生卡牌详情及地图，验证遮挡期间资源不进入日志。两者只使用隔离测试入口。事件与烹饪场景纳入默认集，范围和证据见[资源事件第一阶段](../research/2026-11-01-run-resource-events.md)。

套件模式通过 `STS2_AGENT_TEST_MODE=1` 和 `STS2_AGENT_TEST_SUITE=1` 双重门控，提供仅文件 IPC 可用的 `configure_test_run`、`reset_test_run`、`get_test_session`。前两项需最新状态令牌；配置仅允许没有对局的主菜单。它们不属于公开 MCP 工具，也不改变玩法 JSON 或动作许可规则。旧的单用例启动命令继续有效。

局间使用游戏原生 `NGame.ReturnToMainMenu` / `RunManager.CleanUp`，等待夹具任务结束、释放夹具引用并移除专用 Harmony 补丁。不能确认清理完成时将进程标记为不可再用，并由套件关闭；不直接重写玩家状态伪造新局。该清理是测试设施，不是正常游玩的“放弃对局”接口。

输出包括：

- `report.json`：总结果、游戏启动次数、PID/会话、每局身份、配置/创建/步骤/清理耗时，以及本次测试 Mod 的 SHA-256。
- `suite.json`：本次采用的清单副本。
- `game/`：该进程的独立 IPC、完整日志与测试存档。
- `<用例>/<步骤>/`：`verifier.log`、`evidence.json`、配置、截图及执行到该步骤时的游戏日志。

不要删除失败目录后原地重跑来覆盖证据；使用新的输出目录。启动失败也保留日志和错误文件。套件退出时仅终止自己启动的 PID，验证脚本超时则清理其进程组内的 MCP 子进程。

本次实际覆盖、阶段耗时和证据位置见[验证记录](../research/2026-11-01-gui-suite.md)。
