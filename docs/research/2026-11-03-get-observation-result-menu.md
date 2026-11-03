# get_observation 胜负结算、解锁与菜单核验

> 当前状态：16–17 组现状核验完成，共 2 组；保存的 47 份 full 与 2 份错误响应属于 MCP 0.50.6 原始基线。后续 Mod 0.49.3／MCP 0.50.7 已修复文字转写并将兜底改名为 unrecognized，见[实施记录](2026-11-03-result-observation-implementation.md)。summary 已定稿，正在实施。leaderboard 仅源码核对；地图及牌组／牌堆覆盖主体仍留待对应工具核验，get_observation 整体未核销。

流程见[工具核验清单](2026-11-02-mcp-tool-review.md)，场景编号见[观察总目录](2026-11-02-get-observation-review.md)。本轮不核销 inspect_run_result 或 run_result_option。

## 基线与读取依据

- 核对日期：2026-11-03，项目 abc2de2；MCP 0.50.6、Mod 0.49.2、原生 schema 31。
- 游戏 Linux v0.107.1、release 59260271，RitsuLib 0.6.10；游戏目录 data_sts2_linuxbsd_x86_64/sts2.dll 的 SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 本次使用的隔离运行时 DLL SHA-256 为 1d1a7e8c180bbb05b15f3ee8a5dbbf098485685dda393466eb3e5356e6d403ed；未安装正式 Mod，未使用个人存档。
- 当前反编译证据：本地 `.tmp/2026-11-03-observation-final-review/source/`，provenance.json 记录程序集及 6 个完整类型名。源码不纳入 Git。
- 原生组装与场景判定见 [GameAdapter.Observe](../../src/Sts2Agent/Adapter/GameAdapter.cs)，许可和 screen.status 见 [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。结算根节点、就绪、文字和物品读取见 [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)；公开结构与校验见 [run_ending_details.py](../../src/sts2_mcp/output/run_ending_details.py)。

## 16：胜负结算与解锁

所有已识别结算页均为 scene:run_result、screen.view:run_result，当前页另用 run_result.phase 区分。full 的 run_result 固定包含 status、phase、title、texts、score_lines、badges、discoveries、options、cards、relics、potions；当前页不适用的列表仍为 []，title 可为 null。

| phase | 当前可读内容 | 本轮证据与限制 |
| --- | --- | --- |
| outcome | 原生胜负横幅、已经出现的原因或建筑师伤害句、Continue；不提前返回后页分数和解锁 | 胜利与失败均沿原生流程实测。Victory...? 的问号保留；get_observation 不含 stop_reason，胜负停止原因属于进入该页的动作回执 |
| summary | 分数行、已出现徽章、发现类别与数量、分数进度及当前按钮 | 胜负均实测。title、按钮文字及计分行也可能出现在 texts 中；进度及 Unlocks Remaining 只有 texts，不能直接删除整个列表 |
| history | 当前本局详情的可浏览文字、已显示物品和返回按钮 | 仅隔离夹具打开原生页。本版本 NGameOverScreen._Ready 禁用 View Run，未强行启用普通流程入口；长内容包含夹具标签，不作为正常游玩内容示例 |
| leaderboard | 原生每日挑战榜单显示后的文本和当前按钮，沿用同一结构 | 仅源码核验。NGameOverScreen 在 GameMode.Daily 初始化榜单并提供入口，ShowLeaderboard 切换横幅及正文；未运行每日挑战、联网或制造榜单数据，因此不提供伪造 full |
| tutorial | 当前时间线教程文字和继续按钮 | 新隔离存档首次教程实测；不是每次结算都必经的页面 |
| timeline | 当前可浏览的待揭示 epoch:N 与真实返回按钮；不会提前给出其奖励 | 实测多个待揭示条目、逐项处理与最后返回菜单。inspect_run_result 另提供原生悬停说明，基础观察不包含 hover_tips |
| epoch | 当前已揭示章节标题、正文和实际提供的按钮 | 实测多个章节。next_chapter/previous_chapter 仅在原生可见时列出，本轮未实测翻页组合；不返回完整章节脚本或未来内容 |
| unlock | 已显示卡牌、遗物、药水或其他解锁文字与 Confirm | 卡牌、遗物、药水、角色与功能解锁均已实测；未穷举各类别全部内容，具体页面见完整样本 |

### 物品、覆盖与等待边界

- 当前解锁卡牌的基础观察已包含 id、name、type、rarity、visual_card_pool、energy_cost、star_cost、description；已显示正文可以直接读取，不依赖先悬停。id 为 card:N 字符串，属于该页物品定位，不是可调用 select_card 的手牌 ID。
- 遗物、药水基础观察目前只读名称；inspect_run_result 增加效果和附加解释。徽章与发现图标的悬停说明同样由该工具读取。无论 preset 是 full 还是 default，都不能把基础观察理解成详情工具的 full。
- 顶栏仅在实际可读时返回。结算仍显示的 HP 可以为 0，不能据此改判原生胜利；时间线等已离开本局页面不从历史补顶栏。summary 继续使用已实现的共用四字段顶栏摘要。
- screen.status 描述上层是否暴露，run_result.status 另判断文字和动画就绪；因此 screen 可为 visible 而 run_result 为 not_ready。未就绪时可能已有部分可见文字、灰置选项，不能将其当作稳定终态。覆盖时隐藏结算内容，未知模态不自动点击。这些瞬态和覆盖组合本轮仅核对实现，没有稳定 GUI 样本，不用修改正常样本伪造。
- 本次结算的时间线由 RunResultInspection 绑定原生菜单栈。离开后重新从普通主菜单打开同类时间线，不再算 run_result。本轮通过受门控夹具模拟重新打开，实际返回 main_menu，run_result:null，结算操作被拒绝；没有把它当作正常结算后页。

### 已复现的文字缺口

失败 summary 的 texts 中出现 `“The Ironclad被Group of Slimes打倒了。”`；history 夹具页也含中文月份及 `“The Ironclad成功到达了塔顶？”`。当前英文转写没有覆盖这些完整句式和日期。原样保留 full，未手工翻译样本；default、summary 与 inspect_run_result 共用该读取路径。可见内容来源一致，但语言转换不完整。基线影响及修复验证见本地[问题记录](../../.tmp/2026-11-03-observation-final-review-report.md)，后续修复应保留已显示句子的来源，不能重新抽签死亡语句。Mod 0.49.3 已修复上述转写，原始样本继续保留，新的真实 full 见[阶段 1 验证](2026-11-03-result-observation-implementation.md#阶段-1-验证)。

## 17：主菜单、加载及未分类页面

本节表格与 JSON 保留 MCP 0.50.6 的原始基线：当时 loading_or_noncombat 仍是正在使用的兜底 scene，不是可靠的“正在加载”判断。该命名也容易将商店等已识别非战斗场景包含进来，现已改为 unrecognized。判定范围不变：Observe 优先识别结算、建筑师、战斗、受支持房间；均未匹配时，MainMenu 节点存在则使用 main_menu，否则使用兜底。

| 返回 | 可据此确认 | 不应推断 |
| --- | --- | --- |
| main_menu，screen.status:not_applicable | 当前被归入主菜单体系；本工具没有返回受支持的玩法内容 | 不代表刚刚完成一局，也不保证当前是主菜单首页；普通时间线等子页也可能如此 |
| loading_or_noncombat，screen.status:not_applicable | 尚未匹配已支持场景；本次捕获的启动过渡确实如此 | 不能仅凭 scene 判定还在加载、没有任何画面或应自动重试原动作 |
| loading_or_noncombat，screen.status:visible，可能含顶栏或查看工具 | 实现允许未匹配专用房间但 RunUi.NonCombatVisible 成立的非战斗画面 | 不表示该房间有完整文字或操作支持；本轮仅源码核验，没有捏造该分支的实测样本 |

当前没有独立 unknown scene，也没有菜单正文、开始新局或通用菜单点击工具。测试模式内部的 start_test_combat 不属于公开 MCP available_actions，不能写进玩法示例。真正未知 Mod 页面没有穷举。

最终采用 unrecognized，表示尚未识别成受支持场景，包括加载过渡；不新增没有可靠 UI 判据的 loading 状态。新旧标识与版本边界见[观察接口](../development/observation.md)。原始样本未改名，不能直接当作新版本响应。

## 完整 full 示例

全部使用真实 stdio MCP 的 get_observation({"preset":"full"})，文字 JSON 与 structuredContent 逐次一致。以下文件逐对象保留原响应及其 null、空列表、名称、数值与 actions，没有以详情响应代替，也没有截断。测试夹具的开局数值、进度和发现内容不代表正常角色配置。

本地证据列均相对于 `.tmp/2026-11-03-observation-final-review/gui/`，格式为案例目录 evidence.json 的零起始下标；同案例 screenshots 目录有对应 label.png。history-fixture 含明确的长列表测试标签。没有 leaderboard 或未捕获瞬态的假样本。

可先查看以下结构不同的代表页，再按后面的索引查看连续流程：

| 场景 | 完整 JSON |
| --- | --- |
| 失败／胜利首屏 | [失败](2026-11-03-get-observation-result-menu-examples/death-outcome.full.json)、[胜利](2026-11-03-get-observation-result-menu-examples/victory_unlock-outcome.full.json) |
| 失败／胜利计分汇总 | [失败](2026-11-03-get-observation-result-menu-examples/death-summary.full.json)、[胜利](2026-11-03-get-observation-result-menu-examples/victory_unlock-summary.full.json) |
| 首次教程、多个待揭示条目、章节正文 | [教程](2026-11-03-get-observation-result-menu-examples/death-after-result-00.full.json)、[时间线](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-04.full.json)、[章节](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-05.full.json) |
| 卡牌／药水／遗物解锁 | [卡牌](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-06.full.json)、[药水](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-09.full.json)、[遗物](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-13.full.json) |
| 功能／角色解锁 | [功能](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-10.full.json)、[角色](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-19.full.json) |
| 本局详情夹具 | [history](2026-11-03-get-observation-result-menu-examples/history-history-fixture.full.json) |
| 启动过渡、主菜单、普通时间线边界 | [启动](2026-11-03-get-observation-result-menu-examples/death-startup.full.json)、[主菜单](2026-11-03-get-observation-result-menu-examples/death-main-menu-before-run.full.json)、[普通时间线](2026-11-03-get-observation-result-menu-examples/death-ordinary-timeline-unowned.full.json) |

以下为全部样本及来源：

| 案例与步骤 | phase／scene | 完整 JSON | 本地证据／下标 |
| --- | --- | --- | --- |
| death / startup | `loading_or_noncombat` | [death-startup.full.json](2026-11-03-get-observation-result-menu-examples/death-startup.full.json) | death：0 |
| death / main-menu-before-run | `main_menu` | [death-main-menu-before-run.full.json](2026-11-03-get-observation-result-menu-examples/death-main-menu-before-run.full.json) | death：3 |
| death / run-started | `outcome` | [death-run-started.full.json](2026-11-03-get-observation-result-menu-examples/death-run-started.full.json) | death：7 |
| death / outcome | `outcome` | [death-outcome.full.json](2026-11-03-get-observation-result-menu-examples/death-outcome.full.json) | death：9 |
| death / summary | `summary` | [death-summary.full.json](2026-11-03-get-observation-result-menu-examples/death-summary.full.json) | death：12 |
| death / after-result-00 | `tutorial` | [death-after-result-00.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-00.full.json) | death：16 |
| death / after-result-01 | `timeline` | [death-after-result-01.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-01.full.json) | death：20 |
| death / after-result-02 | `epoch` | [death-after-result-02.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-02.full.json) | death：24 |
| death / after-result-03 | `unlock` | [death-after-result-03.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-03.full.json) | death：28 |
| death / after-result-04 | `timeline` | [death-after-result-04.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-04.full.json) | death：32 |
| death / after-result-05 | `epoch` | [death-after-result-05.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-05.full.json) | death：36 |
| death / after-result-06 | `unlock` | [death-after-result-06.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-06.full.json) | death：40 |
| death / after-result-07 | `timeline` | [death-after-result-07.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-07.full.json) | death：44 |
| death / after-result-08 | `main_menu` | [death-after-result-08.full.json](2026-11-03-get-observation-result-menu-examples/death-after-result-08.full.json) | death：48 |
| death / ordinary-timeline-unowned | `main_menu` | [death-ordinary-timeline-unowned.full.json](2026-11-03-get-observation-result-menu-examples/death-ordinary-timeline-unowned.full.json) | death：51 |
| death / ordinary-timeline-closed | `main_menu` | [death-ordinary-timeline-closed.full.json](2026-11-03-get-observation-result-menu-examples/death-ordinary-timeline-closed.full.json) | death：55 |
| victory_unlock / startup | `loading_or_noncombat` | [victory_unlock-startup.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-startup.full.json) | victory_unlock：0 |
| victory_unlock / main-menu-before-run | `main_menu` | [victory_unlock-main-menu-before-run.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-main-menu-before-run.full.json) | victory_unlock：3 |
| victory_unlock / outcome | `outcome` | [victory_unlock-outcome.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-outcome.full.json) | victory_unlock：15 |
| victory_unlock / summary | `summary` | [victory_unlock-summary.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-summary.full.json) | victory_unlock：18 |
| victory_unlock / after-result-00 | `tutorial` | [victory_unlock-after-result-00.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-00.full.json) | victory_unlock：22 |
| victory_unlock / after-result-01 | `timeline` | [victory_unlock-after-result-01.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-01.full.json) | victory_unlock：26 |
| victory_unlock / after-result-02 | `epoch` | [victory_unlock-after-result-02.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-02.full.json) | victory_unlock：30 |
| victory_unlock / after-result-03 | `unlock` | [victory_unlock-after-result-03.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-03.full.json) | victory_unlock：34 |
| victory_unlock / after-result-04 | `timeline` | [victory_unlock-after-result-04.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-04.full.json) | victory_unlock：38 |
| victory_unlock / after-result-05 | `epoch` | [victory_unlock-after-result-05.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-05.full.json) | victory_unlock：42 |
| victory_unlock / after-result-06 | `unlock` | [victory_unlock-after-result-06.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-06.full.json) | victory_unlock：46 |
| victory_unlock / after-result-07 | `timeline` | [victory_unlock-after-result-07.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-07.full.json) | victory_unlock：50 |
| victory_unlock / after-result-08 | `epoch` | [victory_unlock-after-result-08.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-08.full.json) | victory_unlock：54 |
| victory_unlock / after-result-09 | `unlock` | [victory_unlock-after-result-09.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-09.full.json) | victory_unlock：58 |
| victory_unlock / after-result-10 | `unlock` | [victory_unlock-after-result-10.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-10.full.json) | victory_unlock：62 |
| victory_unlock / after-result-11 | `timeline` | [victory_unlock-after-result-11.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-11.full.json) | victory_unlock：66 |
| victory_unlock / after-result-12 | `epoch` | [victory_unlock-after-result-12.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-12.full.json) | victory_unlock：70 |
| victory_unlock / after-result-13 | `unlock` | [victory_unlock-after-result-13.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-13.full.json) | victory_unlock：74 |
| victory_unlock / after-result-14 | `timeline` | [victory_unlock-after-result-14.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-14.full.json) | victory_unlock：78 |
| victory_unlock / after-result-15 | `epoch` | [victory_unlock-after-result-15.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-15.full.json) | victory_unlock：82 |
| victory_unlock / after-result-16 | `unlock` | [victory_unlock-after-result-16.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-16.full.json) | victory_unlock：86 |
| victory_unlock / after-result-17 | `timeline` | [victory_unlock-after-result-17.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-17.full.json) | victory_unlock：90 |
| victory_unlock / after-result-18 | `epoch` | [victory_unlock-after-result-18.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-18.full.json) | victory_unlock：94 |
| victory_unlock / after-result-19 | `unlock` | [victory_unlock-after-result-19.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-19.full.json) | victory_unlock：98 |
| victory_unlock / after-result-20 | `timeline` | [victory_unlock-after-result-20.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-20.full.json) | victory_unlock：102 |
| victory_unlock / after-result-21 | `main_menu` | [victory_unlock-after-result-21.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-after-result-21.full.json) | victory_unlock：106 |
| victory_unlock / ordinary-timeline-unowned | `main_menu` | [victory_unlock-ordinary-timeline-unowned.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-ordinary-timeline-unowned.full.json) | victory_unlock：109 |
| victory_unlock / ordinary-timeline-closed | `main_menu` | [victory_unlock-ordinary-timeline-closed.full.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-ordinary-timeline-closed.full.json) | victory_unlock：113 |
| history / outcome | `outcome` | [history-outcome.full.json](2026-11-03-get-observation-result-menu-examples/history-outcome.full.json) | history：9 |
| history / summary | `summary` | [history-summary.full.json](2026-11-03-get-observation-result-menu-examples/history-summary.full.json) | history：14 |
| history / history-fixture | `history` | [history-history-fixture.full.json](2026-11-03-get-observation-result-menu-examples/history-history-fixture.full.json) | history：18 |

普通时间线拒绝结算操作的实际错误另保存在 [death-ordinary-timeline-rejected.error.json](2026-11-03-get-observation-result-menu-examples/death-ordinary-timeline-rejected.error.json)、[victory_unlock-ordinary-timeline-rejected.error.json](2026-11-03-get-observation-result-menu-examples/victory_unlock-ordinary-timeline-rejected.error.json)，它们是错误响应，不是 full 成功观察。

## summary 定稿

结算主体沿用 default，保留 status、phase、title、texts、score_lines、badges、discoveries、options 及当前空列表；仅 cards 使用共用 card_summary，保留字符串 card:N ID、名字、类型和费用等摘要字段，正文、rarity、visual_card_pool 由 inspect_run_result 按需查看。full/default/详情保持当前信息范围。菜单及 unrecognized 主体沿用 default；顶栏仍独立使用共用摘要。

texts 保留：章节故事、教程、死亡原因、建筑师伤害、分数进度和非物品解锁均依赖它。title、按钮或分数的重复不另加自动去重。实现和验证见[实施记录](2026-11-03-result-observation-implementation.md)，当前尚未完成阶段 2。

## 验证与未覆盖范围

- 三个自有 GUI 案例均完成：death、victory_unlock、history。共 183 次真实 MCP 调用及 10 次显式原生测试调用；不将启动器内部状态轮询计入。7 个已采样 phase 为 epoch, history, outcome, summary, timeline, tutorial, unlock。
- 47 份 full 逐对象匹配来源，并通过当前观察结构校验；逐份确认现行 run_result.summary 主体与 default 相同。哈希、样本位置、下标及过程见本地 verification.json，原始流程见 gui/report.json。
- 自有 PID 为 14552, 15125, 15773，全部关闭；本轮未更换运行时 DLL、正式 Mod 或个人存档，未修改生产实现和测试，未重新运行整套编译及 Python 回归。
- 样本数量不等于穷举全部游戏内容：每日挑战榜单、各类解锁的全部内容、章节翻页、覆盖与动画瞬态、所有菜单子页及未知 Mod 页面未穷举；已区分源码核验、测试夹具与正常交互流程。失败结算及本局详情的混合语言缺口如上，未声称已修复。
