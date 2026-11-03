# 终章与一局结算

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持单人第三幕结束后的建筑师对话、胜负结算、必要解锁和返回主菜单。实现依据与验证范围见[源码及图形验证](../research/2026-10-31-run-ending-validation.md)。

下文输出字段的空值与 JSON 示例以底层文件或 MCP full 为准；MCP 工具另接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

## 工具与流程

| 工具 | 操作 |
| --- | --- |
| `get_observation()` | 获取当前台词或当前结算页；不提前展开后页 |
| `advance_dialogue()` | 点击当前建筑师继续/回应按钮一次；与先古之民共用工具 |
| `proceed()` | 点击建筑师最后的前进，沿原生流程进入“胜利？”结算 |
| `inspect_run_result()` | 当前结算页详情，增加徽章、发现图标的悬停说明，时间线图标的原生说明，以及已显示解锁物品的效果与解释 |
| `run_result_option({"option_id":"continue"})` | 点击 `run_result.options` 中实际启用的一个按钮或解锁条目 |

第三幕最后 Boss 的奖励页 `proceed` 返回 `scene: "epilogue"`。依次操作观察提供的 `advance_dialogue` 或 `proceed`，不会跳过台词。结算使用 `scene: "run_result"`，按 `options` 继续、解锁、确认或返回。`main_menu` 按钮的文字有时是 Unlock，点击后先进入时间线；只有 `scene: "main_menu"`、结算字段为空时才真正回到菜单。工具不新开一局。

成功动作使用现有 `transition`：`action_completed/complete=true` 表示下一页已就绪，可按许可规则继续；当前页内容和按钮通过观察或 `inspect_run_result` 按需读取。首次进入已就绪的胜利结算页返回 `run_won/complete=true`，失败结算页返回 `run_lost/complete=true`，依据与原生横幅相同的胜负判据。刚进入建筑师对话仍为 `action_completed`；结算后翻页、解锁和返回菜单同样为 `action_completed`，不重复报告胜负。终局回执不保留连续动作许可，需通过观察或详情取得当前结算操作。成功详情也刷新状态令牌；失败、超时或人工改动后重新读取当前状态。MCP 工具除通用 `preset` 外只接受 `option_id`，底层文件操作不接受额外参数；按钮、页面身份和状态令牌在游戏线程再次核对。工具将时间线绑定到本次结算的原生菜单栈；人工返回菜单同样结束关联。工具入口不用于操作平常打开的时间线或其他主菜单页面。

## 建筑师观察

```json
{
  "scene": "epilogue",
  "screen": {"status": "visible", "view": "epilogue"},
  "epilogue": {
    "status": "visible",
    "dialogue": {"speaker": "Ironclad", "text": "Enemy...\nKill..."},
    "continue": null,
    "proceed": {"text": "Continue", "enabled": true}
  }
}
```

示例仅展示相关字段；具体台词及按钮文字由当前原生对话决定。只读取已出现且显示完整的当前气泡，不返回整段脚本、未来台词、访问次数或选择的随机分支。

## 结算观察

`run_result` 提供下列字段：

| 字段 | 含义 |
| --- | --- |
| `status` | `visible`、`not_ready` 或 `covered` |
| `phase` | `outcome` 首屏、`summary` 汇总、`tutorial` 时间线教程、`timeline`、`epoch` 章节故事、`unlock` 解锁确认；原生提供时也识别 `history` 和 `leaderboard` |
| `title` / `texts` | 当前已展示页面的横幅与文本，英文转写；可滚动内容完整读取，保留 `Victory...?` 中的问号和分数进度 `[140/200]` |
| `score_lines` | 当前可见计分行，每项为 `label`、`value` |
| `badges` | 当前可见徽章名称及 `bronze/silver/gold` 外观等级；悬停效果在详情调用中读取 |
| `discoveries` | 当前发现图标的类别及显示数量，`cards/relics/potions/enemies/epochs` |
| `cards` | 当前解锁页中已显示卡牌的牌面信息与正文；不包含后续页面的卡牌 |
| `relics` / `potions` | 当前已显示的解锁物品名称；效果由详情调用提供 |
| `options` | 当前按钮的 `id`、`text`、`enabled`；调用时原样传回 ID |

