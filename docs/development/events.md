# 问号房与通用事件

适用于 Mod `0.27.0`、MCP `0.23.0`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10`。支持目标版本单人的原生默认事件和战斗背景事件；实际出现的战斗、商店、宝箱继续使用对应工具。问号是地图节点图标，不代表房内交互类型。

## 工具

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | 返回当前事件正文、选项、启用状态和原生致死警告 |
| `inspect_event()` | 增加当前可悬停选项的 `hover_tips`，不推进页面、选项或 RNG |
| `choose_event_option({"option_id":0})` | 点击一个已观察到且启用的原生选项 |
| `proceed()` | 点击事件完成后的原生前进按钮，通常打开地图 |

选项参数必须是非负的 32 位整数，不接受布尔值、字符串或额外字段。ID 绑定真实选项，翻页后必须使用新页面返回的 ID。动作需要[当前观察许可](mcp.md#调用和错误语义)，可直接复用完整成功的动作返回；详情不新建许可，切换查看页后须重新观察。

## 基础观察与详情

以下为深渊浴场初始页面的示例片段，省略通用顶栏和其他场景的空字段：

```json
{
  "scene": "event",
  "screen": {"status": "visible"},
  "event": {
    "status": "visible",
    "name": "Abyssal Baths",
    "description": "You discover a secluded chamber.",
    "options": [
      {
        "id": 0,
        "title": "Immerse",
        "description": "Gain 2 Max HP. Take 3 damage.",
        "enabled": true,
        "lethal_warning": false
      },
      {
        "id": 1,
        "title": "Abstain",
        "description": "Heal 10 HP.",
        "enabled": true,
        "lethal_warning": false
      }
    ],
    "proceed": null
  },
  "available_actions": ["choose_event_option"]
}
```

示例正文仅摘取首句，不是额外的摘要模式；实际返回完整的当前已展示正文。ID、数值和危险标记以当次观察为准。

- `event.status` 为 `visible` 或 `covered`。被选牌、奖励、地图、占卜或弹窗覆盖时，其余事件字段全部为 `null`，不能穿透读取或点击。
- `name`、`description` 只来自已经显示的当前页面；正文渐显未结束时先返回 `null` 并禁用选项动作，等待完成后才返回完整英文正文。
- `options` 包含当前已显示的选项，包括锁定项。`enabled` 合并原生按钮规则与结算忙碌状态，不按文本猜测可用性。
- `lethal_warning` 对应原生红框，表示界面上的危险警告，不承诺穷尽复活机制或断言必死。单人允许按原生规则选择危险项，工具不代替决策。
- `inspect_event` 为每项增加 `hover_tips` 数组；锁定或当前不可悬停的按钮返回空数组。不提前透露未显示页面、未打开的奖励或随机结果。
- `proceed` 为完成事件后生成的原生按钮，含 `text`、`enabled`，没有时为 `null`。普通“继续”“离开”“战斗”仍是选项；原生内部 `IsProceed` 标志不能单独决定工具分类。

事件英文格式化保留变量及嵌套正文的真实来源，按引用追踪赋值与克隆，在分离数据上读取；不修改原有语言、变量、选项或随机状态。升级牌名保留当前已公开的 `+`/`+N`。

## 后续交互与结算

事件使用原生按钮和 `EventSynchronizer`，不根据选项文字自行扣血、发钱或给牌。点击后返回最终观察及 `transition`，语义与[共享动作边界](end-turn.md#动作完成与画面稳定)一致。

| 停止原因 | 后续处理 |
| --- | --- |
| `action_completed` | 下一页事件、完成后的前进、奖励或地图已可交互 |
| `choice_required` | 使用现有 `inspect_selection`、`select_card`、`selection_option` 处理选择 |
| `player_ready` | 已进入战斗且玩家可以行动，继续使用战斗工具 |
| `combat_won` / `combat_lost` | 事件引入的战斗已由原生流程确认胜负 |
| `run_lost` | 原生 `RunManager.OnEnded(false)` 确认战斗外整局失败；不以短暂零血判死 |
| `manual_input_required` | 当前专属界面尚未支持，停止自动操作 |
| `timeout` / `interrupted` | 结果不完整；重新观察，禁止自动重发动作 |

支持移除、升级、附魔、变形、简单网格和多选等现有[选牌界面](card-selection.md)，以及卡牌、药水和其他原生[奖励](rewards.md)。父事件可能仍在等待这些输入，不能把父任务未完成当作不可操作；结束选择后则继续等待父效果及卡牌预览、资源显示稳定。

只列出原生允许的取消入口。升级预览的返回与取消整个选择是两件事；例如 Aroma of Chaos 的升级选择允许退回预览前重新选牌，但没有取消整次选择的按钮。

从事件进入战斗时，在战斗开始钩子和首回合自动效果之前开始记录。第一回合若需要选牌或已经结束战斗，按实际边界返回。战斗奖励的 `proceed` 保留原生房间恢复流程，例如 Battleworn Dummy 会返回父事件，并继续发药水、升级或给遗物；不会强制改成打开地图。事件初始化、选项和 `Resume` 任务都纳入结算检查。

奖励页可以按原生规则腾出药水槽；父事件仍在结算且没有可操作子奖励页时，不允许抢先使用或丢弃药水。事件自身的禁止移除药水规则仍由原生流程决定。

## 专属界面与限制

假商人沿用[商店接口](shop.md)，不额外暴露隐藏身份。[占卜小游戏](divination.md)支持棋盘图像、大小工具、揭开与原生奖励结算。Trial 确认弹窗仍只识别，不操作：

```json
{
  "scene": "event",
  "screen": {"status": "covered", "view": "confirmation"},
  "event": {
    "status": "covered",
    "name": null,
    "description": null,
    "options": null,
    "proceed": null
  },
  "available_actions": [],
  "notes": {"interaction": "A native dialog or unsupported screen requires manual input."}
}
```

动作还返回 `transition.stop_reason: "manual_input_required"`；之后单独调用观察也保留明确的页面标识及说明。确认框不自动确认或取消。

终章 The Architect、多人、第三方事件及专属 UI 和确认框操作未接通。注册事件数量及源码分类见[调研](../research/2026-10-31-events.md)，不代表所有事件、分支和遗物组合均已实测。

## 验证入口

先按[测试指南](roundtrip.md)编译并准备隔离实例。例如启动茶师事件：

```sh
python3 scripts/run_roundtrip.py --windowed --event-scenario tea
```

另一终端运行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_events.py --scenario tea --report .tmp/event-check/tea.json
```

使用全新报告和截图路径。验证会真实点击、购买或选择，不得连接正式对局。源码依据见[调研](../research/2026-10-31-events.md)，实际验证及限制见[验证记录](../research/2026-10-31-events-validation.md)。
