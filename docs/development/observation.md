# 游戏基础观察 JSON

输出语言为英语，游戏本身可以继续使用中文。底层结构版本及兼容基线统一见[项目 README](../../README.md#当前版本与前提)。信息范围遵循 [可见信息边界](../observation.md)，安装见 [正常游戏加载与读取](live-game.md)。

## 读取和控制信息

重新构建、安装 Mod 并重启游戏后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state > .tmp/live/observation.json
```

默认输出面向 LLM 的玩法内容，成功结果直接包含 `scene`、`screen`、`player` 等字段，没有 `ok`、外层 `state`、请求 ID、状态令牌、会话、结构版本或语言字段。版本、种子、Mod 调试覆盖层也不再作为玩法内容返回。

需要控制信息或排查问题时执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state --raw
```

`--raw` 保留原始文件协议：成功为 `id/ok/state`，`state` 内保留 `snapshot_id/schema_version/language/session` 及战斗、界面、选择、物品、房间、结算等代际字段；失败为 `id/ok/error`。Python 的 `Client.call()` 同样返回原始响应。生产入口通过 `response_pipeline.decode_success(operation, state, native_arguments)` 完整校验并转换成功结果，不改写原响应；旧 `player_result(response, operation="get_state")` 仍支持片段投影兼容调用，但不能替代完整校验。共享解释与 notes 在公开装配层生成。外部客户端必须自行保存最近的原始令牌，动作仍带 `expected_state` 校验；省略 LLM 可见令牌不等于绕过校验。[本地 MCP](mcp.md) 复用同一玩法输出转换。

玩法输出按声明的结构递归投影，未知嵌套字段不会转发；基础观察的 `player.hand` 不包含正文或悬停解释。已提供字段须符合对应类型，布尔值不能代替数字。MCP 与非 raw 文件客户端对基础观察和动作结果检查全部必需顶层观察字段，格式错误返回 `transport_error`，不保留动作令牌。这个检查不证明游戏采样本身符合可见信息边界；Mod 的显示过滤仍是读取依据。

## 页面主体的展示状态

事件、先古之民、建筑师、结算、奖励、火堆、商店、宝箱和占卜主体的status统一表达当前页展示进度：visible表示当前展示完成，not_ready表示仍在分阶段展示、当前文字／数值／列表可能不完整，covered表示被覆盖。get_observation和对应详情读取同一判断；not_ready结果带notes.presentation及来源列表。不增加content_complete。

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

`get_observation()` 等同于 `get_observation({"preset":"default"})`，保留完整基础观察的内容范围并省略普通空值；`preset:"full"` 保留原有空值。普通手牌仍不附正文或悬停详情，选牌可浏览面板按下述范围读取；统一规则见[MCP 输出预设](mcp.md#输出预设)。`get_observation({"preset":"actions_only"})` 仅返回以下上下文及工具名，例为战斗中的手牌选择：

```json
{
  "scene": "combat",
  "screen": {"status": "covered"},
  "selection": {"type": "hand", "status": "visible"},
  "available_actions": ["select_card", "selection_option", "inspect_potions", "inspect_selection", "set_selection_view"]
}
```

这是结构示例，工具名仅用于说明字段形态；实际列表随按钮、持有物及交互状态变化，以当前完整返回为准。`scene` 仍表示底层房间或战斗；`screen.view` 标识地图、牌组／牌堆、占卜、确认、建筑师或结算，`selection.type/status` 区分选牌及查看战场，没有待处理选择时省略 `selection`。精简输出不附候选参数、提示、数值或占卜图像；后续需要详情时调用相应工具或再次完整观察。

五种预设都会实时读取、完整校验并刷新内部动作令牌，精简模式不改变游戏 UI，也不改变后续动作的精简回执格式，见[MCP 动作返回](mcp.md#动作返回格式)。只允许可选字符串 `preset: default/full/actions_only/summary/top_bar`；非法值或额外字段返回 `invalid_request`，保留已有许可且不请求游戏。读取被明确拒绝与结果未知的处理分别遵循[MCP 错误语义](mcp.md#调用和错误语义)。预设属于 MCP 输出投影，底层文件 `get_state` 仍返回完整状态。

`preset:"summary"` 基于 default 分别处理共用顶栏、战斗观察、当前卡牌选择、结算卡牌、商店卡牌、普通事件和占卜教学说明；共用部分先于场景分派执行：

- 玩家、敌人及友方的 `hp/max_hp/hp_display` 合并为 `health`：正常为 `"70/80"`，无限为 `"∞"`，死亡为 `"dead"`，无法识别显示为 `"unknown"`，隐藏时显式保留 `null`。不补隐藏生命数字，格式为 numeric 但数字不完整时也保留 `health:null`。
- 玩家能量合并为 `energy:"3/3"`，移除 `max_energy`；数字不可完整读取时省略，不拼接猜测值。`stars` 保持原有意义。
- `powers/orb_slots/sovereign_blades` 为 `[]` 时省略；有空槽的非空球数组保留位置及 null 元素。友方共享格挡标记保留。
- `player.hand` 复用 [inspect_hand 的摘要字段](hand-inspection.md#参数与返回范围)，移除稀有度和卡池，保留费用颜色、标记及可见附魔；空值遵循本预设的 default 规则。
- 所有场景的 `top_bar` 独立复用同一摘要，仅保留 `gold/potion_slots/deck_count/relic_count`；隐藏时省略，不从遗物明细推算未知数量。其他字段、意图、按钮、可用工具及适用 notes 保留。非战斗主体及当前选择按下述规则精简。

当前选择页的 `selection` 候选、包内卡牌和已展开的比较均复用手牌摘要，省略正文、稀有度、卡池、空 `unplayable_markers` 和 `outline:"none"`；其他描边、非空标记及可见附魔保留。空 bundles 与空 `upgrade_previews/enchant_previews/transform_previews` 省略，cards／selected_ids／options 的空数组保留。提示、数量限制、全部已选 ID、按钮启用状态、升级模式、附魔操作说明及随机结果标记保留；比较中的未知身份、随机 after:null 不补齐。

奖励和宝箱的房间主体保持与default一致，不省略标题、选项、空列表或按钮状态。火堆在full/default/summary中共用[静态格式](rest-site.md#观察与详情)，省略顶层与选项description；完整说明由inspect_rest_site.default/full提供，其他空值按各自预设处理。宝箱可见时 default／summary 保留 `treasure.relic:null`；被覆盖时仍省略，完整规则见[公共空值规则](mcp.md#输出预设)。弹出的选牌使用上述共用摘要，顶栏独立精简。

商店的商品卡牌复用共用卡牌摘要：保留已有的名称、类型和费用，省略 rarity／visual_card_pool；商品 ID 保持在 items[].id，card 内不额外生成 ID。价格、affordable、enabled、on_sale、position、已用删牌项等商品信息仍沿用 default。商店卡牌沿用其网格上下文的可见外观字段；未显示的费用颜色、描边或不可打出标记不补造；卡牌正文继续通过 inspect_shop 查看。先古之民主体保持 default。

普通事件主体在 get_observation.full/default/summary 中均使用 inspect_event.summary：省略页面叙事 event.description、悬停说明及 lethal_warning:false；保留选项效果 description、true 警告、启用状态和前进按钮。完整已展示正文及选项悬停解释由 inspect_event.full/default 提供。共用规则见[事件接口](events.md#基础观察与详情)。

审判（Trial）同样省略页面叙事，confirmation.description 保留，不能按字段名递归删除后果说明。建筑师 epilogue 主体沿用 default。结算主体三种内容预设共用静态名称／提示标题，卡牌full/default为face、summary为卡牌摘要，见[结算接口](run-ending.md#结算观察)。占卜在 full/default/summary 中均省略固定教学 divination.instructions，保留文字棋盘、可见碎片、次数、工具和当前完整对白；基础观察不返回 PNG，也不接受 include_image。详情教学和可选图像见[占卜接口](divination.md)。

已就绪且未被更高层覆盖的牌组页提供完整 `deck`、`view_upgrades` 和 `sort.by/descending`，分别对应 UI 的升级模式、主排序与方向。full/default/summary 的牌组卡牌采用 face_full／face_default／共用卡牌摘要，均无正文和悬停解释；ID 和显示顺序与 inspect_deck 相同，后者的 card_ids 不会限制基础观察。关闭或被覆盖后不附缓存内容，详细边界见[牌组接口](deck-inspection.md)。actions_only/top_bar 不增加牌组数据。

已就绪且未被更高层覆盖的战斗牌堆页提供 pile、cards、message；full/default/summary 的卡牌分别采用 face_full／face_default／共用摘要，均无正文或悬停解释，底部固定 message 在 summary 省略。原生显示顺序及 ID 与 inspect_pile 一致，不继承 card_ids 筛选，不读取真实抽取顺序；关闭或覆盖后不附缓存，actions_only/top_bar 不增加这些字段。详见[牌堆接口](pile-inspection.md#已打开牌堆的基础观察)。

地图覆盖（`screen.view:map`）时，full/default/summary 的 map 均返回整幕节点的 `nodes_by_type` 分类、当前节点及原生可选节点；不含连接、名称、揭晓类型或任务标记。`notes.map` 提醒连接省略、详情用 inspect_map。基础观察不继承详情的 max_steps；actions_only/top_bar 不附地图或这条 note，地图未就绪／关闭／被覆盖时也不附 note。完整规则见[地图接口](map-inspection.md#地图选路)。所有浏览页均先处理共用顶栏摘要，保留被覆盖选择的元数据，不对下层战斗再次压缩；分工依据见[共用顶栏记录](../research/2026-11-02-shared-top-bar-summary.md)。

结算的 `run_result` 主体沿用 default，保留完整的当前页 texts、分数、徽章、发现、options 及空列表；已显示的 cards 复用卡牌摘要，保留字符串 card:N ID、名称、类型和费用等字段，省略正文、稀有度及卡池。需要正文或悬停说明时调用 inspect_run_result。full/default 的结算卡牌使用共用完整格式，包含逐牌悬停解释；结算页其他悬停帮助仍由专项详情提供。主菜单与 unrecognized 主体沿用 default；共用顶栏规则独立适用。约定及验证见[结算观察实施记录](../research/2026-11-03-result-observation-implementation.md)。

已打开候选页的 full/default/summary 都提供整个原生可浏览列表，包含滚动区域外的候选，保持原生顺序及原牌 ID。读取不滚动或选择卡牌；确认预览只提供该页展示内容，眼睛与覆盖页继续隐藏选择。卡面附魔按实际显示规则读取，字段及界面操作见[选牌接口](card-selection.md)。

`preset:"top_bar"` 在 actions_only 的场景、页面、选择 type/status 和工具名上增加 default 的顶栏字段，移除 `top_bar.relics` 并保留 `relic_count`。不套用 summary 的顶栏四字段限制，也不合并顶栏 hp/max_hp；不返回战斗单位、手牌、房间正文、notes 或占卜图像。遗物效果通过 `inspect_relics` 查看。顶栏不可读时省略，不伪造空顶栏。

full/default 顶栏提供 `relic_count`，表示原生遗物栏登记的持有数量；整个遗物栏不可读时为 null。它独立于是否可悬停或位于屏幕内，不从筛选后的明细列表求长度。旧 Mod 缺少该字段时，各预设省略数量，不猜测成零或列表长度；更新排错见[正常游戏指南](live-game.md#更新与排错)。样例与验证范围见[战斗核验记录](../research/2026-11-02-get-observation-combat.md)。

`available_actions` 包含当前原生页面允许的详情和页面工具，例如 `inspect_selection`、`set_selection_view`、`close_card_view`、`close_map`，不是全部已安装工具。工具出现不意味着任意卡牌、目标、商品或选项参数都有效，也不保证调用前状态不发生变化。列表不携带参数；从完整观察或专用详情读取候选后再提交。

当前暴露的地图、牌组及抽牌／弃牌／消耗堆浏览页保留实际可见顶栏。`screen.status:covered` 表示下层战斗／房间被覆盖，不会单独使顶栏不可读；顶栏本身隐藏、透明、位于视口外，或受不支持的弹窗／详情／过渡遮挡时仍不读取。单个数字隐藏时不从模型补齐。药水说明和已显示遗物可通过相应 inspect 工具查看；遗物静态条目与悬停缺失 note 的边界见[遗物详情](relic-inspection.md#读取边界)，下层战斗和药水动作仍按原有条件限制；验证见[顶栏修复记录](../research/2026-11-02-top-bar-visibility.md)。

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

`allies: null` 表示战场不可读，`[]` 表示当前可见范围中没有友方召唤物；死亡奥斯提的身体仍可识别，但已隐藏的生命数字保持 `null`，不从模型补出 0。悬浮剑按卡牌稳定 ID 排列，公转不改变顺序或状态令牌；隐藏、零缩放或被实际裁剪的剑不列出；已展示剑不按视口坐标截断，也不借其读取其他隐藏卡牌。剑离开手牌后，只要悬浮对象仍然可见，就仍可通过 [inspect_combatants](combatant-inspection.md) 查看原生卡牌预览；消耗及变牌后随原生对象移除。来源和验证见[奥斯提与君王之剑](../research/2026-11-02-companions.md)。

充能球按当前 UI 队列顺序输出，首项是最先激发的槽位，不按屏幕横坐标排序；不包含已脱离队列但仍在淡出的旧图像。球种可以按外观识别，普通球未显示的激发数值为 `null`，等离子球不补出模型数字。任一槽位隐藏或被裁剪时，整个 `orb_slots` 为 `null`，避免把未知槽当空槽。已生成球的悬停说明由 [inspect_combatants](combatant-inspection.md) 提供；空槽的通用帮助由 [inspect_ui](ui-inspection.md) 提供。

## 数值预览说明

客户端仅在成功的战斗结果包含至少一项敌人意图时加入以下 `notes.enemy_attack_intents`；没有可读意图时省略这一条。普通命令行输出和 MCP 共用此规则，原始协议不附这条客户端说明。手牌数值及选牌提示按各自场景加入，不受敌人意图是否存在影响。

```json
{
  "notes": {
    "enemy_attack_intents": "Enemy attack intents already include current preview modifiers, including effects on you. Do not apply those modifiers again; the number is not guaranteed HP loss."
  }
}
```

敌人攻击意图已经按当前本地玩家计算，包含适用的易伤、污染等效果，不能再对意图数字重复应用同一效果。意图仍是当前预览，不保证等于最终生命损失。

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

按 [README](../../README.md#开发与运行入口) 加载路径配置，再按 [往返指南](roundtrip.md) 构建，在独立实例验证：

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
