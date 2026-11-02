# get_observation 奖励、火堆与宝箱核验

> 当前状态：07–09 组的现状核验完成，11 类夹具、37 份完整 full 样本已保存；进入 summary 设计讨论，尚未定稿或修改工具行为。其余 8 组（10–17）待选，get_observation 整体未核销。

总流程见[工具核验记录](2026-11-02-mcp-tool-review.md)，分组见[观察场景目录](2026-11-02-get-observation-review.md)。inspect_rewards、inspect_rest_site、inspect_treasure 仅用于核对基础观察与详情的区别，不在本轮核销。

## 基线与证据

- 核对日期：2026-11-02，项目基线 `8d64c2f`，MCP `0.50.2`、Mod `0.49.1`、schema `31`。
- 游戏 Linux `v0.107.1`、release `59260271`，RitsuLib `0.6.10`。游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 当前构建产物与隔离运行时 Mod DLL 均为 `f6c4b3be3952e4020679c885292ca27ef5586fecdb54e6d943531b8eec5ae1f9`。本轮未重新构建，也未安装正式游戏 Mod。
- 原生读取：[RewardInspection](../../src/Sts2Agent/Observation/RewardInspection.cs)、[RestSiteInspection](../../src/Sts2Agent/Observation/RestSiteInspection.cs)、[TreasureInspection](../../src/Sts2Agent/Observation/TreasureInspection.cs)。组装与工具可用性见 [GameAdapter.Observe](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- MCP 验证与预设：[game_output.py](../../src/sts2_mcp/output/game_output.py)、[reward_details.py](../../src/sts2_mcp/output/reward_details.py)、[rest_site_details.py](../../src/sts2_mcp/output/rest_site_details.py)、[treasure_details.py](../../src/sts2_mcp/output/treasure_details.py)、[observation_presets.py](../../src/sts2_mcp/output/observation_presets.py)。
- 新反编译证据位于 `.tmp/2026-11-02-observation-rooms-review/source/`：目标程序集的 NRewardsScreen、NRestSiteRoom、NRestSiteButton、NTreasureRoom、RestSiteOption 及其九种具体选项。反编译产物不纳入 Git。
- 隔离 GUI、真实 stdio MCP 返回与相邻截图位于 `.tmp/2026-11-02-observation-rooms-review/`。夹具准备了奖励、遗物、牌组、生命和楼层，数值不代表正常开局；截图与 JSON 不是同一帧的原子采样。

## 07：奖励列表

基础观察只列当前屏幕内的奖励行。列表支持原生滚动；inspect_rewards 返回整张可浏览列表并增加 hover_tips，但不会展开尚未打开的卡牌候选。实测 basic 夹具有 6 行，初始基础观察只有 5 行，底部 card 奖励被裁切；领取上方金币后，该入口才出现在基础观察里。这与已调整为完整候选列表的选牌读取不同，属于后续设计需要明确的范围。

| 字段／状态 | 当前含义 |
| --- | --- |
| scene | rewards；即使已领空或被选牌、地图覆盖也可能保持这个底层场景 |
| rewards.status | visible 时返回本页；covered 时 title、items、proceed 均为 null |
| title | 已识别的原生标题；搜刮／被抢劫的区别，不以怪物名称推断 |
| items[].id | 本局当前奖励对象的稳定整数 ID；领取其他行后不重排，不等于数组下标或卡牌 ID |
| type | gold、potion、relic、card、special_card、card_removal、unsupported |
| text | 原生行文本，包括追回金币、特殊卡牌等区别；不是完整物品效果 |
| enabled | 当前工具可以点击此行；动画、等待和未支持类型可为 false |
| linked_group | 互斥奖励共有的组 ID，普通行 null；不是领取后还会保留的另一项奖励 |
| proceed | 当前原生按钮；text、enabled、skips_remaining 均保留。Skip 不保证立刻离开房间 |

- 普通领取后，已领取行消失，其他 ID 保持不变；全部领完后 items:[]，终结奖励页保留 Proceed。
- 满药水栏时，行仍可能 enabled:true：按钮可以点击，但原生流程会拒绝获取。claim_reward 的 reward_result.status 才报告 not_claimed；get_observation 不回放该结果或 transition。
- 打开 card 行后，selection.type:reward，rewards.status:covered，不同时返回隐藏列表。选牌 Skip 返回列表且保留奖励入口；候选结构及 summary 沿用已完成的[选牌设计](2026-11-02-get-observation-selections.md)。
- 领取遗物可能打开嵌套奖励，scene 仍为 rewards，但显示的是当前最上层奖励页。关闭后才返回父页。奖励也可覆盖火堆或宝箱，底层房间对象保持 covered。
- 目标源码 NRewardsScreen.UpdateScreenState 区分终结与非终结奖励：终结页领空后保留 Proceed，非终结页领空后自动关闭；OnProceedButtonPressed 的非终结 Skip 返回父页面。不能把所有空列表都设计成相同的后续路径。
- 被抢劫标题、card_removal、unsupported、禁止跳过及动画期间的 disabled 为当前实现／源码确认分支，本轮没有新造完整实测样本；普通类型、互斥、满栏、领空、卡牌覆盖、嵌套和地图推进有实测。

现行接口规则见[奖励接口](../development/rewards.md)，本轮不改领取行为。

## 08：火堆

| 字段／状态 | 当前含义 |
| --- | --- |
| scene | rest_site；选牌／地图覆盖时仍可能保持此值，弹出奖励时优先为 rewards |
| status | visible 或 covered；covered 时其余火堆字段均为 null |
| prompt | 当前可见的原生标题 |
| description | 当前画面已经展开且可识别的选项说明；未展开时 null |
| options | 当前可见按钮，含 id、text、enabled；不包含每项完整说明 |
| proceed | 实际显示时返回 text 与 enabled；可以与剩余选项同时存在 |

原生 NRestSiteButton.OnFocus / RefreshTextState 将对应选项说明写入房间，失焦后淡出。基础观察不主动聚焦按钮；inspect_rest_site 才读取各按钮的完整动态说明，包括灰置原因和数值。不能把 get_observation 的 full 理解为自动附送所有悬停内容。

- 普通页包含 HEAL / SMITH；有对应遗物时可增加 DIG、LIFT、KINDLE、COOK、CLONE、HATCH。当前按钮是否存在来自 UI，不通过遗物清单补造。它们只是同一种 options 结构的内容变体。
- 本轮 disabled 夹具中，SMITH 和 COOK 灰置，但仍保留在列表中且 enabled:false；HEAL 可用。灰置原因从 inspect_rest_site 获取。
- 普通休息后 options:[] 并提供 Proceed。Miniature Tent 允许使用多个不同选项，成功后移除用过的按钮，剩余 options 与 Proceed 共存；本轮采样包含 LIFT 后及连续三种操作后的状态。
- 锻造打开 deck_upgrade 选择，火堆对象变成 covered。取消返回原选项页，不消耗机会；升级候选、查看升级和前后预览属于[03 组选牌](2026-11-02-get-observation-selections.md)。COOK 等其他选牌同理，不重复设计牌面摘要。
- Dream Catcher 休息后打开奖励页，scene:rewards、rest_site.status:covered；处理奖励后回火堆，再继续。不能因选择的是 HEAL 就预设下一画面一定只有 Proceed。
- CLONE、HATCH、DIG、COOK 选牌、多人 MEND 和瞬态动画本轮仅核对实现／目标源码，没有新采完整流程；MEND 不在现有可执行选项白名单，不能假装已经支持多人目标流程。

现行规则见[休息处接口](../development/rest-site.md)。

## 09：宝箱房

| 字段／状态 | 当前含义 |
| --- | --- |
| status | visible 或 covered；covered 时 chest、relic、proceed 均为 null |
| chest:closed | 尚未开箱；relic:null，不读取预先生成的隐藏遗物；通常 proceed:null |
| chest:opening | 开箱处理中；当前实现根据宝箱按钮状态及完成标记判断，不代表遗物已可领取 |
| chest:open | 已开箱；不等于仍有遗物，须另外查看 relic |
| relic | 已实际显示的遗物才返回 name 与 enabled；没有正文或悬停说明，详情用 inspect_treasure |
| proceed | text、enabled、skips_remaining；有遗物待领时通常为 Skip，领完／空箱后为 Proceed |

目标源码 NTreasureRoom.OpenChest 的顺序为普通奖励、额外奖励、展示遗物、处理领取／跳过、开放前进。开箱可能先自动获得金币；JSON 不把金币伪装成一项待点奖励，最终顶栏反映当前金币。

- loot_treasure(open_only:true) 打开后保留遗物选择；本轮实测 Anchor 已显示且 enabled:true，Skip 可用。默认 loot_treasure 可能连同领取完成，因此要采待领取状态须显式只开箱。
- 领取后 chest:open、relic:null、proceed.skips_remaining:false。白银熔炉导致的空箱也会出现相同房间结构，工具不会在静态观察中伪造“刚领取”或“空箱原因”。可以从顶栏和动作历史理解差别，但不能仅凭 relic:null 反推。
- 额外奖励覆盖时，scene:rewards、treasure.status:covered；处理完才返回遗物。领取遗物自身引发的选牌／嵌套奖励也遵循相同覆盖原则，本轮未新采这些遗物变体。
- 开箱中 opening、尚未启用的 Skip、多人投票和教程遮挡只核对实现／源码；本轮完整样本只记录稳定可交互边界，不用稳定的 open 样本冒充动画帧。

现行规则见[宝箱房接口](../development/treasure.md)。

## 预设设计的讨论边界

本轮尚未定稿新的房间 summary。当前 summary 由 default 起步：三种房间主体保持 default，顶栏独立复用 gold、potion_slots、deck_count、relic_count；选择覆盖时继续使用共用卡牌摘要。actions_only 和 top_bar 也保持各自现行契约，不由房间摘要重新定义。

需要继续决定：奖励是否读取完整可浏览列表；房间摘要是否省略 prompt／title 等标题；是否需要整合当前可见说明。建议保留奖励 ID、按钮 enabled、互斥组与跳过语义，以及宝箱状态，避免压缩后无法判断该点什么。未展开候选、未来遗物或未显示的悬停效果不应通过 summary 补出。

## full 样本与验证

所有样本统一调用 `get_observation({"preset":"full"})`，仅保存实际 structuredContent：不删 null、不截断数组、不改写 ID、名称、数值、notes 或 available_actions。MCP 文本 JSON 与 structuredContent 在采集时逐次核对一致。下表下标从 0 开始，证据根目录为 `.tmp/2026-11-02-observation-rooms-review/`；同场景 screenshots/<步骤>.png 为相邻截图，精确映射见 samples-manifest.json。

### 奖励列表

| 场景 | 完整 full JSON | 本地 evidence.json／下标 |
| --- | --- | --- |
| 普通多类型奖励（6 行中可见 5 行） | [reward-basic-initial.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-initial.full.json) | gui/reward_basic：0 |
| 领取金币后，底部卡牌入口露出 | [reward-basic-after-gold.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-after-gold.full.json) | gui/reward_basic：4 |
| 卡牌奖励候选覆盖列表 | [reward-basic-card-choice.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-card-choice.full.json) | gui/reward_basic：7 |
| 跳过选牌返回，保留该入口 | [reward-basic-after-card-skip.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-after-card-skip.full.json) | gui/reward_basic：10 |
| 全部领完，空列表与 Proceed | [reward-basic-empty.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-empty.full.json) | gui/reward_basic：25 |
| 前进打开地图，奖励被覆盖 | [reward-basic-proceeded.full.json](2026-11-02-get-observation-rooms-examples/reward-basic-proceeded.full.json) | gui/reward_basic：28 |
| 满药水栏的奖励页 | [reward-full-initial.full.json](2026-11-02-get-observation-rooms-examples/reward-full-initial.full.json) | gui-remaining/reward_full：0 |
| 点击药水被拒领后的静态画面 | [reward-full-potion-refused.full.json](2026-11-02-get-observation-rooms-examples/reward-full-potion-refused.full.json) | gui-remaining/reward_full：4 |
| 两项互斥奖励，共同 linked_group | [reward-linked-initial.full.json](2026-11-02-get-observation-rooms-examples/reward-linked-initial.full.json) | gui-remaining/reward_linked：0 |
| 领取一项后整组消失 | [reward-linked-claimed.full.json](2026-11-02-get-observation-rooms-examples/reward-linked-claimed.full.json) | gui-remaining/reward_linked：3 |
| 领取会触发后续奖励的遗物 | [reward-nested-initial.full.json](2026-11-02-get-observation-rooms-examples/reward-nested-initial.full.json) | gui-remaining/reward_nested：0 |
| 当前嵌套奖励页 | [reward-nested-nested.full.json](2026-11-02-get-observation-rooms-examples/reward-nested-nested.full.json) | gui-remaining/reward_nested：3 |
| 返回已领空的父奖励页 | [reward-nested-returned.full.json](2026-11-02-get-observation-rooms-examples/reward-nested-returned.full.json) | gui-remaining/reward_nested：6 |

### 火堆

| 场景 | 完整 full JSON | 本地 evidence.json／下标 |
| --- | --- | --- |
| 普通火堆选项 | [rest-basic-initial.full.json](2026-11-02-get-observation-rooms-examples/rest-basic-initial.full.json) | gui-remaining/rest_basic：0 |
| 地图覆盖火堆 | [rest-basic-map.full.json](2026-11-02-get-observation-rooms-examples/rest-basic-map.full.json) | gui-remaining/rest_basic：4 |
| 锻造选牌覆盖火堆 | [rest-basic-smith-choice.full.json](2026-11-02-get-observation-rooms-examples/rest-basic-smith-choice.full.json) | gui-remaining/rest_basic：8 |
| 休息后无剩余选项 | [rest-basic-healed.full.json](2026-11-02-get-observation-rooms-examples/rest-basic-healed.full.json) | gui-remaining/rest_basic：12 |
| 火堆前进后的地图 | [rest-basic-proceeded.full.json](2026-11-02-get-observation-rooms-examples/rest-basic-proceeded.full.json) | gui-remaining/rest_basic：15 |
| Smith / Cook 灰置，Rest 可用 | [rest-disabled-initial.full.json](2026-11-02-get-observation-rooms-examples/rest-disabled-initial.full.json) | gui-remaining/rest_disabled：0 |
| 帐篷与多种额外选项 | [rest-tent-initial.full.json](2026-11-02-get-observation-rooms-examples/rest-tent-initial.full.json) | gui-remaining/rest_tent：0 |
| 锻炼后剩余选项与 Proceed 共存 | [rest-tent-after-lift.full.json](2026-11-02-get-observation-rooms-examples/rest-tent-after-lift.full.json) | gui-remaining/rest_tent：4 |
| 使用三种选项后的剩余列表 | [rest-tent-after-three-options.full.json](2026-11-02-get-observation-rooms-examples/rest-tent-after-three-options.full.json) | gui-remaining/rest_tent：8 |
| 带 Dream Catcher 的火堆 | [rest-rewards-initial.full.json](2026-11-02-get-observation-rooms-examples/rest-rewards-initial.full.json) | gui-remaining/rest_rewards：0 |
| 休息触发奖励页，火堆隐藏 | [rest-rewards-nested-rewards.full.json](2026-11-02-get-observation-rooms-examples/rest-rewards-nested-rewards.full.json) | gui-remaining/rest_rewards：3 |
| 跳过后续奖励，返回火堆 | [rest-rewards-returned.full.json](2026-11-02-get-observation-rooms-examples/rest-rewards-returned.full.json) | gui-remaining/rest_rewards：6 |

### 宝箱房

| 场景 | 完整 full JSON | 本地 evidence.json／下标 |
| --- | --- | --- |
| 尚未开箱 | [treasure-open-initial.full.json](2026-11-02-get-observation-rooms-examples/treasure-open-initial.full.json) | gui-remaining/treasure_open：0 |
| 仅开箱，遗物待领取 | [treasure-open-opened.full.json](2026-11-02-get-observation-rooms-examples/treasure-open-opened.full.json) | gui-remaining/treasure_open：3 |
| 遗物已领走 | [treasure-open-collected.full.json](2026-11-02-get-observation-rooms-examples/treasure-open-collected.full.json) | gui-remaining/treasure_open：7 |
| 宝箱前进后的地图 | [treasure-open-proceeded.full.json](2026-11-02-get-observation-rooms-examples/treasure-open-proceeded.full.json) | gui-remaining/treasure_open：10 |
| 白银熔炉场景，尚未开箱 | [treasure-empty-initial.full.json](2026-11-02-get-observation-rooms-examples/treasure-empty-initial.full.json) | gui-remaining/treasure_empty：0 |
| 已开空箱与 Proceed | [treasure-empty-opened.full.json](2026-11-02-get-observation-rooms-examples/treasure-empty-opened.full.json) | gui-remaining/treasure_empty：3 |
| 空箱前进后的地图 | [treasure-empty-proceeded.full.json](2026-11-02-get-observation-rooms-examples/treasure-empty-proceeded.full.json) | gui-remaining/treasure_empty：6 |
| 含额外奖励的未开宝箱 | [treasure-extra-initial.full.json](2026-11-02-get-observation-rooms-examples/treasure-extra-initial.full.json) | gui-extra/treasure_extra：0 |
| 开箱先弹出奖励页 | [treasure-extra-opened.full.json](2026-11-02-get-observation-rooms-examples/treasure-extra-opened.full.json) | gui-extra/treasure_extra：3 |
| 处理奖励后才显示遗物 | [treasure-extra-returned.full.json](2026-11-02-get-observation-rooms-examples/treasure-extra-returned.full.json) | gui-extra/treasure_extra：6 |
| 领取遗物后的宝箱 | [treasure-extra-collected.full.json](2026-11-02-get-observation-rooms-examples/treasure-extra-collected.full.json) | gui-extra/treasure_extra：10 |
| 额外奖励宝箱前进后的地图 | [treasure-extra-proceeded.full.json](2026-11-02-get-observation-rooms-examples/treasure-extra-proceeded.full.json) | gui-extra/treasure_extra：13 |

### 普通奖励页（保留原始可见 5 行，不补第 6 行）

```json
{
  "scene": "rewards",
  "map": null,
  "screen": {
    "status": "visible"
  },
  "turn": null,
  "player": null,
  "enemies": null,
  "allies": null,
  "top_bar": {
    "hp": 80,
    "max_hp": 80,
    "gold": 99,
    "floor": 1,
    "ascension": null,
    "deck_count": 10,
    "room_icon": null,
    "bosses": [
      "Vantom"
    ],
    "potion_slots": [
      null,
      null,
      null
    ],
    "relic_count": 1,
    "relics": [
      {
        "name": "Burning Blood",
        "counter": null,
        "melted": null
      }
    ],
    "map_visible": true,
    "deck_visible": true,
    "settings_visible": true
  },
  "buttons": null,
  "selection": null,
  "rewards": {
    "status": "visible",
    "title": "Loot!",
    "items": [
      {
        "id": 0,
        "type": "gold",
        "text": "17 Gold",
        "enabled": true,
        "linked_group": null
      },
      {
        "id": 1,
        "type": "gold",
        "text": "23 Gold (stolen back)",
        "enabled": true,
        "linked_group": null
      },
      {
        "id": 2,
        "type": "potion",
        "text": "Block Potion",
        "enabled": true,
        "linked_group": null
      },
      {
        "id": 3,
        "type": "relic",
        "text": "Whetstone",
        "enabled": true,
        "linked_group": null
      },
      {
        "id": 4,
        "type": "special_card",
        "text": "Add Strike+ to your deck.",
        "enabled": true,
        "linked_group": null
      }
    ],
    "proceed": {
      "text": "Skip",
      "enabled": true,
      "skips_remaining": true
    }
  },
  "rest_site": null,
  "treasure": null,
  "shop": null,
  "ancient": null,
  "event": null,
  "divination": null,
  "confirmation": null,
  "epilogue": null,
  "run_result": null,
  "available_actions": [
    "claim_reward",
    "proceed",
    "inspect_potions",
    "inspect_relics",
    "inspect_deck",
    "inspect_map",
    "inspect_rewards"
  ]
}
```

### 普通火堆选项页

```json
{
  "scene": "rest_site",
  "map": null,
  "screen": {
    "status": "visible"
  },
  "turn": null,
  "player": null,
  "enemies": null,
  "allies": null,
  "top_bar": {
    "hp": 30,
    "max_hp": 80,
    "gold": 99,
    "floor": 2,
    "ascension": null,
    "deck_count": 10,
    "room_icon": null,
    "bosses": [
      "Vantom"
    ],
    "potion_slots": [
      null,
      null,
      null
    ],
    "relic_count": 1,
    "relics": [
      {
        "name": "Burning Blood",
        "counter": null,
        "melted": null
      }
    ],
    "map_visible": true,
    "deck_visible": true,
    "settings_visible": true
  },
  "buttons": null,
  "selection": null,
  "rewards": null,
  "rest_site": {
    "status": "visible",
    "prompt": "What shall I do?",
    "description": null,
    "options": [
      {
        "id": "HEAL",
        "text": "Rest",
        "enabled": true
      },
      {
        "id": "SMITH",
        "text": "Smith",
        "enabled": true
      }
    ],
    "proceed": null
  },
  "treasure": null,
  "shop": null,
  "ancient": null,
  "event": null,
  "divination": null,
  "confirmation": null,
  "epilogue": null,
  "run_result": null,
  "available_actions": [
    "choose_rest_option",
    "inspect_potions",
    "inspect_relics",
    "inspect_deck",
    "inspect_map",
    "inspect_rest_site"
  ]
}
```

### 宝箱已开且遗物待领取

```json
{
  "scene": "treasure",
  "map": null,
  "screen": {
    "status": "visible"
  },
  "turn": null,
  "player": null,
  "enemies": null,
  "allies": null,
  "top_bar": {
    "hp": 80,
    "max_hp": 80,
    "gold": 143,
    "floor": 2,
    "ascension": null,
    "deck_count": 10,
    "room_icon": null,
    "bosses": [
      "Vantom"
    ],
    "potion_slots": [
      null,
      null,
      null
    ],
    "relic_count": 1,
    "relics": [
      {
        "name": "Burning Blood",
        "counter": null,
        "melted": null
      }
    ],
    "map_visible": true,
    "deck_visible": true,
    "settings_visible": true
  },
  "buttons": null,
  "selection": null,
  "rewards": null,
  "rest_site": null,
  "treasure": {
    "status": "visible",
    "chest": "open",
    "relic": {
      "name": "Anchor",
      "enabled": true
    },
    "proceed": {
      "text": "Skip",
      "enabled": true,
      "skips_remaining": true
    }
  },
  "shop": null,
  "ancient": null,
  "event": null,
  "divination": null,
  "confirmation": null,
  "epilogue": null,
  "run_result": null,
  "available_actions": [
    "loot_treasure",
    "proceed",
    "inspect_potions",
    "inspect_relics",
    "inspect_deck",
    "inspect_map",
    "inspect_treasure"
  ]
}
```

## 验证结果与未覆盖范围

- 共 11 类夹具完成采样与正常局清理，145 次真实 MCP 调用，37 份完整 full JSON 逐对象等于原始证据，通过当前 observation_details 校验；所有相邻截图存在。三个自有游戏 PID 均已退出。
- 成功证据由 gui/reward_basic、gui-remaining 的前 9 类和 gui-extra/treasure_extra 组成，最后一批总报告 passed。前两批总报告均保留 failed，不能描述为整批通过：gui 的满栏夹具在跳过未领完奖励后清理超时，补跑先腾药水槽、领完再清理；gui-remaining 的采样脚本在非终结奖励自动返回后多点一次 proceed，补采时删除这次多余调用。没有修改生产读取、动作或夹具代码。原因与处理见本地[采样问题报告](../../.tmp/2026-11-02-observation-rooms-review-report.md)。
- 本轮仅修改调研文档和实测样本，不改公共参数、summary、Mod 或 schema；未重跑与本次文档无关的单元测试，未安装正式游戏 Mod。
- 上文明确标注为源码分支的标题／类型、禁用／动画、其他火堆选项、特殊遗物、多人与教程并未穷举 GUI。本轮只确认当前已有结构，不承诺所有组合都有样本，也不把专用 inspect 工具返回当作基础 full。
