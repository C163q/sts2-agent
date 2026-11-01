# 先古之民

适用于 Mod `0.34.2`、MCP `0.29.1`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。支持实际单人的常规先古之民房间，使用原生对话及事件选项流程；不自动选择遗物或前往地图节点。终章建筑师使用[终章接口](run-ending.md)，与常规先古之民共用 `advance_dialogue`。普通问号事件使用[通用事件工具](events.md)。

## 工具与观察

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | `scene: "ancient"` 和 `ancient` 对象；只列已经显示的对话和选项 |
| `inspect_ancient()` | 读取当前选项正文及原生悬停解释，不推进对话或提前查看领取结果 |
| `advance_dialogue()` | 点击原生对话继续区域一次，不选择遗物 |
| `choose_ancient_option({"option_id":0})` | 点击一个启用的当前选项；可能立即生效，也可能停在选牌或奖励 |
| `proceed()` | 点击先古之民原生前进选项，通常打开地图，不选择节点 |

`ancient` 字段：

- `status`：`visible` 或 `covered`。覆盖时其余字段全部为 `null`。
- `name`、`epithet`、`description`：先古名称、已显示的称号及当前说明，原生无说明时为 `null`。
- `dialogue`：当前可见的对话行，每项有英语 `speaker`、`text`。不返回未显示的后文。
- `options`：当前显示的选项，每项有稳定整数 `id`、`title`、`description`、`enabled`。正文已在界面展开，基础观察可以提供；`inspect_ancient` 增加逐项 `hover_tips`。通常为遗物三选一，但不固定数量或强制要求选项包含遗物。
- `continue`、`proceed`：当前按钮的 `text`、`enabled`，没有时为 `null`。对话未完成、动画、领取进行中或原生锁定时不允许选项动作。

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
  },
  "available_actions": ["choose_ancient_option", "inspect_potions", "inspect_relics", "inspect_map", "inspect_ancient"]
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

动作需要当前观察许可，条件与[其他 MCP 动作](mcp.md#调用和错误语义)相同。选项 ID 按当前实际选项身份分配，原生翻页后旧 ID 不再匹配。详情成功时刷新状态令牌；覆盖页不允许穿透点击。普通完成返回 `action_completed`；选牌返回 `choice_required`；嵌套奖励通过场景和可用工具标识，内容按需观察或查看奖励。超时不自动重试。

到达房间、继续对话及返回页面时，可行动条件还检查原生内容滚动、说明淡入、名称横幅显隐及其入场补间。选项已经能点击，不代表称号等可见字段已经稳定；须等这些有限过渡结束后才报告可行动。称号仍按当时的实际可见性输出，状态指纹不忽略它；成功详情后可直接选择，不要求额外调用 `get_observation`。复现和验证见[先古之民入场稳定性修复](../research/2026-11-01-ancient-stability.md)。

图形验证须使用[隔离测试实例](roundtrip.md)，例如：

```sh
python3 scripts/run_roundtrip.py --windowed --ancient-scenario shrymp
```

另一终端执行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_ancients.py --scenario shrymp --report .tmp/ancient-check/shrymp.json
```

报告及截图路径必须全新；测试会真实选择遗物、选牌并进入隔离战斗，不得指向正式对局。源码依据、验证记录及限制见[本次核对](../research/2026-10-31-ancients.md)。
