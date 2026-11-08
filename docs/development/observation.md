# 游戏基础观察 JSON

输出语言为英语，游戏本身可以继续使用中文。底层结构版本由[观察序列化入口](../../src/Sts2Agent/Observation/GameObservation.cs)中的 `schema_version` 定义；游戏及依赖兼容基线见[项目 README](../../README.md#当前版本与前提)。信息范围遵循 [可见信息边界](../observation.md)，安装见 [正常游戏加载与读取](live-game.md)。

## 读取和控制信息

重新构建、安装 Mod 并重启游戏后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state > .tmp/live/observation.json
```

默认输出面向 LLM 的玩法内容，成功结果直接包含 `scene`、`screen`、`player` 等字段，没有 `ok`、外层 `state`、请求 ID、状态令牌、会话、结构版本或语言字段。种子和 Mod 调试覆盖层属于内部信息。

需要控制信息或排查问题时执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state --raw
```

`--raw` 保留原始文件协议：成功为 `id/ok/state`，`state` 内保留 `snapshot_id/schema_version/language/session` 及战斗、界面、选择、物品、房间、结算等代际字段；失败为 `id/ok/error`。Python 的 `Client.call()` 同样返回原始响应。生产入口通过 `response_pipeline.decode_success(operation, state, native_arguments)` 完整校验并转换成功结果，不改写原响应；旧 `player_result(response, operation="get_state")` 仍支持片段投影兼容调用，但不能替代完整校验。共享解释与 notes 在公开装配层生成。外部客户端必须自行保存最近的原始令牌，动作仍带 `expected_state` 校验。[本地 MCP](mcp.md) 复用同一玩法输出转换。

玩法输出按声明的结构递归投影，未知嵌套字段不会转发；基础观察的 `player.hand` 不包含正文或悬停解释。已提供字段须符合对应类型，布尔值不能代替数字。MCP 与非 raw 文件客户端对基础观察和动作结果检查全部必需顶层观察字段，格式错误返回 `transport_error`，不保留动作令牌。游戏端依据实际 UI 做显示过滤，Python 负责协议结构与类型校验。

## 页面主体的展示状态

事件、先古之民、建筑师、结算、奖励、火堆、商店、宝箱和占卜主体的status统一表达当前页展示进度：visible表示当前展示完成，not_ready表示仍在分阶段展示、当前文字／数值／列表可能不完整，covered表示被覆盖。`get_observation` 和对应详情共用判断；`not_ready` 结果带 `notes.presentation` 及来源列表，提醒可用动作也可能尚未齐全，应待页面稳定后重新读取。actions_only、top_bar 及使用同一精简投影的关闭回执保留此提示。

该状态与screen.status的可见／覆盖含义分开，也与操作合法性分开。展示完成但按钮禁用时仍为visible；enabled和available_actions继续依据原生操作条件。尚未翻开的占卜格子、未打开的宝箱或未来解锁不代表当前展示未完成。占卜phase、商店view及宝箱chest保留各自业务阶段。

原生PresentationState统一生成主体状态，各页面DisplayComplete核对当前展示信号，Ready保留原生队列、交互与按钮守卫。计分及宝箱集合的有限入场／退场补间由PresentationMotion按弱引用采样，读取不阻塞游戏线程。

## 场景上下文

基础观察、动作回执和所有已返回 scene 的详情工具，使用同一含义与判定入口：

- `scene` 表示当前战斗、房间或结算场景，取值为 `combat/rewards/rest_site/treasure/shop/ancient/event/map/epilogue/run_result/main_menu/unrecognized`。不能根据工具名称或读到战斗背景就改为 combat。
- `scene:map` 仅表示当前房间本身是原生 MapRoom，例如换幕后尚未选择先古之民节点的地图入口；普通战斗或事件上展开地图仍保留 combat/event 等原场景。
- `screen.status` 表示该场景的可见／覆盖状态，取值为 `visible/covered/hidden/not_ready/not_applicable`；`screen.view` 在识别到覆盖或专项页面时提供。没有已识别查看页时省略 view。
- 地图展开时返回 `screen:{status:covered,view:map}`，与牌组／牌堆一样表示下层场景被覆盖；不据此隐藏仍暴露的顶栏。`map.status:visible` 仍表示地图本身可见，地图主体与摘要另按现有接口读取。
- `view` 包括 `map/deck/draw_pile/discard_pile/exhaust_pile/divination/confirmation/epilogue/run_result`。打开地图、牌组和牌堆不会将 scene 改为页面类型；牌堆本次请求是否打开页面另看其 status。
- 详情读取使用其状态令牌对应的快照上下文；会打开或修改页面的工具，使用修改后的快照。因此，同一画面的 scene/screen 与 get_observation 一致；不因 summary 或筛选改变。

例如在事件中打开牌组，get_observation 与 inspect_deck 都返回 `scene:event`、`screen:{status:covered,view:deck}`；建筑师的 inspect_ui/inspect_combatants 返回 `scene:epilogue`。空牌堆没有打开页面，仍返回实际战斗画面的 screen，而非伪造一个牌堆页。

原生 [ObservationContext](../../src/Sts2Agent/Observation/ObservationContext.cs) 负责场景、遮挡与页面判定，详情响应由共用入口复制对应快照的上下文；[Python 场景校验](../../src/sts2_mcp/output/scene_context.py)统一检查与投影。专门工具返回自身领域数据及场景上下文；可用操作由 get_observation 提供。

## MCP 输出预设

`get_observation` 的五种预设均实时采样、完整校验结果并刷新内部动作令牌。参数仅有可选字符串 `preset`；非法值或额外字段返回 `invalid_request`，保留已有许可。令牌与失败恢复见[MCP 调用语义](mcp.md#调用和错误语义)，普通空值及事件例外见[公共输出规则](mcp.md#输出预设)。

| 预设 | 返回范围 |
| --- | --- |
| `default`（默认） | 完整基础观察，省略普通空值 |
| `full` | 与 default 相同的内容范围，保留普通空值 |
| `summary` | 在 default 上精简战斗对象、卡牌和顶栏，场景主体见下表 |
| `actions_only` | `scene`、`screen`、`available_actions`，以及有待处理选择时的 `selection.type/status` |
| `top_bar` | actions_only 加上 default 顶栏，保留 `relic_count`、移除 `relics`；顶栏生命仍用 `hp/max_hp` |

基础观察中的所有标准卡牌，full/default 使用[无正文的牌面格式](hand-inspection.md#共用卡牌格式)，summary 使用共用卡牌摘要。适用于手牌、选牌候选、卡包、比较两侧、商店、牌组／牌堆和结算卡牌；正文及悬停解释由专项详情提供。

### 战斗与顶栏摘要

summary 的战斗内容按以下规则精简：

- 玩家、敌人及友方的 `hp/max_hp/hp_display` 合并为 `health`：正常为 `"70/80"`，无限为 `"∞"`，死亡为 `"dead"`，无法识别显示为 `"unknown"`。隐藏或数字不完整时显式保留 `health:null`。
- 可见毒／灾厄血条的 `hp_preview` 保留，字段含义见[血条预示](combatant-inspection.md#血条预示)。
- 完整能量对合并为 `energy:"3/3"` 并移除 `max_energy`；数字不完整时省略能量。`stars` 保持原有意义。
- 空 `powers/orb_slots/sovereign_blades` 省略；非空球槽数组保留位置和空槽 `null`。友方共享格挡标记保留。
- 手牌使用[共用摘要](hand-inspection.md#参数与返回范围)，保留身份、费用、可见附魔、Affliction、费用颜色、非空标记及有效描边。
- 意图、按钮、可用工具和仍适用的 notes 保留。

各场景的顶栏独立处理：full/default 保留可见顶栏；summary 仅保留 `gold/potion_slots/deck_count/relic_count`；top_bar 使用上表范围。顶栏不可读时按对应预设的空值规则处理，数量以原生可读值为准。

地图、牌组和牌堆覆盖时，`screen.status:covered` 表示下层场景被覆盖，仍实际显示的顶栏继续可读。顶栏自身的隐藏、透明、视口、裁剪及弹窗遮挡另行判断。药水与遗物查看的条件见[药水边界](potion-inspection.md#显示与悬停边界)和[遗物边界](relic-inspection.md#读取边界)。

### 场景主体与专项详情

full/default/summary 共用各场景的静态主体；summary 再精简其中的卡牌和公共顶栏。以下表格列出基础观察的内容入口，完整契约由对应专题维护。

| 场景或页面 | 基础观察与详情分工 |
| --- | --- |
| [选牌](card-selection.md#观察与信息范围) | 返回整个可浏览候选及已展开比较；保留提示、数量限制、全部已选 ID、按钮、升级模式、附魔操作说明和随机标记。summary 省略空的包／列表预览，保留 cards、selected_ids、options 空数组 |
| [奖励](rewards.md#观察与详情) | 静态奖励行、标题和按钮；悬停帮助由 inspect_rewards 提供 |
| [休息处](rest-site.md#观察与详情) | 选项名称、启用状态及按钮；顶层和选项 description 由 inspect_rest_site 提供 |
| [宝箱](treasure.md#观察与详情) | 箱子状态、已显示遗物名称与按钮；可见主体在 default/summary 中也保留 relic:null |
| [商店](shop.md#打开观察与详情) | 已展示商品的购买字段和卡牌牌面；商品 ID 位于 items[].id。完整效果由 inspect_shop 提供 |
| [先古之民](ancients.md#工具与观察) | 已显示对话、馈赠正文与按钮；仅保留 true 致死警告，悬停解释由 inspect_ancient 提供 |
| [事件](events.md#基础观察与详情) | 选项效果、启用状态、true 致死警告及前进按钮；页面叙事与悬停解释由 inspect_event 提供 |
| [确认框](events.md#事件确认弹窗) | 保留标题、完整后果说明与按钮 |
| [建筑师](run-ending.md#建筑师观察) | 当前完整气泡及按钮 |
| [结算](run-ending.md#结算观察) | 当前 texts、分数、徽章、发现、静态物品名称和提示标题、按钮及空列表；完整正文效果和悬停说明由 inspect_run_result 提供 |
| [占卜](divination.md) | 文字棋盘、可见碎片、次数、工具及当前完整对白；教学和可选 PNG 由 inspect_event 提供 |
| [牌组](deck-inspection.md#生命周期及验证) | 已打开且就绪页面的完整 deck、升级模式及排序；ID 与原生顺序保持 |
| [战斗牌堆](pile-inspection.md#已打开牌堆的基础观察) | 已打开且就绪页面的 pile、cards、message；summary 省略底部固定 message |
| [地图](map-inspection.md#地图选路) | 整幕 nodes_by_type 分类、当前节点及原生候选；notes.map 提示用 inspect_map 查看连接及节点详情 |

actions_only/top_bar 按上表的最小范围返回。基础观察独立读取当前 UI；详情调用的 `card_ids`、`max_steps` 等输出筛选只作用于该次详情结果。关闭、覆盖或未就绪的浏览页按各自契约返回，避免沿用缓存内容。

例如，actions_only 在手牌选择中可返回：

```json
{
  "scene": "combat",
  "screen": {"status": "covered"},
  "selection": {"type": "hand", "status": "visible"},
  "available_actions": ["select_card", "selection_option", "inspect_potions", "inspect_selection", "set_selection_view"]
}
```

工具名仅示意字段形态，实际列表随当前页面和交互条件变化。原生采样入口见[GameObservation](../../src/Sts2Agent/Observation/GameObservation.cs)，基础观察的卡牌格式由[成功解码](../../src/sts2_mcp/output/observation_details.py)选择，预设投影由[observation_presets](../../src/sts2_mcp/output/observation_presets.py)处理。

## 玩法字段

以下空值语义及含 null 的示例以底层文件或 MCP full 为准；default 按[公共规则](mcp.md#输出预设)省略普通空字段，保留槽位等结构。

| 字段 | 内容 |
| --- | --- |
| `screen.view` | 可识别的当前查看页：`deck/draw_pile/discard_pile/exhaust_pile/map`，或占卜 `divination`、确认框 `confirmation`（Trial 支持操作，未知来源仍为人工输入）、建筑师 `epilogue` 及结算 `run_result`；仅在实际显示时出现 |
| `confirmation` | 当前受支持的原生确认框：类型、标题、正文及两个按钮；没有时为 null，详见[事件接口](events.md#事件确认弹窗) |
| `scene`、`screen.status` | 当前场景，以及 `visible/covered/hidden/not_ready/not_applicable` |
| `turn` | 当前结束回合按钮显示的回合号；未显示数字时为空 |
| `player.character` | 当前可见角色身份，例如 `IRONCLAD` |
| `hp`、`max_hp`、`hp_display` | 实际显示的生命数字，以及 `numeric/dead/infinite/hidden/unknown` 显示状态；用于角色和敌人 |
| `hp_preview` | 玩家、敌人与友方当前血条的毒／灾厄预示；含义及空值见[血条预示](combatant-inspection.md#血条预示) |
| `block`、`energy`、`max_energy`、`stars` | 当前可见资源与计数 |
| `player.hand[]` | 从左到右排列的当前可见手牌，包含稳定 ID、名称、固有属性、显示费用与标记，不含卡牌正文 |
| `deck[]`、`view_upgrades`、`sort` | 仅在当前牌组页可读时出现；完整排序列表及 UI 实际设置，卡牌无正文／悬停解释 |
| `player.orb_slots` | 按原生队列排列的充能球槽；整个字段 `null` 表示不可读，`[]` 表示没有槽位，数组项 `null` 表示空槽。非空项含 `name/passive/evoke`，数字仅取实际显示标签 |
| `powers[]` | 实际显示状态图标的英语名称和可见计数，不枚举全部模型状态 |
| `enemies[]` | 从左到右排列的可见敌人身份、定位 ID、生命、格挡、状态图标和当前意图 |
| `allies[]` | 从左到右排列的可见友方召唤物，包含 `id/name/hp/max_hp/hp_display/block/powers`；奥斯提不属于敌人 |
| `allies[].block_shared_with` | 实际生命条控件跟踪本地玩家格挡时为 `"player"`；该格挡是玩家同一资源的重复显示，不是额外一份 |
| `player.sovereign_blades[]` | 当前可见悬浮君王之剑的 `id/name`，ID 与绑定卡牌共用；不自动提供正文或伤害数值 |
| `intents[]` | 当前渲染意图的 `category/value`，不读取下一招模型或悬停说明 |
| `draw_count/discard_count/exhaust_count` | 当前可见牌堆计数，不返回内容或顺序 |
| `top_bar` | 当前可见生命与最大生命（`hp/max_hp`）、金币、总楼层、可见进阶等级、主牌组数量、房间图标、首领、药水槽、遗物及入口可见性 |
| `top_bar.bosses` | 实际显示的首领名称数组，例如 `["Ceremonial Beast"]`；未识别的可见图标以槽内 `null` 保留 |
| `top_bar.potion_slots` | 按位置排列；槽内 `null` 是已确认空槽，非空为含 `name` 的对象，整个字段为 `null` 是未能观察槽位 |
| `top_bar.relics[].melted` | 与[遗物详情](relic-inspection.md#格式)相同：蜡质未熔化／已熔化分别为 `false/true`，非蜡质不适用或图标不可读时为 `null` |
| `top_bar.relics[].grayed_out/pulsing` | 与遗物详情共用实际图标置灰／激活发光读取；full 保留 false 和未知 null，default 省略这两字段的 false／null；summary/top_bar 不返回遗物列表 |
| `top_bar.relic_count` | 原生遗物栏登记的持有数量，不按视口位置或能否悬停截断；遗物栏不可读时为 null，旧 Mod 可缺少此字段 |
| `buttons.end_turn` | 当前按钮的英语文字与启用状态 |
| `available_actions` | 当前场景可用的查看与操作工具名，不含参数；省略 `get_observation`、截图和测试入口。具体参数、状态和原生条件仍在调用时检查 |
| `notes` | 按结果内容附带的英语数值解读说明，无适用内容时省略；属于接口说明，不是额外采样到的游戏状态 |

战斗外在 [药水工具支持的页面](potion-actions.md#场景与停止边界) 也提供可见顶栏；搜刮页使用 `scene: "rewards"` 和独立的[奖励结构](rewards.md)，休息处、宝箱房、商店、先古之民和[通用事件](events.md)分别使用 `rest_site`、`treasure`、`shop`、`ancient`、`event`；[终章与结算](run-ending.md)使用 `epilogue` 与 `run_result`；未匹配已支持场景的页面使用 `unrecognized`，也可能处于加载过渡；不将商店等已识别非战斗场景归入该类。战斗外的 `player/enemies/turn/buttons` 为空；事件被覆盖时不附送其下方的正文和选项。

旧兜底标识 `loading_or_noncombat` 已替换为 `unrecognized`，当前 MCP 校验不接受旧名称。该值本身不判断加载是否完成，须结合 screen、实际内容和 available_actions 判断；更新时应配套更换 Mod 和 Python，见[更新说明](live-game.md#更新与排错)。

奖励列表及已打开本局详情的滚动内容完整读取，不按视口截断；适用边界统一见[可浏览列表](../observation.md#可浏览列表)。这不改变地图／牌组／牌堆主体的摘要占位，也不自动展开悬停、隐藏页面或未来内容。

数字来自可见标签，金币动画期间也按标签返回。`null` 不等于 0，表示未显示、尚未准备或不能可靠识别；可见空容器使用 `[]`。正常生命条没有格挡图标时才归一化为 `block: 0`。死亡文字与无限图标分别映射为 `dead`、`infinite`，不从隐藏生命模型补数字。

战场对象的生命、格挡、状态与意图通过与 [inspect_combatants](combatant-inspection.md) 相同的读取入口取得；该工具支持按对象或静态字段筛选，summary 共用生命显示格式。

`allies: null` 表示战场不可读，`[]` 表示当前可见范围中没有友方召唤物；死亡奥斯提的身体仍可识别，但已隐藏的生命数字保持 `null`，不从模型补出 0。悬浮剑按卡牌稳定 ID 排列，公转不改变顺序或状态令牌；隐藏、零缩放或被实际裁剪的剑不列出；已展示剑不按视口坐标截断，也不借其读取其他隐藏卡牌。剑离开手牌后，只要悬浮对象仍然可见，就仍可通过 [inspect_combatants](combatant-inspection.md) 查看原生卡牌预览；消耗及变牌后随原生对象移除。来源和验证见[奥斯提与君王之剑](../research/2026-11-02-companions.md)。

充能球按当前 UI 队列顺序输出，首项是最先激发的槽位，不按屏幕横坐标排序；不包含已脱离队列但仍在淡出的旧图像。球种可以按外观识别，普通球未显示的激发数值为 `null`，等离子球不补出模型数字。任一槽位隐藏或被裁剪时，整个 `orb_slots` 为 `null`，避免把未知槽当空槽。已生成球的悬停说明由 [inspect_combatants](combatant-inspection.md) 提供；空槽的通用帮助由 [inspect_ui](ui-inspection.md) 提供。

## 数值预览说明

客户端仅在成功的战斗结果包含至少一项敌人意图时加入以下 `notes.enemy_attack_intents`；没有可读意图时省略这一条。普通命令行输出和 MCP 共用此规则，原始协议不附这条客户端说明。手牌数值及选牌提示按各自场景加入，不受敌人意图是否存在影响。

```json
{
  "notes": {
    "enemy_attack_intents": "Attack intents include current preview modifiers; block and damage redirection affect HP loss."
  }
}
```

敌人意图描述返回状态中接下来要执行的动作；`transition.events` 描述本次调用期间已经结算的动作。结束回合后敌人可能已切换意图，核对上一轮伤害须使用攻击前的意图。

攻击意图已经按当前本地玩家计算，包含适用的易伤、污染等效果；估算生命损失时还须考虑格挡和伤害转移，例如 Osty 代受伤。已包含的预览修正只计算一次。

`card_values` 仅属于 [查看手牌详情](hand-inspection.md) 的结果，基础战斗观察不输出。手牌数值可能已经包含缩小等修正，但未包含某个敌人的易伤，对准目标后会重新预览。仅查看手牌、不包含敌人意图的结果不附带 `enemy_attack_intents`。

来源与验证范围见 [手牌查看来源调研](../research/2026-10-29-hand-inspection-sources.md#数值预览的上下文)。固定说明不根据当前状态枚举效果、计算目标伤害或调用刷新预览的方法。

## 手牌与身份

单张已识别卡牌的示例：

```json
{
  "id": 0,
  "name": "Defend",
  "type": "Skill",
  "rarity": "basic",
  "visual_card_pool": "ironclad",
  "energy_cost": "1",
  "star_cost": null,
  "unplayable_markers": [],
  "outline": "cyan"
}
```

- `id` 对应卡牌实例，在同一战斗和 Mod 会话中稳定。同名副本使用不同 ID；重新抽到同一实例复用 ID，ID 不因位置改变而重排。普通抽牌按实际发生顺序分配，生成等其他来源在首次可见时分配。身份映射仅使用过去的本地抽牌记录与当前可见卡牌，不输出隐藏牌内容或位置；重启进程不保证相同编号。
- `name` 为英语基础名加牌面当前可见的升级后缀，例如 `True Grit+`；基础观察、手牌详情、选牌与目标查询共用同一可见牌名规则，不另读隐藏的升级级数。标题不可读时为 `null`；未知或锁定牌仍使用匿名标题。事件记录可以保留已经实际看见的完整名称，隐藏且未识别的名称仍为 `null`。来源与验证见[名称一致性修复](../research/2026-10-30-card-names.md)。
- `type` 为攻击、技能等固有牌型，已识别卡牌直接给出实际值，不要求小标签在画面中展开。`rarity` 为固有稀有度；普通横幅颜色不能单独区分 `basic/common`，这里明确允许按已识别身份补充。`visual_card_pool` 使用实际外观卡池，与真实卡池不同的特殊牌不暴露真实卡池。
- 未知或锁定牌不输出真实名称、牌型、稀有度或卡池，仍可通过不含内容语义的 ID 定位。
- `energy_cost/star_cost` 是显示字符串，保留 `X`、`?` 等形式。`energy_cost_color/star_cost_color` 仅在文字出现特殊颜色时输出 `red/green/blue/other`，默认颜色省略字段；不输出 RGB 或费用图标配色。
- `unplayable_markers` 合并标记位置：`[]`、`["energy"]`、`["star"]` 或二者都有。没有标记不等于可以打出。
- `outline` 为 `none/cyan/gold/red/other`，只表达当前描边，不据此声明动作合法。
- `enchantment` 仅在已识别卡牌的原生附魔图标当前可见且与模型身份一致时提供。`name` 是图标身份的英语名称；计数标签可读时才提供整数 `amount`，不以内部 Amount 补齐；`dimmed` 表示图标当前使用原生置灰材质，不是未来效果或可打出性判断。没有可见附魔、未知/锁定卡牌、图标隐藏或视口外时 full 返回 enchantment:null，default/summary 省略普通空值。附魔正文不进入基础观察，仍由手牌完整详情的共享提示提供。来源与边界验证见[卡面附魔记录](../research/2026-11-01-card-enchantments.md)。
- `affliction` 记录已识别卡牌当前实际显示的 Affliction 覆盖外观，仅有英语 `name`，不补内部层数或置灰字段；可与附魔共存。无可读覆盖时 full 为 null，default/summary 省略普通空值。隐藏、透明、离屏及未知／锁定牌均不提供身份。
- [手牌详情调用](hand-inspection.md) 一次返回全部当前可见手牌及其效果，沿用这些 ID；基础观察仍不输出完整效果、关键词或目标规则。

## 失败结果

文件客户端的默认失败结果为 `{"error":{"code":"stale_state","message":"...","recovery":"get_state"}}`，没有 `ok`。`message` 使用英语，提供可指导下一步的提示，内部异常路径和堆栈留在原始诊断响应或游戏日志中。

| 错误 | 建议处理 |
| --- | --- |
| `stale_state`、`illegal_action`、`expired_request` | `recovery: get_state`，重新观察后再选择动作 |
| `invalid_request` | `recovery: correct_request`，修正参数 |
| `timeout`、`game_error` | 标记 `outcome: unknown`，重新观察，不自动重试动作 |
| `transport_error` | 标记结果未知，`recovery: check_connection`，先检查连接 |

MCP 的恢复入口名为 get_observation，错误及权限语义统一见[MCP 指南](mcp.md#调用和错误语义)。客户端不自动重试动作。客户端等待超时也输出结构化错误；默认输出不会把原始异常信息直接交给 LLM。失败时命令仍以非零退出码结束。

## 采样与验证

读取在主线程执行，图形模式使用 `RenderingServer.FramePostDraw`，无头验证回退到 `SceneTree.ProcessFrame`。游戏动作复核停止边界、等待已识别的原生牌堆移动并检查观察稳定；时限及 `complete` 保证统一见[动作完成与画面稳定](end-turn.md#动作完成与画面稳定)，页面查看另行处理。读取不刷新 UI、不切换全局语言，英语名称独立读取游戏资源表。

显示检查覆盖有效性、显示开关、父级透明度、视口、祖先裁剪和描边 Shader 宽度。打开地图、菜单、教学、详情或过渡期间保守返回 `covered`。当前仍用矩形近似，不承诺逐像素判断卡牌之间或任意 Mod 图层的遮挡。

按[路径配置](roundtrip.md#路径配置)加载 `.env`，再按[往返指南](roundtrip.md)构建，在独立实例验证：

```sh
python3 scripts/prepare_roundtrip.py --game-dir "${Sts2Dir:?请先配置并加载 .env}" --language zhs
```

```sh
python3 scripts/run_roundtrip.py --windowed --capture --check-observation
```

```sh
python3 -m tests.game.verifiers.verify_roundtrip --ipc-dir .tmp/roundtrip/ipc --report .tmp/roundtrip/player-format-roundtrip.json --observation-output .tmp/player-observation-v3.json
```

独立测试入口创建铁甲战士临时战斗并关闭该测试存档的教学。截图和布局、临时 UI 扰动检查仅由测试标志启用；正常游戏不启用测试环境变量。基础采样的历史验证见 [实施说明](../research/2026-10-29-player-observation-plan.md)，更早的图形验证见 [历史记录](../research/2026-10-29-visible-combat-validation.md)。

## 选择状态

基础观察通过可空 `selection` 字段识别选牌、查看战场和覆盖状态。格式、工具与简短提示见 [选牌与查看战场](card-selection.md)。选择遮挡战场时不补出隐藏战斗数据；显式眼睛切换后复用正常可见性规则。底层 `selection_generation` 不含玩法信息，但参与动作令牌。

休息处基础观察的 `rest_site`、遮挡和选项规则见[休息处接口](rest-site.md)。锻造使用 `deck_upgrade` 选牌及实际显示的 `upgrade_previews`。

宝箱房基础观察的 `treasure`、开箱状态和遗物可见性见[宝箱房接口](treasure.md)。未开箱不透露隐藏内容，遗物效果须显式查看。

商店基础观察的 `shop`、商品摘要、补货 ID 和药水可用提示见[商店接口](shop.md)。未打开或被覆盖时不读取商品，完整效果需显式查看。

先古之民基础观察的full/default/summary共用inspect_ancient.summary的静态主体：保留已显示的对话、馈赠正文及true致死警告，省略悬停解释和false警告；其余结构和可见边界见[先古之民](ancients.md)。

## 占卜棋盘

[占卜接口](divination.md)通过 divination 返回当前阶段、可见次数、工具、对白、cell_rows 文字棋盘及 visible_fragments。#/. 表示覆盖／空白，s/S 区分局部图案与完整揭开；当前已揭开的方向线索由部位名称提供。三种基础观察预设共用事件详情摘要，省略固定教学；PNG 仅由 inspect_event.include_image 显式请求。底层事件与被覆盖棋盘内容继续隐藏，不读取雾下身份或未来随机奖励。

地图展开且就绪时，`map` 返回整幕类型分组及原生候选；可选时列出 `travel_to_node`。连接与节点详情由 `inspect_map` 提供，见[地图接口](map-inspection.md#地图选路)。

各场景工具可用性与早期预设验证见[核查记录](../research/2026-10-31-observation-presets-validation.md)；当前各场景 summary 的设计与实施证据见[逐项核验记录](../research/2026-11-02-get-observation-review.md)。

原生采样由 GameObservation.Capture 统一管理同步与代次，ObservationSnapshot 同时持有 JSON、令牌及原生身份；详情共用该快照的上下文。公开格式不因此增加私有元数据，见[MCP 成功上下文](mcp.md#成功结果的场景上下文)。占卜的图片需求由响应选项控制，不参与逻辑令牌计算，见[占卜接口](divination.md#工具与图像)。
