# 终章与一局结算

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持单人第三幕结束后的建筑师对话、胜负结算、必要解锁和返回主菜单。实现依据与验证范围见[源码及图形验证](../research/2026-10-31-run-ending-validation.md)。

含 null 的字段说明与示例按 full 表达；默认输出的空值处理见[公共预设](mcp.md#输出预设)。

## 工具与流程

| 工具 | 操作 |
| --- | --- |
| `get_observation()` | 获取当前台词或当前结算页；不提前展开后页 |
| `advance_dialogue()` | 点击当前建筑师继续/回应按钮一次；与先古之民共用工具 |
| `proceed()` | 点击建筑师最后的前进，沿原生流程进入“胜利？”结算 |
| `inspect_run_result(preset?)` | 当前完整或展示中的结算页；full/default提供已允许悬停的效果和解释，summary保留文字、名称与提示标题 |
| `run_result_option({"option_id":"continue"})` | 点击 `run_result.options` 中实际启用的按钮、待揭晓或已揭晓章节 |

第三幕最后 Boss 的奖励页 `proceed` 返回 `scene: "epilogue"`。依次操作观察提供的 `advance_dialogue` 或 `proceed`，不会跳过台词。结算使用 `scene: "run_result"`，按 `options` 继续、解锁、确认或返回。`main_menu` 按钮的文字有时是 Unlock，点击后先进入时间线；只有 `scene: "main_menu"`、结算字段为空时才真正回到菜单。工具不新开一局。

### 动作结果与许可

成功动作使用 `transition`：`action_completed/complete=true` 表示下一页已就绪，可按许可规则继续；当前页内容和按钮通过观察或 `inspect_run_result` 按需读取。首次进入已就绪的胜利结算页返回 `run_won/complete=true`，失败结算页返回 `run_lost/complete=true`，依据与原生横幅相同的胜负判据。终局 available_actions 保留实际可用的只读查看工具，玩法许可在终局撤销。刚进入建筑师对话仍为 `action_completed`；结算后翻页、解锁和返回菜单同样为 `action_completed`，不重复报告胜负。

终局后通过观察或详情取得当前结算操作的许可。成功详情也刷新状态令牌；过期观察、超时、不确定结果或人工改动后重新读取当前状态。

`inspect_run_result` 接受 default/full/summary，默认 default；run_result_option另接受option_id，底层查看操作不接受额外参数；按钮、页面身份和状态令牌在游戏线程再次核对。工具将时间线绑定到本次结算的原生菜单栈；人工返回菜单同样结束关联。工具入口不用于操作平常打开的时间线或其他主菜单页面。

advance_dialogue的明确点击前拒绝保留已有许可，并区分页面覆盖、等待对话／按钮就绪和最终前进；可直接关闭覆盖页或改用proceed。已有许可的恢复遵循[统一错误语义](mcp.md#调用和错误语义)。两类对话的参数均只有default/full，建筑师可用性由EpilogueInspection.DialogueUnavailableReason集中维护，执行、continue.enabled及available_actions共用；最终proceed继续沿用原生胜利流程。

run_result_option在明确未交互的拒绝后保留已有许可，并提示没有关联结算、覆盖、展示未完成、输入被阻挡或选项不存在／禁用。RunResultInspection的ActionUnavailableReason、OptionUnavailableReason供执行和就绪判断共用；enabled及available_actions使用同一操作条件。首次滚动／点击前标记交互，滚动后重查相同页面与按钮；已滚动、过期或结果不确定时重新读取。

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

示例仅展示相关字段；具体台词及按钮文字由当前原生对话决定。读取当前已出现且显示完整的气泡，后续台词在推进后提供。

## 结算观察

`run_result` 提供下列字段：

| 字段 | 含义 |
| --- | --- |
| `status` | 当前展示完成、展示中或被覆盖，见[共用展示状态](observation.md#页面主体的展示状态)；与按钮是否可用分开 |
| `phase` | `outcome` 首屏、`summary` 汇总、`tutorial` 时间线教程、`timeline`、`epoch` 章节故事、`unlock` 解锁确认；原生提供时也识别 `history` 和 `leaderboard` |
| `title` / `texts` | title 为横幅；texts 为尚未由结构字段表达的正文、故事、总分进度和提示，英文转写并完整读取可滚动内容。保留 `Victory...?` 中的问号和 `[140/200]` 等进度 |
| `score_lines` | 当前可见计分行，每项为 `label`、`value` |
| `badges` | 当前可见徽章名称及 `bronze/silver/gold` 外观等级；悬停效果在详情调用中读取 |
| `discoveries` | 当前发现图标的类别及显示数量，`cards/relics/potions/enemies/epochs` |
| `cards` | 当前已揭示卡牌；基础观察为face／摘要，详情full/default为完整牌面，summary为共用卡牌摘要 |
| `relics` / `potions` | 当前已显示的解锁物品名称；效果由详情调用提供 |
| `options` | 当前按钮的 `id`、`text`、`enabled`；调用时原样传回 ID |

`top_bar` 仅在原生结算上方确实可见时保留；不由本局历史补出未显示的数值。战斗、事件、奖励等底层操作不再提供。初始 `outcome` 页不会提前给出分数行、徽章或发现列表。

基础观察的结算卡牌full/default采用[face格式](hand-inspection.md#共用卡牌格式)，summary采用共用摘要；inspect_run_result的完整牌面和逐牌解释保留在卡牌条目内。详情另增加页面级 `hover_tips`，来源如 `badge:0`、`discovery:cards`；卡牌、遗物、药水的附加说明位于各自条目。原生发现提示最多列十个名称，之后用省略号，工具保留这个限制。累计建筑师伤害与随机死亡语句来自已显示标签的本地化来源，不能重新抽签或根据当前存档重算。

get_observation三种内容预设共用结算静态主体，页面hover_tips只保留source/title，药水和遗物只保留名称，texts、options和空列表保留。卡牌full/default使用face_full/face_default，summary使用共用摘要，ID仍为card:N。顶栏继续独立处理，见[观察预设](observation.md#mcp-输出预设)。

texts 按原生控件归属排除已由 title、score_lines、discoveries 和 options 表达的文字；不同位置的独立正文即使文字相同也保留。时间线章节槽的 Reveal／View 是操作名，不代替槽位本身的可见说明。未结构化的正文和进度继续保留，基础观察及详情的三种内容预设共用同一读取规则。

inspect_run_result.summary同样省略页面提示的description、药水／遗物正文和附加解释，卡牌使用共用摘要；完整故事正文保留。full/default提供允许读取的完整效果。不可悬停项保留静态信息，以null正文／空解释及notes.hover_tips_unavailable指明来源；summary省略该悬停note，但保留notes.presentation。

查看只要求对应单人结算页面可读，不要求按钮可点击；展示中返回not_ready及已显示内容。执行、基础观察和专项查看使用RunResultInspection的共同读取，展示与操作就绪分开。原生hover_sources列出当前可浏览的提示图标，已提供提示与不可用来源互斥且共同覆盖该清单；徽章／发现／卡牌／药水／遗物引用另与实际条目核对。该清单与unavailable_hover_sources仅用于完整协议校验，公开输出不含内部列表；完整字段及同次scene/screen先校验，再投影预设，坏响应清除许可。无结算、无关菜单、非单人、模态／物品详情覆盖和过渡给出具体提示；明确纯读取拒绝保留已有许可，首次失败不授予许可。

本局详情页的滚动文字与物品不按视口截断，基础观察和详情使用同一浏览范围；读取不改变滚动位置。隐藏、透明、非滚动画外控件以及未揭示解锁仍不读取，按钮按真实可点击状态判断。当前原版禁用了View Run；其详情资源包含普通历史子页，但原生打开方法没有初始化返回导航。没有有效菜单栈的历史页可以读取，操作返回具体拒绝且不提供启用的按钮。隔离夹具使用原生资源与NRunSubmenuStack.Push／Pop验证浏览和返回，不启用正式入口，见[结算选项实施记录](../research/2026-11-08-result-option-recovery-implementation.md)。

失败汇总死亡原因、本局详情结果句与日期均转写为英语。原生生成当前文本时保留完整本地化来源及日期输入，观察只转写当前标签，不重新生成死亡句、不改变游戏语言或区域。基础观察与详情共用该结果；源码、实际 full 和验证范围见[结算观察实施记录](../research/2026-11-03-result-observation-implementation.md)。

原生胜利流程会让玩家生命归零后展示 `Victory...?`；不能用结算时 HP 为零改判失败。`run_won` 表示原生按胜利结算，不表示击败建筑师；仍保留 HP 归零事件与原生标题中的问号。死亡首屏同样保留原生随机横幅和语句。修复依据及验证范围见[终章胜负停止原因修复](../research/2026-11-02-run-outcome.md)。

## 解锁及等待

时间线的待揭晓和已揭晓条目分别提供Reveal、View选项，沿用同一`epoch:N`定位ID；悬停标题由相同source关联。原生尚未获得的条目仍只提供实际可见说明。重新打开已揭晓条目可阅读章节，原生提供时可用next_chapter／previous_chapter翻页；关闭后返回时间线。

与地图／牌组浏览一致，当前时间线中可浏览的条目完整列出；选择离屏条目时先沿原生滚动流程将它展示，再重新核对相同页面及按钮。每个章节和确认页分别返回。进度解锁不属于本局牌组／物品获得，普通翻页events为空。

就绪检查包括打字、原生结算创建的补间动画、分数条及各解锁页的入场动画；可行动边界还须等待可见计数稳定。到达已知边界后仍要求观察连续 250 毫秒不变，25 秒内未满足则返回 `timeout/complete=false`。未知模态不自动点击。

每日挑战榜单按原生实际提供的按钮识别，尚未补充GUI实测；View Run的正常入口仍禁用。结算翻页和章节重读不改变本局胜负，验证范围见结算选项实施记录。

建筑师使用原生战斗背景，`available_actions` 列出当前可读的界面、对象、药水、遗物及原生允许的浏览工具。地图／牌组覆盖时隐藏底层对白和动作；关闭后恢复当前对话，查看条件见[工具可用性验证](../research/2026-10-31-observation-presets-validation.md)及[修复记录](../research/2026-11-02-available-actions-fix.md)。

五种基础观察预设均支持建筑师牌组覆盖；药水与遗物只读工具按控件实际可见、可悬停条件独立提供。结算页同样独立判断顶栏详情；牌组打开及已结束对局的玩法动作不在结算操作范围。覆盖页验证见[核验记录](../research/2026-11-03-get-observation-divination-confirmation-epilogue.md#已确认缺陷建筑师牌组覆盖)。

## 验证入口

结算读取见 [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)，对话与结算动作见 [GameAdapter.RunEnding](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs)，公开校验与预设见 [run_ending_details](../../src/sts2_mcp/output/run_ending_details.py)。

结算动作验证使用[verify_result_option.py](../../tests/game/verifiers/verify_result_option.py)，隔离套件为[gui_suite_result_option.json](../../tests/game/data/gui_suite_result_option.json)；失败与胜利流程使用独立终局实例。胜利回执不续接玩法许可，后续检查原生解锁、稳定ID重读、章节翻页、滚动后拒绝及返回主菜单。读取预设另由[verify_result_inspection.py](../../tests/game/verifiers/verify_result_inspection.py)核验。
