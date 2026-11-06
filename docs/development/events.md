# 问号房与通用事件

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持目标版本单人的原生默认事件和战斗背景事件；实际出现的战斗、商店、宝箱继续使用对应工具。问号是地图节点图标，不代表房内交互类型。

下文输出字段的空值与 JSON 示例以底层文件或 MCP full 为准；MCP 工具另接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

## 工具

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | 返回当前事件名称、选项效果、启用状态及原生致死警告 |
| `inspect_event(preset?, include_image?)` | full/default 提供当前事件正文及可悬停选项的 `hover_tips`；summary 使用共用静态摘要；include_image 用于占卜 |
| `choose_event_option({"option_id":0})` | 点击一个已观察到且启用的原生选项 |
| `respond_to_confirmation({"option":"cancel"})` | 点击当前 Trial 原生确认框的取消；`confirm` 确认放弃本局 |
| `proceed()` | 点击事件完成后的原生前进按钮，通常打开地图 |

选项参数必须是非负的 32 位整数，不接受布尔值、字符串或额外字段。ID 绑定真实选项，翻页后必须使用新页面返回的 ID。动作需要[当前观察许可](mcp.md#调用和错误语义)，基础观察、成功详情、视图操作及满足续接条件的动作结果均可提供当前状态令牌，无需额外基础观察。

## 基础观察与详情

以下为 inspect_event.full 的深渊浴场初始页面主体示例片段，省略通用顶栏和其他场景的空字段：

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
  }
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

get_observation 的 full/default/summary 均使用 inspect_event.summary 的静态事件主体：省略页面叙事 event.description、hover_tips 和值为 false 的 lethal_warning，保留选项效果 description、true 警告、锁定状态及继续按钮。inspect_event.full/default 提供已展示正文与可悬停解释；default 另执行共用空值过滤。读取拒绝提供具体原因，已有许可的明确读取拒绝保留合法后续操作；事件选项的静态列表不按视口坐标截断。完整规则见[观察预设](observation.md#mcp-输出预设)。

## 后续交互与结算

事件使用原生按钮和 `EventSynchronizer`，不根据选项文字自行扣血、发钱或给牌。点击后返回[精简动作回执](mcp.md#动作返回格式)，语义与[共享动作边界](end-turn.md#动作完成与画面稳定)一致。

| 停止原因 | 后续处理 |
| --- | --- |
| `action_completed` | 下一页事件、完成后的前进、奖励或地图已可交互 |
| `choice_required` | 使用现有 `inspect_selection`、`select_card`、`selection_option` 处理选择 |
| `player_ready` | 已进入战斗且玩家可以行动，继续使用战斗工具 |
| `combat_won` / `combat_lost` | 事件引入的战斗已由原生流程确认胜负 |
| `run_lost` | 战斗外整局失败；结算显示后以原生结算胜负为准，不以短暂零血或剧情死亡回调判死，见[终章结算](run-ending.md) |
| `manual_input_required` | 当前专属界面尚未支持，停止自动操作 |
| `timeout` / `interrupted` | 结果不完整；重新观察，禁止自动重发动作 |

支持移除、升级、附魔、变形、简单网格和多选等现有[选牌界面](card-selection.md)，以及卡牌、药水和其他原生[奖励](rewards.md)。父事件可能仍在等待这些输入，不能把父任务未完成当作不可操作；结束选择后则继续等待父效果及卡牌预览、资源显示稳定。

只列出原生允许的取消入口。升级预览的返回与取消整个选择是两件事；例如 Aroma of Chaos 的升级选择允许退回预览前重新选牌，但没有取消整次选择的按钮。

从事件进入战斗时，在战斗开始钩子和首回合自动效果之前开始记录。第一回合若需要选牌或已经结束战斗，按实际边界返回。战斗奖励的 `proceed` 保留原生房间恢复流程，例如 Battleworn Dummy 会返回父事件，并继续发药水、升级或给遗物；不会强制改成打开地图。事件初始化、选项和 `Resume` 任务都纳入结算检查。

奖励页可以按原生规则腾出药水槽；父事件仍在结算且没有可操作子奖励页时，不允许抢先使用或丢弃药水。事件自身的禁止移除药水规则仍由原生流程决定。

## 专属界面与限制

假商人沿用[商店接口](shop.md)，不额外暴露隐藏身份。[占卜小游戏](divination.md)支持文字棋盘、可选图片、大小工具、揭开与原生奖励结算。

### 事件确认弹窗

Trial 第二次拒绝会打开原生放弃本局确认框。`get_observation` 提供标题、正文及两个按钮，不需要额外详情工具。触发弹窗的动作回执通过 `screen.view: "confirmation"` 和 `available_actions` 标识当前交互；决定确认或取消前按需观察。以下为MCP full的确认框字段示例：

```json
{
  "scene": "event",
  "screen": {"status": "visible", "view": "confirmation"},
  "event": {
    "status": "covered",
    "name": null,
    "options": null,
    "proceed": null
  },
  "confirmation": {
    "status": "visible",
    "type": "abandon_run",
    "title": "Are you sure?",
    "description": "Abandoning the game will result in a loss.",
    "options": [
      {"id": "confirm", "text": "Yes", "enabled": true},
      {"id": "cancel", "text": "No", "enabled": true}
    ]
  },
  "available_actions": ["respond_to_confirmation"]
}
```

弹窗入场完成后，触发动作返回 `transition.stop_reason: "action_completed"` 和 `complete: true`。后续明确调用：

```json
{"option":"cancel"}
```

`respond_to_confirmation` 的 `option` 仅接受 `cancel` 或 `confirm` 字符串，不接受额外字段。取消点击原生 No，等待遮罩退出后返回原事件；可以直接复用结果，再点 Double Down 打开新确认框。确认点击原生 Yes，走 `RunManager.Abandon`，等待原生失败信号和放弃任务完成，返回 `run_lost`、`complete: true`、空动作列表；不自动点击失败画面的后续按钮，装饰动画仍可能继续。

`confirmation` 在没有受支持弹窗时为 `null`。操作只接受由当前单人 Trial 事件实际打开、仍属于同一对局的原生弹窗，主菜单或设置打开的同类型弹窗不会因此得到支持。外部取消后再打开同样文字的新弹窗会使旧观察失效。遮挡期间底层事件、顶栏、地图及药水操作不可用。

未知弹窗继续返回覆盖状态、空动作列表及人工输入说明；触发动作返回 `manual_input_required`。工具不自动确认或取消任何弹窗。

终章建筑师使用[终章接口](run-ending.md)。多人、第三方事件及其他专属 UI 未接通。注册事件数量及源码分类见[调研](../research/2026-10-31-events.md)，不代表所有事件、分支和遗物组合均已实测。

## 验证入口

先按[测试指南](roundtrip.md)编译并准备隔离实例。例如启动茶师事件：

```sh
python3 scripts/run_roundtrip.py --windowed --event-scenario tea
```

另一终端运行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_events --scenario tea --report .tmp/event-check/tea.json
```

使用全新报告和截图路径。验证会真实点击、购买或选择，不得连接正式对局。源码依据见[调研](../research/2026-10-31-events.md)，实际验证及限制见[验证记录](../research/2026-10-31-events-validation.md)。

确认框使用 `--event-scenario trial` 启动新的隔离实例，运行 `tests/game/verifiers/verify_confirmation.py --scenario cancel|confirm --report <新路径>`；两个场景须分别启动实例。`confirm` 会结束该测试对局。结果见[确认弹窗验证](../research/2026-10-31-event-confirmation-validation.md)。