`top_bar` 仅在原生结算上方确实可见时保留；不由本局历史补出未显示的数值。战斗、事件、奖励等底层操作不再提供。初始 `outcome` 页不会提前给出分数行、徽章或发现列表。

详情增加 `hover_tips`，来源如 `badge:0`、`discovery:cards`；卡牌、遗物、药水的附加说明位于各自条目。原生发现提示最多列十个名称，之后用省略号，工具保留这个限制。累计建筑师伤害与随机死亡语句来自已显示标签的本地化来源，不能重新抽签或根据当前存档重算。

get_observation 的 summary 保留当前结算主体和全部 texts、options、空列表，只将已显示 cards 压缩为共用卡牌摘要，卡牌 ID 仍为 card:N 字符串。正文、稀有度和卡池保留在 full/default 及 inspect_run_result；顶栏继续独立复用共用摘要。完整规则见[观察预设](observation.md#mcp-输出预设)。

当前原生本局详情页的滚动文字与物品不按视口截断，基础观察和详情使用同一浏览范围；读取不改变滚动位置。隐藏、透明、非滚动画外控件以及未揭示解锁仍不读取，按钮仍按真实可点击状态判断。当前游戏基线原生禁用了 View Run 按钮，工具不会启用它；该页修复使用仅测试模式的原生页面夹具验证，范围见[浏览内容审查](../research/2026-11-02-browsable-content-audit.md)。

失败汇总死亡原因、本局详情结果句与日期均转写为英语。原生生成当前文本时保留完整本地化来源及日期输入，观察只转写当前标签，不重新生成死亡句、不改变游戏语言或区域。基础观察与详情共用该结果；源码、实际 full 和验证范围见[结算观察实施记录](../research/2026-11-03-result-observation-implementation.md)。

原生胜利流程会让玩家生命归零后展示 `Victory...?`；不能用结算时 HP 为零改判失败。`run_won` 表示原生按胜利结算，不表示击败建筑师；仍保留 HP 归零事件与原生标题中的问号。死亡首屏同样保留原生随机横幅和语句。修复依据及验证范围见[终章胜负停止原因修复](../research/2026-11-02-run-outcome.md)。

## 解锁及等待

时间线可能出现多个待揭示条目，`epoch:N` 是工具定位 ID，不是提前公开的物品结果。与地图/牌组浏览一致，当前时间线中可浏览的待揭示条目可以列出；选择离屏条目时先沿原生滚动流程将它展示，再重新核对并点击。每个章节和确认页分别返回，不自动领取后续页。

就绪检查包括打字、原生结算创建的补间动画、分数条及各解锁页的入场动画；按钮启用不等于所有可见计数已经稳定。到达已知边界后仍要求观察连续 250 毫秒不变，25 秒内未满足则返回 `timeout/complete=false`。未知模态不自动点击。

每日挑战榜单、原生启用的查看本局/章节翻页入口按当前按钮识别；它们不改变本局胜负。本版本部分入口本来隐藏或禁用，工具不强行启用。相关未实测范围见验证记录。

建筑师使用原生战斗背景；当前可读的界面、对象、遗物、药水及地图工具会列入 `available_actions`，具体合法性仍由调用入口校验。关闭地图会恢复当前对话；不会因此提供普通出牌或结束回合。工具可用性核查见[验证记录](../research/2026-10-31-observation-presets-validation.md)。

建筑师对话也可在原生按钮可用时查看牌组；覆盖期间保留 `screen.view: deck` 并隐藏底层对话，当前原生工具列表包含浏览及实际可读的药水／遗物详情。结算页的药水／遗物详情也根据实际可见、可悬停控件独立列出，不要求无关的结算文字动画完成；仍不能打开牌组或执行已结束对局的动作。实测范围见[可用工具修复记录](../research/2026-11-02-available-actions-fix.md)。

建筑师牌组覆盖期间，五种观察预设均可读取当前覆盖页，并接受原生允许的药水／遗物只读工具；底层对白和推进对话、使用药水等动作仍被覆盖。缺陷与修复的验证证据见[覆盖页核验记录](../research/2026-11-03-get-observation-divination-confirmation-epilogue.md#已确认缺陷建筑师牌组覆盖)。
