# get_observation：占卜、确认框与建筑师终章

> 当前状态：13–15 组现状核验已交付，共 3 组，已完成源码核对及 5 类隔离 GUI 采样，收录 47 份完整 full、19 张同次棋盘 PNG 和 1 份已知错误响应。建筑师牌组覆盖校验已由 MCP 0.50.5 修复并验证；summary 约定已确认，新增占卜说明省略尚待实现。后续功能另列[用户待办](../development/TODO.md)，get_observation 整体不核销。总进度见[场景目录](2026-11-02-get-observation-review.md)。

## 范围与证据

- 核对日期：2026-11-03；代码基线 `a561f5b`，MCP `0.50.4`、Mod `0.49.2`、原生 schema `31`。
- 目标：Linux 游戏 `v0.107.1`、release `59260271`、RitsuLib `0.6.10`。安装目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 已准备隔离 Mod 的 SHA-256 为 `1d1a7e8c180bbb05b15f3ee8a5dbbf098485685dda393466eb3e5356e6d403ed`；本轮不重新编译、不安装至正式游戏。
- 原生类型从上述程序集重新反编译，保存在未纳入 Git 的 `.tmp/2026-11-03-observation-special-review/source/`；类型和程序集校验值见该目录 `provenance.json`。
- 原生观察：[占卜](../../src/Sts2Agent/Observation/DivinationInspection.cs)、[确认框](../../src/Sts2Agent/Actions/EventConfirmation.cs)、[终章](../../src/Sts2Agent/Observation/EpilogueInspection.cs)；组装与工具列表见 [GameAdapter](../../src/Sts2Agent/Adapter/GameAdapter.cs) 和 [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- 公开转换：[player_output.py](../../src/sts2_mcp/output/player_output.py)、[占卜图像校验](../../src/sts2_mcp/output/divination_details.py)、[观察预设](../../src/sts2_mcp/output/observation_presets.py)。现行契约见[占卜](../development/divination.md)、[事件确认框](../development/events.md#事件确认弹窗)、[终章与结算](../development/run-ending.md)。

本轮沿用[工具核验流程](2026-11-02-mcp-tool-review.md#逐项工作流程)：展示完整 full 后讨论 summary。观察不会自动推进对话、揭开格子或接受确认；`transition` 和 `stop_reason` 属于动作回执，不属于 `get_observation`。

## 13：占卜

### 场景及字段

底层 `scene` 仍为 `event`。棋盘展开时 `screen.view: divination`，底层 `event.status: covered`；不能把原事件选项或正文与当前棋盘同时当作可见内容。

| 字段 | full 当前含义与边界 |
| --- | --- |
| `divination.status` | `visible` 或 `covered`；覆盖时其他占卜字段全部为 null，不带棋盘图片 |
| `phase` | `playing` 为可继续占卜；`settling` 为展示或效果结算尚未稳定；`finished` 为原生小游戏结束且已就绪 |
| `remaining` | 仅在次数控件可见时读取；终结页控件隐藏后为 null，不能补成 0 |
| `tool` | 当前 `big/small`；工具控件隐藏后为 null |
| `tools` | 两个原生工具按钮的 `id/text/enabled`；隐藏时为 null，按钮就绪与当前选中工具是两回事 |
| `instructions` | 当前可见的教学标题与完整说明；结束后隐藏，为 null |
| `dialogue` | 当前完整显示且仍可见的英文对白；打字中、已消失或被覆盖为 null，不保留对白历史 |
| `grid` | 11×11；`covered_rows` 按行给出 `#` 未揭开和 `.` 已揭开，另有棋盘 PNG 的实际尺寸 |
| `proceed` | 仅在原生前进按钮已显示时提供文字与 enabled；不能因次数耗尽提前出现 |
| `notes.divination` | 棋盘坐标与符号说明；左上 `(0,0)`，x 向右、y 向下 |

JSON 后另有一个 `ImageContent` PNG，来自当次渲染棋盘的矩形裁剪。它保留雾、已揭开的图案及局部碎片；JSON 不附送雾下物品身份、占地范围、奖励结果或 RNG。`grid.image` 只有尺寸，不能代替图片。坐标与图片按 11 等分对应，不能固定像素尺寸。

原生 `NCrystalSphereScreen.OnMinigameFinished` 隐藏工具、次数和教学说明，显示前进按钮；`CrystalSphereMinigame.CompleteMinigame` 先等待延迟并走奖励同步，再发出结束信号。因此次数耗尽与 `finished` 不是同一时刻；奖励或选牌覆盖棋盘时必须先处理当前页面。

### 已识别的返回分支

1. 普通事件选项：支付金币取得 3 次，或获得诅咒取得 6 次。此时尚未打开棋盘，`divination:null`。
2. `playing`：大／小工具、完整或部分揭开的棋盘；切换工具不消耗次数，小范围揭一格，大范围揭以目标为中心、在边界裁剪的 3×3。
3. `settling`：棋盘仍可见但揭开动画、原生任务、资源变化等未完成；可保留可见棋盘，暂不提供占卜动作。
4. 地图或牌组覆盖：棋盘字段隐藏且无 PNG；关闭覆盖恢复原进度。顶栏沿共用读取规则独立判断。
5. 奖励列表及卡牌奖励选择：当前奖励或候选可读，占卜为 covered；处理完毕后回到结束棋盘。
6. `finished`：棋盘仍有 PNG；次数、工具及说明隐藏，原生前进可用。前进后退出占卜，回到地图。

未发现这里有可滚动列表被按视口截断的问题。棋盘本身是固定 11×11 区域；对白完整显示、覆盖与淡入淡出的判断属于信息边界，不能按“可浏览列表”规则取消。

## 14：确认框与人工输入

### 支持范围

当前专门支持 **审判（Trial）事件再次拒绝后打开的放弃本局确认框**。原生 `Trial.DoubleDown` 使用通用 `NAbandonRunConfirmPopup.Create(null)`；本项目在这个调用点记录当前事件与对局的来源，再对仍属于该对局的弹窗提供操作。

不能仅按弹窗类名判断支持：同类窗口也用于菜单或其他放弃入口。来源不匹配时 `confirmation:null`，不提供 `respond_to_confirmation`，保留人工输入边界；工具不会自动选择确认或取消。

| 字段 | 受支持弹窗的 full 返回 |
| --- | --- |
| `scene` | `event`，不会变成新的 confirmation 场景 |
| `screen` | `status:visible, view:confirmation` |
| `confirmation.status/type` | `visible` / `abandon_run` |
| `title/description` | 原生当前可见的确认标题与正文，英文转写 |
| `options` | `confirm/cancel` 两个按钮的 `id/text/enabled` |
| `event` | `status:covered`，其余字段为 null |
| `top_bar` | null，当前模态读取规则不提供弹窗后的顶栏观察 |
| `available_actions` | 就绪时只有 `respond_to_confirmation`；入场未完成时不提供动作 |

`respond_to_confirmation` 参数名是 `option`，值为 `confirm/cancel`，不能把观察中的 options 数组下标当作参数。取消回原事件；确认走原生 `RunManager.Abandon`，结束该局，动作回执为 `run_lost`，后续结算观察另读。

### 人工输入分支

已识别但不受支持的同类弹窗使用 `screen.status:covered, view:confirmation`、`confirmation:null`、空 `available_actions`，并附 `notes.interaction`。这个 null 表示没有可供工具读取／操作的受支持确认框，不能等同于“现在没有弹窗”。

`confirmation-cancel-unowned.full.json` 由仅测试入口 `open_test_unowned_confirmation` 触发：先取消正常审判确认框，再由 [ConfirmationFixture.OpenUnowned](../../src/Sts2Agent/Testing/Fixtures/ConfirmationFixture.cs) 直接调用原生 `NAbandonRunConfirmPopup.Create(null)` 并加入模态容器，绕过 `Trial.DoubleDown`，因此没有登记受支持来源。这是同类窗口来源校验的隔离测试，不是审判的额外正常选项；采样后由测试入口取消。原始证据为 `gui-remaining/confirmation_cancel/evidence.json` 下标 8–15。

基础观察自身不返回 `manual_input_required`。触发未知模态的玩法动作可以在其 `transition.stop_reason` 返回该值；其他未知专属覆盖页也可能停在这个动作边界，但不能据此承诺基础观察会统一将任意未知窗口命名为 confirmation。

原生确认框是固定布局，没有需要滚动展开的候选列表。保留来源核对、遮挡、按钮动画与真实可点击状态。

## 15：建筑师终章

### 场景及字段

进入建筑师后为 `scene:epilogue`，通常 `screen.view:epilogue`；不作为普通事件、先古之民或新一场战斗返回。原生使用战斗背景，因此实际可读的战斗对象及顶栏详情工具可能仍可用，这不代表可以出牌或结束回合。

| 字段 | full 当前含义与边界 |
| --- | --- |
| `epilogue.status` | `visible` 已就绪；`not_ready` 当前仍展示／打字／任务中；`covered` 被其他页面遮盖 |
| `dialogue.speaker/text` | 当前已完整显示的气泡及说话者，可能为建筑师或玩家角色；没有完整可见气泡时为 null |
| `continue` | 当前原生继续／回应按钮，`text/enabled`；它对应 `advance_dialogue` |
| `proceed` | 最后一步的原生继续按钮，`text/enabled`；它对应 `proceed`，不能仅靠同样的英文按钮文字判断动作 |
| `top_bar` | 使用共用读取规则；地图／牌组覆盖不应把仍可读的顶栏一并隐藏 |
| `available_actions` | 仅列当前真实可用操作；对话推进与最后前进分别出现，不提供普通出牌／结束回合 |

`dialogue` 只含当前气泡，不能附送整段脚本、随机分支、访问次数、未来台词或结算分数。打字中的气泡不提前输出完整文本；`status:not_ready` 与 `dialogue:null` 有实际含义。

原生 `TheArchitect.CreateOptionForCurrentLine` 在最后一句使用 `PROCEED`，此前使用对话推进；最终 `WinRun` 才执行原生结束流程。进入终章的动作是 `action_completed`，最终 `proceed` 到已就绪的原生胜利页才是 `run_won`。静态观察中不增加胜负推断，胜利问号标题保留原样。

### 已识别的返回分支

1. 最后 Boss 奖励前进后，建筑师初始气泡与继续／回应按钮。
2. 逐句推进，当前气泡替换；角色和访问情况会改变原生台词与长度，结构相同，不穷举脚本。
3. 尚未准备：打字、任务或入场未完成，按钮 enabled 可为 false；不提前输出完整对白。
4. 地图覆盖：scene 仍为 epilogue，`screen.view:map`，终章内容 covered；关闭后回原气泡。
5. 牌组覆盖：原生为 scene:epilogue、`screen.view:deck`、终章内容 covered；MCP 0.50.4 的基础观察被校验器拒绝，0.50.5 已修复，见下述记录。关闭牌组后可恢复原气泡。
6. 最后气泡只有 proceed；完成后 `epilogue:null`，进入 `run_result`。后续结算八种 phase 属于 16 组，不在本轮展开。

气泡与按钮不是可滚动列表，未发现无用的视口截断；隐藏或未完整显示的台词继续不读。

### 已确认缺陷：建筑师牌组覆盖

MCP 0.50.4 基线中，`inspect_deck` 能成功打开牌组并返回牌组数据；其后 `get_observation` 返回 `transport_error`，不是一份成功的 full 观察。原生成功响应中的工具列表是：

```json
["inspect_potions", "inspect_relics", "inspect_deck", "close_card_view", "inspect_map"]
```

Python 的 [validate_ending](../../src/sts2_mcp/output/run_ending_details.py) 在该基线的 `epilogue.status:covered` 且 `screen.view:deck` 时只允许后三项，抛出 `Covered or unready ending actions.`；[GameTools](../../src/sts2_mcp/game_tools.py) 将校验错误包装为通信失败。完整数据校验先于 preset，因此不只是 full 受影响。

原生读取已经隐藏底层台词，新增两项也只是按可见顶栏提供的只读工具；这是校验契约未同步，不需要扩大原生动作权限。`close_card_view` 可以恢复正常观察。MCP 0.50.5 同步该分支的允许工具并补回归，继续禁止覆盖时推进对话或执行底层玩法动作；原始错误样本不改写。

原始失败证据为本地 `gui-remaining/epilogue/evidence.json` 下标 11–12；完整问题报告为 `.tmp/2026-11-03-epilogue-deck-observation-report.md`。不能将原生诊断 JSON 冒充 MCP 已成功返回的 full 样本。

### 建筑师修复与验证（MCP 0.50.5）

- 仅调整 Python covered/deck 分支的允许工具集合，Mod 0.49.2、schema 31 及原生 DLL 不变；不改变其他页面和原生动作许可。
- 新增公开 GameTools 回归在旧代码下证明五种 preset 都误报 transport_error；隐藏对白、其他覆盖页和底层动作的拒绝回归保持通过。相关 28 项及全套 472 项 Python 测试通过。
- 隔离 GUI 的既有 verify_view_availability(epilogue) 用例通过，共 56 次 MCP 调用；实际读取覆盖时提供的药水和遗物详情，核对五种观察预设，并确认覆盖时推进对话被拒绝，牌组／地图浏览与关闭可恢复。
- [修复后的完整 full](2026-11-03-observation-special-implementation-examples/epilogue-deck.full.json) 与 `.tmp/2026-11-03-observation-special-implementation/fix-gui/epilogue_view_availability/verify/evidence.json` 下标 16 的 structuredContent 一致。证据根目录为 `.tmp/2026-11-03-observation-special-implementation/`，fix-gui/report.json 为 passed，fix-python.log 为全套结果；自有 PID 160365 已退出，未更新正式 Mod。

## 本轮样本与验证

采样脚本和原始响应保存在未纳入 Git 的 `.tmp/2026-11-03-observation-special-review/`。使用已有测试夹具布置独立对局，再通过真实 stdio MCP 采集 `get_observation({"preset":"full"})`。金币、生命、奖励坐标和第三幕进度来自测试准备，不代表正常开局；只用于覆盖 UI 分支。

以下 47 份 JSON 均为实际 `get_observation({"preset":"full"})` 的完整玩法返回，保留所有空值与数组，名称和数值未改写；不是原生快照或其他工具的结果。每份可见棋盘另有同次 MCP 响应的 PNG，覆盖状态不带图片。全窗口截图是相邻的独立调用，只用于核对页面，不能代替同次棋盘图片。

原始证据下标从 0 开始；表中来源目录相对于本地证据根目录，各目录内均为 `evidence.json`。完整路径及图片映射见本地 `samples-manifest.json`。

### 13：占卜 full 样本

| 分支／状态 | 完整 full JSON | 同次棋盘图片 | 来源／下标 |
| --- | --- | --- | --- |
| 3 次占卜：初始画面 | [divination-basic-initial.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-initial.full.json) | 无 | `gui-final/divination_basic`：0 |
| 3 次占卜：大范围工具 | [divination-basic-playing-big.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-playing-big.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-playing-big.png) | `gui-final/divination_basic`：3 |
| 3 次占卜：小范围工具 | [divination-basic-playing-small.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-playing-small.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-playing-small.png) | `gui-final/divination_basic`：6 |
| 3 次占卜：揭开中心一格 | [divination-basic-partly-revealed.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-partly-revealed.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-partly-revealed.png) | `gui-final/divination_basic`：9 |
| 3 次占卜：地图覆盖 | [divination-basic-map-covered.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-map-covered.full.json) | 无 | `gui-final/divination_basic`：12 |
| 3 次占卜：关闭地图 | [divination-basic-map-returned.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-map-returned.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-map-returned.png) | `gui-final/divination_basic`：15 |
| 3 次占卜：牌组覆盖 | [divination-basic-deck-covered.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-deck-covered.full.json) | 无 | `gui-final/divination_basic`：18 |
| 3 次占卜：关闭牌组 | [divination-basic-deck-returned.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-deck-returned.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-deck-returned.png) | `gui-final/divination_basic`：21 |
| 3 次占卜：恢复大范围工具 | [divination-basic-big-restored.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-big-restored.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-big-restored.png) | `gui-final/divination_basic`：24 |
| 3 次占卜：后续揭开 0 | [divination-basic-after-reveal-0.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-after-reveal-0.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-after-reveal-0.png) | `gui-final/divination_basic`：27 |
| 3 次占卜：后续揭开 1 | [divination-basic-after-reveal-1.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-after-reveal-1.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-after-reveal-1.png) | `gui-final/divination_basic`：30 |
| 3 次占卜：结束棋盘 | [divination-basic-finished.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-finished.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-finished.png) | `gui-final/divination_basic`：32 |
| 3 次占卜：前进后地图 | [divination-basic-proceeded.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-basic-proceeded.full.json) | 无 | `gui-final/divination_basic`：35 |
| 6 次占卜及奖励：初始画面 | [divination-rewards-initial.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-initial.full.json) | 无 | `gui-remaining/divination_rewards`：0 |
| 6 次占卜及奖励：大范围工具 | [divination-rewards-playing-big.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-playing-big.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-playing-big.png) | `gui-remaining/divination_rewards`：3 |
| 6 次占卜及奖励：小范围工具 | [divination-rewards-playing-small.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-playing-small.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-playing-small.png) | `gui-remaining/divination_rewards`：6 |
| 6 次占卜及奖励：揭开中心一格 | [divination-rewards-partly-revealed.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-partly-revealed.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-partly-revealed.png) | `gui-remaining/divination_rewards`：9 |
| 6 次占卜及奖励：恢复大范围工具 | [divination-rewards-big-restored.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-big-restored.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-big-restored.png) | `gui-remaining/divination_rewards`：13 |
| 6 次占卜及奖励：后续揭开 0 | [divination-rewards-after-reveal-0.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-0.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-0.png) | `gui-remaining/divination_rewards`：16 |
| 6 次占卜及奖励：后续揭开 1 | [divination-rewards-after-reveal-1.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-1.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-1.png) | `gui-remaining/divination_rewards`：19 |
| 6 次占卜及奖励：后续揭开 2 | [divination-rewards-after-reveal-2.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-2.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-2.png) | `gui-remaining/divination_rewards`：22 |
| 6 次占卜及奖励：后续揭开 3 | [divination-rewards-after-reveal-3.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-3.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-3.png) | `gui-remaining/divination_rewards`：25 |
| 6 次占卜及奖励：后续揭开 4 | [divination-rewards-after-reveal-4.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-after-reveal-4.full.json) | 无 | `gui-remaining/divination_rewards`：28 |
| 6 次占卜及奖励：领取奖励／打开候选 0 | [divination-rewards-reward-claimed-0.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-reward-claimed-0.full.json) | 无 | `gui-remaining/divination_rewards`：31 |
| 6 次占卜及奖励：领取奖励／打开候选 1 | [divination-rewards-reward-claimed-1.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-reward-claimed-1.full.json) | 无 | `gui-remaining/divination_rewards`：34 |
| 6 次占卜及奖励：领取奖励／打开候选 2 | [divination-rewards-reward-claimed-2.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-reward-claimed-2.full.json) | 无 | `gui-remaining/divination_rewards`：37 |
| 6 次占卜及奖励：跳过卡牌候选 3 | [divination-rewards-reward-selection-skipped-3.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-reward-selection-skipped-3.full.json) | 无 | `gui-remaining/divination_rewards`：40 |
| 6 次占卜及奖励：跳过剩余奖励后 4 | [divination-rewards-rewards-closed-4.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-rewards-closed-4.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-rewards-closed-4.png) | `gui-remaining/divination_rewards`：43 |
| 6 次占卜及奖励：结束棋盘 | [divination-rewards-finished.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-finished.full.json) | [PNG](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-finished.png) | `gui-remaining/divination_rewards`：45 |
| 6 次占卜及奖励：前进后地图 | [divination-rewards-proceeded.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/divination-rewards-proceeded.full.json) | 无 | `gui-remaining/divination_rewards`：48 |

### 14：确认与人工输入 full 样本

| 分支／状态 | 完整 full JSON | 同次棋盘图片 | 来源／下标 |
| --- | --- | --- | --- |
| 取消及来源校验：初始画面 | [confirmation-cancel-initial.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-initial.full.json) | 无 | `gui-remaining/confirmation_cancel`：0 |
| 取消及来源校验：首次拒绝 | [confirmation-cancel-declined.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-declined.full.json) | 无 | `gui-remaining/confirmation_cancel`：3 |
| 取消及来源校验：再次拒绝的确认框 | [confirmation-cancel-confirmation.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-confirmation.full.json) | 无 | `gui-remaining/confirmation_cancel`：6 |
| 取消及来源校验：取消回原事件 | [confirmation-cancel-canceled.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-canceled.full.json) | 无 | `gui-remaining/confirmation_cancel`：9 |
| 取消及来源校验：同类弹窗但无受支持来源 | [confirmation-cancel-unowned.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-unowned.full.json) | 无 | `gui-remaining/confirmation_cancel`：12 |
| 取消及来源校验：人工边界测试取消后 | [confirmation-cancel-unowned-canceled.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-cancel-unowned-canceled.full.json) | 无 | `gui-remaining/confirmation_cancel`：16 |
| 确认放弃：初始画面 | [confirmation-confirm-initial.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-confirm-initial.full.json) | 无 | `gui-remaining/confirmation_confirm`：0 |
| 确认放弃：首次拒绝 | [confirmation-confirm-declined.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-confirm-declined.full.json) | 无 | `gui-remaining/confirmation_confirm`：3 |
| 确认放弃：再次拒绝的确认框 | [confirmation-confirm-confirmation.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-confirm-confirmation.full.json) | 无 | `gui-remaining/confirmation_confirm`：6 |
| 确认放弃：确认放弃后的结算首屏 | [confirmation-confirm-confirmed.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/confirmation-confirm-confirmed.full.json) | 无 | `gui-remaining/confirmation_confirm`：9 |

### 15：建筑师 full 样本与错误响应

| 分支／状态 | 完整 full JSON | 同次棋盘图片 | 来源／下标 |
| --- | --- | --- | --- |
| 建筑师：初始画面 | [epilogue-initial.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-initial.full.json) | 无 | `gui-epilogue/epilogue`：0 |
| 建筑师：当前气泡 0 | [epilogue-dialogue-0.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-dialogue-0.full.json) | 无 | `gui-epilogue/epilogue`：3 |
| 建筑师：地图覆盖 | [epilogue-map-covered.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-map-covered.full.json) | 无 | `gui-epilogue/epilogue`：6 |
| 建筑师：关闭地图 | [epilogue-map-returned.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-map-returned.full.json) | 无 | `gui-epilogue/epilogue`：9 |
| 建筑师：关闭牌组 | [epilogue-deck-returned.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-deck-returned.full.json) | 无 | `gui-epilogue/epilogue`：16 |
| 建筑师：当前气泡 1 | [epilogue-dialogue-1.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-dialogue-1.full.json) | 无 | `gui-epilogue/epilogue`：19 |
| 建筑师：终章完成后的胜利首屏 | [epilogue-outcome.full.json](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-outcome.full.json) | 无 | `gui-epilogue/epilogue`：22 |

牌组覆盖时没有可导出的成功 full：[实际错误响应](2026-11-03-get-observation-divination-confirmation-epilogue-examples/epilogue-deck-covered.error.json)，来源 `gui-epilogue/epilogue`：12。原生诊断响应仍留在本地证据中，不替代公开工具样本。

### 验证结果及未验证范围

- 5 类采样分批完成：`gui-final` 的 3 次占卜、`gui-remaining` 的 6 次占卜及两类确认、`gui-epilogue` 的终章。前两份报告整体仍为 failed；最后终章采样显式预期并记录已知错误后继续，不表示牌组覆盖缺陷已修复。
- 上述完整用例记录内共 136 次 MCP 调用、4 次原生诊断／测试调用；后者仅用于定位奖励覆盖、打开／关闭无来源弹窗以及读取失败时的原生状态，不向 LLM 发布隐藏坐标或物品模型。对局准备及清理另由测试夹具执行。
- 47 份 full 与原始 structuredContent 逐对象一致，通过当前 observation_details 校验；19 张 PNG 与原响应图像字节一致，尺寸与 grid.image 相同。MCP 文字 JSON 与 structuredContent 在每次调用核对一致。1 份错误响应单独保存，不当作成功观察校验。
- 所有自有 GUI 进程均已退出；Mod DLL 未变，未更新正式安装。未修改生产代码，没有重新运行整套 Python、C# 测试或构建。
- 首次 `gui` 采样把 close_map 误当作必含 transition 的玩法动作；`gui-final` 的奖励流程又重复打开跳过后仍保留的卡牌奖励行。两次临时脚本失败均保留，后续只修正采样流程。`gui-remaining` 的终章采样则因真实校验缺陷停止，原始错误未掩盖。
- playing、finished、地图／牌组覆盖、奖励／选牌与来源不同的确认框已实际覆盖；settling、确认框入场和建筑师 not_ready 的动画中间态仅核对源码，没有人工拼接 full 样本。建筑师只采集本次铁甲战士的原生对话，不穷举角色、访问次数或随机脚本。
- 奖励中的金钱、药水和卡牌候选均已采集。卡牌候选的 Skip 会回奖励列表，卡牌奖励行仍可重新打开；本次再点击奖励页 Skip 才离开，不把跳过候选当作已领走奖励。
- 其他未知模态／第三方自定义页面未实测；本轮的人工输入样本只证明同类确认窗口来源不匹配时停止自动操作。16–17 组继续待核验，summary 另行定稿。


## summary 约定与实施顺序

以下约定已经确认；建筑师牌组覆盖校验修复已交付，新增占卜摘要省略项尚待实现与验证。共用顶栏及卡牌选择继续使用已交付的摘要，`default/full/actions_only/top_bar` 保持现有契约。

- **事件层**：统一沿用已有的 `event.description` 省略规则，包含审判（Trial）初始、再次拒绝及取消确认后的事件正文；保留 `event.options[].description` 中的费用、效果与后果。覆盖时不补出原事件正文。该规则已经实现，本轮核对回归即可。
- **确认框**：主体沿用 default，保留 `confirmation.description`、标题和按钮；省略普通事件叙事的规则不能按字段名递归套到确认框正文。来源不支持时仍按人工输入边界返回。
- **建筑师**：主体沿用 default，保留当前对白、说话者、状态及按钮。
- **占卜**：summary 仅新增省略 `divination.instructions`，保留状态、阶段、可见次数、当前工具、工具按钮文字及 enabled、当前完整对白、格子、原生前进按钮、坐标说明与同次 PNG；不改变遮挡和未知值规则。`full/default` 及 `inspect_event` 仍提供实际可见的教学说明。

已交付的建筑师修复限于同步 Python 对 `epilogue.status:covered` 且 `screen.view:deck` 的工具校验：接受原生当前可读的 `inspect_potions/inspect_relics`，继续拒绝底层对话推进与玩法动作；不扩大其他页面的动作许可。相应回归及隔离 GUI 验证见上文。

占卜当前由 `inspect_event` 查看，工具表中没有独立的 `inspect_divination`；其返回仍依赖图片表达已揭开的图案。文字观察、地图和牌组／牌堆覆盖摘要、商店详情及已提出的知识库计划统一列入[用户后续待办](../development/TODO.md)，不并入本轮实现。
