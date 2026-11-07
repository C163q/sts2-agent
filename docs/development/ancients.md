# 先古之民

页面主体的visible／not_ready／covered及部分内容提示遵循[共用展示状态](observation.md#页面主体的展示状态)，按钮可操作性另行判断。

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持实际单人的常规先古之民房间，使用原生对话及事件选项流程；不自动选择遗物或前往地图节点。终章建筑师使用[终章接口](run-ending.md)，与常规先古之民共用 `advance_dialogue`。普通问号事件使用[通用事件工具](events.md)。

下文输出字段的空值与 JSON 示例以底层文件或 MCP full 为准；MCP 工具另接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

get_observation 的 full/default/summary 共用 inspect_ancient.summary 的静态先古主体；共用顶栏及选牌仍按[观察预设](observation.md#mcp-输出预设)独立处理。

## 工具与观察

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | `scene: "ancient"` 和 `ancient` 对象；只列已经显示的对话和选项 |
| `inspect_ancient(preset?, option_ids?)` | 读取已展示对话、馈赠正文及悬停解释；summary省略悬停解释，option_ids按当前选项ID筛选 |
| `advance_dialogue()` | 点击原生对话继续区域一次，不选择遗物 |
| `choose_ancient_option({"option_id":0})` | 点击一个启用的当前选项；可能立即生效，也可能停在选牌或奖励 |
| `proceed()` | 点击先古之民原生前进选项，通常打开地图，不选择节点 |

`ancient` 字段：

- `status`：`visible`、`not_ready` 或 `covered`。覆盖时其余字段全部为 `null`。
- `name`、`epithet`、`description`：先古名称、已显示的称号及当前说明，原生无说明时为 `null`。
- `dialogue`：当前可见的对话行，每项有英语 `speaker`、`text`。不返回未显示的后文。
- `options`：当前显示的选项，每项有稳定整数 `id`、`title`、`description`、`enabled`。正文已在界面展开，基础观察可以提供；`inspect_ancient` 增加逐项 `hover_tips`。通常为遗物三选一，但不固定数量或强制要求选项包含遗物。
- `options[].lethal_warning`：原生选项的致死红框判断，来自游戏回调。详情full/default保留true/false，summary及基础观察仅保留true；旧schema缺失此字段时不补造false。
- `continue`、`proceed`：当前按钮的 `text`、`enabled`，没有时为 `null`。对话未完成、动画、领取进行中或原生锁定时不允许选项动作。

`inspect_ancient`成功结果包含同次快照的`scene`、`screen`和`ancient`，要求当前先古页面可见。无房间、非单人及覆盖页拒绝给出具体原因；地图／牌组覆盖提示关闭工具，选牌／奖励覆盖提示对应详情工具。完整响应的页面、字段和悬停来源先校验，再进行筛选及预设投影。

预设支持default、full、summary，默认default。full保留空值；default应用[通用空值规则](mcp.md#输出预设)；summary在default基础上省略全部hover_tips及false警告，保留页面说明、已展示对话、馈赠效果正文及按钮。

option_ids接受非负Int32数组：省略或null取全部，[]返回空options；保留页面顺序、对话和按钮，重复ID去重。缺失ID合并到`errors:[{code:"option_ids_not_found",option_ids:[...]}]`，匹配项照常返回。选项已有稳定ID，无须返回筛选后位置映射。

文字及馈赠读取不按视口截断，仍排除真实隐藏、透明、裁剪和未揭示内容。可见而不能悬停的选项保留正文，完整详情返回空hover_tips，并通过`notes.hover_tips_unavailable.sources`给出`ancient.options.<id>`；note随筛选缩小，summary省略此类note。点击仍检查按钮在屏幕内且可操作。

例如已展开的选项摘要：

```json
{
  "scene": "ancient",
  "ancient": {
    "status": "visible",
    "name": "Orobas",
    "epithet": null,
    "description": null,
    "dialogue": [],
    "options": [
      {
        "id": 0,
        "title": "Touch of Orobas",
        "description": "Replace Burning Blood with Black Blood.",
        "enabled": true
      }
    ],
    "continue": null,
    "proceed": null
  }
}
```

示例省略通用顶栏和其他空观察字段，选项数组仅展示一项，不表示该先古只提供一个选项。实际 ID 以当次观察为准。后续选牌使用[现有选择工具](card-selection.md)，额外奖励使用[搜刮工具](rewards.md)，可以逐项决定顺序。

## 遗物效果与其他场景

不为每件遗物实现一套规则。游戏自身负责领取回调、自动出牌、额外回合、返还卡牌、附魔和商店等 hook；工具识别真实 UI 和可行动边界。选择或奖励会暂停领取任务，此时及时返回，不能等到整个领取结束才输出。

| 遗物 | 原生行为与接口衔接 |
| --- | --- |
| 低语耳环 `WhisperingEarring` | 最大能量加一；首次回合的自动出牌阶段由瓦库依次出牌，至无可出牌等条件停止，最多13张。其专用原生 selector 会自动处理期间选牌。接口不代替它做选择，也不擅自结束该回合；原生流程结束后仍可能让玩家手动操作。 |
| 欧洛巴斯之触 `TouchOfOrobas` | 将起始遗物替换为对应增强版；选项描述和悬停解释反映本角色对应物。领取后顶栏和 `inspect_relics` 反映真实持有项。 |
| 佩尔之眼 `PaelsEye` | 首次满足条件的“未手动出牌”回合结束时消耗手牌，获得额外玩家回合；`end_turn` 等到该回合可操作，无须虚构一次敌人行动。原生对自动出牌及低语耳环有额外判定。 |
| 佩尔之牙 `PaelsTooth` | 领取时原生筛选可移除、可升级的牌，最多移除5张；复用多选及确认。存储的随机卡牌在战后返还并升级，由游戏原生 hook 决定，不提前返回随机结果。 |
| 放电异虾 `ElectricShrymp` | 为技能牌选择注能附魔，复用 `deck_enchant` 和真实预览；该牌在首回合的自动阶段打出。 |

其他已接通的 UI 包括附魔多选、随机/指定变牌、卡牌包预览、潘多拉魔盒结果确认，以及嵌套奖励。先古遗物引发的[休息处](rest-site.md)、[宝箱](treasure.md)及[商店](shop.md)行为继续复用对应工具。任意第三方 UI、所有遗物组合与其他游戏版本尚未穷尽验证；遇到未支持的交互仍明确返回 `manual_input_required`，不自动代选。

## 状态与验证

动作需要当前观察许可，条件与[其他 MCP 动作](mcp.md#调用和错误语义)相同。选项 ID 按当前实际选项身份分配，原生翻页后旧 ID 不再匹配。详情成功时刷新状态令牌；确定性读取拒绝保留已有许可，不为首次失败建立许可。覆盖页不允许穿透点击。普通完成返回 `action_completed`；选牌返回 `choice_required`；嵌套奖励通过场景和可用工具标识，内容按需观察或查看奖励。超时不自动重试。

choose_ancient_option和advance_dialogue在明确点击前拒绝且未改UI时保留已有许可，可直接改选、推进对话、处理选牌／奖励或前进。错误区分无房间、覆盖、等待、对话未完成／已结束、已领取、无效ID及按钮不可用，并提示对应工具。地图和牌组关闭工具本身不要求玩法许可。过期观察、已交互、未知或坏响应仍要求重新读取。

页面、馈赠及对话可用性由AncientInspection集中维护，执行、按钮enabled及available_actions共用。advance_dialogue只推进一句，等下一可操作状态稳定后返回action_completed；最后一句启用馈赠选择，后续使用choose_ancient_option。普通翻句events为空，当前台词按需通过get_observation或inspect_ancient读取。

已识别的原生选牌页在进入／退出过渡中，仍真实画出的顶栏继续参与资源及物品事件采样。卡牌包打开时记录已显示的Scroll Boxes获取一次，未选定包内卡牌不提前记录加入；真实隐藏UI的变动仍不公开，恢复显示也不回放隐藏期间事件。

致死斗篷在隔离环境有致命错误，用户也报告原版崩溃；现按原版可复现问题记录，Mod及MCP不是发生崩溃的必要条件，底层根因仍未确定。[用户TODO](TODO.md)要求游戏升级至v0.111后复测。原审阅和反馈来源见[选择馈赠核验](../research/2026-11-07-choose-ancient-option-review.md)。

到达房间、继续对话及返回页面时，可行动条件还检查原生内容滚动、说明淡入、名称横幅显隐及其入场补间。选项已经能点击，不代表称号等可见字段已经稳定；须等这些有限过渡结束后才报告可行动。称号仍按当时的实际可见性输出，状态指纹不忽略它。详情可以在过渡中读取已显示内容，此时选项的`enabled`可能为false；成功详情中选项为`enabled:true`时可直接选择，不要求额外调用 `get_observation`。复现和验证见[先古之民入场稳定性修复](../research/2026-11-01-ancient-stability.md)及[详情核验](../research/2026-11-07-inspect-ancient-development-notes.md)。

图形验证须使用[隔离测试实例](roundtrip.md)，例如：

```sh
python3 scripts/run_roundtrip.py --windowed --ancient-scenario shrymp
```

另一终端执行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_ancients --scenario shrymp --report .tmp/ancient-check/shrymp.json
```

报告及截图路径必须全新；测试会真实选择遗物、选牌并进入隔离战斗，不得指向正式对局。源码依据、验证记录及限制见[源码与验证记录](../research/2026-10-31-ancients.md)。
