# 可浏览内容的视口筛选审查与修复

> 当前状态：修复与验证完成。共 4 项，已完成 4 项；奖励及本局详情滚动漏读已修复，8 类图形场景、15 项原生边界、461 项 Python 与 60 项 C# 检查通过。Mod 0.49.2，MCP 0.50.2／schema 31 不变，未安装正式 Mod。get_observation 的 07–09 组 summary 设计待继续，无阻塞。

## 范围与约定

基线 `8b7a3ce`，MCP 0.50.2、Mod 0.49.1、schema 31。核对 Linux 游戏 v0.107.1、release 59260271、RitsuLib 0.6.10；程序集为游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。

当前已打开页面中，玩家可滚动或平移查看的列表应完整读取；视口位置不能截断列表。保持原生顺序、身份和已揭示状态，不自动打开其他页面、展开悬停或获取未来内容。读取范围与点击条件分开；点击前仍使用原生合法性及必要的滚动定位。

实现沿用两种已存在的读取方式：虚拟化卡牌网格按原生完整列表读取；已实例化的滚动内容按其控件读取。只删除裁掉可浏览内容的几何约束，不全局移除 OnScreen，不把透明、整栏隐藏、动画移出屏幕或未揭示内容当成可浏览列表。

## 全面检查结果

检查 [Observation 目录](../../src/Sts2Agent/Observation)、[选择动作](../../src/Sts2Agent/Actions/CardSelection.cs)及三类选择预览，搜索 OnScreen、Shown、CardVisible、文本／数字读取及集合筛选。按实际 UI 容器分组，不按函数中含有 visible 就认定有错。

| 读取范围 | 核对结果与处理 |
| --- | --- |
| 奖励列表，get_observation／inspect_rewards | 基础观察按标签 OnScreen 截断；详情已经读取全表。统一为当前已展示的完整奖励列表，隐藏标签不补出，保留完整效果仅详情提供 |
| 结算后的“查看本局”，get_observation／inspect_run_result | NRunHistory.ScreenContents 使用原生 NScrollableContainer；Text、遗物、药水等仍按视口筛选。增加共用的滚动内容可读判断，在结算读取中使用，动作按钮仍按真实可点击状态判断 |
| 地图／时间线 | 地图节点和连线已经使用 Shown；时间线条目同样不按视口截断，保留问号、已揭示状态及原生可用操作，无需扩大模型读取 |
| 永久牌组／三类战斗牌堆 | 已读取原生完整可浏览列表，不依赖当前实例化卡牌数量，无此类截断。get_observation 中浏览主体仍是之前约定的占位，实际内容留待对应工具核验 |
| 卡牌选择网格 | 已按完整排序列表读取，包含虚拟化网格之外的候选。候选隐藏、未知牌面和预览仅显示一侧的规则保留 |
| 手牌／三选一／卡牌包／升级、附魔、变牌预览 | 目标界面为固定布局或原生已展开预览，不是可滚动列表；部分卡牌叠放、随机图像或预览前后侧的过滤保护未展开信息，不读取未显示的正文或随机结果 |
| 火堆／商店／事件及先古之民选项／宝箱 | 目标版本固定布局，没有上述完整列表的滚动控件；保留真实显示、灰置、入场、覆盖及悬停边界，不能把非滚动布局的画外对象视为可达 |
| 战斗对象／powers／意图／球栏位／剑／顶栏数字 | 用于当前画面或动画可见性的判断，不是浏览列表截断；保留，不从模型补齐缺失数字 |
| 持有遗物清单 | 已取消视口几何截断，保留控件显示及悬停合法性；计数与熔化表现仍取实际显示，不从内部数值补出 |
| 药水栏／资源入口／占卜／确认框／终章 | 固定位置与未展开／雾下信息边界，无可滚动列表遗漏；保留当前判断 |
| 结算分数、解锁、发现 | 非滚动区域仍按实际显示读取，未完成动画／隐藏解锁不补出；原生发现悬停本身仅列前十项的规则保留，不能误当作接口截断 |

新反编译证据位于 `.tmp/2026-11-02-browsable-content/source/`，含 NRewardsScreen、NRunHistory、NScrollableContainer、NDeckHistory、NRelicHistory、NGameOverScreen、NRunSummary、NEventLayout、NMerchantInventory、NCardGrid、NCardBundle 等；不纳入 Git。已核对的浏览与遮挡规则需同步至[信息边界](../observation.md)、[奖励](../development/rewards.md)、[结算](../development/run-ending.md)和[观察](../development/observation.md)。

## 实施计划

- [x] 全面检查读取与筛选，核对目标版本容器及原生行为，记录应改和应保留的范围。
- [x] 先用真实 MCP 回归复现奖励末行漏读、结算详情滚动后遗漏；保存失败证据，再修改生产代码。
- [x] 统一奖励读取；添加仅适用于原生可浏览内容的共用判断并接入结算文字、物品与悬停解释。核验隐藏／透明、非滚动画外对象、覆盖与读取不改状态，更新版本与文档。
- [x] 完成原生构建、C#／Python 检查及隔离 GUI 回归，补齐实测 JSON、问题报告和清单状态，交付时创建英文 Conventional Commit。

重点回归：奖励完整列表与 ID 不变、画外行实际可领取；浏览不改变滚动位置；本局详情顶部／底部内容同时可读；隐藏控件仍不可读；其他非滚动场景／动画不扩大；未展开牌堆主体占位与选牌摘要保持既有规则。沿用已授权的主工作区，不安装正式 Mod。

## 最终实现

- [RewardInspection](../../src/Sts2Agent/Observation/RewardInspection.cs) 的基础与详情读取都遍历当前完整奖励行，只排除真正隐藏的标签；full 仍仅在显式详情中附带悬停解释。领取保留原生 Reveal 定位，末行奖励的直接领取及其他 ID 不变已经实测。
- [VisibleUi.Browsable](../../src/Sts2Agent/Observation/VisibleUi.cs) 复用静态可见判断，并允许目标原生 NScrollableContainer 当前内容的垂直浏览范围；保留水平边界、内容范围、内层裁剪和隐藏／透明检查。非滚动控件保持原有判断，不改全局 OnScreen。
- [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs) 的文字、物品、牌面及悬停内容复用这一入口，读取前检查文字已显示完整；动作按钮仍使用原有可点击条件。[CardVisible](../../src/Sts2Agent/Observation/CombatObservation.cs) 的原有调用保持静态可见规则，结算读取显式选择可浏览判断。
- 公开参数、字段和 schema 不变；Mod 增至 0.49.2。信息边界、奖励、结算及图形验证文档已同步。基础观察的浏览主体占位、其他工具的摘要设计和已有附魔缺口不在本轮范围内。

## 验证与证据

审查始于 2026-11-02，最终验证完成于 2026-11-03。最终产物和隔离运行时 DLL 的 SHA-256 均为 `1d1a7e8c180bbb05b15f3ee8a5dbbf098485685dda393466eb3e5356e6d403ed`。

- 原生构建零警告／错误；C# 60 项通过；Python 461 项通过，34.550 秒。日志位于 `.tmp/2026-11-02-browsable-content/` 的 build-reviewed.log、csharp-reviewed.log 和 python-reviewed.log。
- [图形清单](../../tests/game/data/gui_suite_browsable_content.json) 8 类场景全部完成并正常清理，最终 gui-reviewed/report.json 为 passed；68 次真实 MCP 调用、13 次受门控测试调用、15 项原生边界检查通过。最终自有 PID 137530 已关闭，没有更新正式游戏 Mod。
- 奖励 full/default/summary 都包含完整 6 行；卡牌入口尚未展开时 selection:null，无候选泄漏。直接领取画外卡牌入口后按正常选牌处理；其他奖励 ID 保持，地图／选牌覆盖时隐藏奖励，领空后 items:[]。
- 本局详情的长内容、滚动不改变结果、隐藏、透明、水平越界、内层裁剪、非滚动画外文字及完整恢复均通过。目标版本禁用 View Run，因此仅测试夹具调用原生历史生成流程并打开原生页，另加长 UI 标签验证滚动；没有启用正常入口，不把它描述为正常可点击流程。
- 实际检查事件、先古之民、火堆、宝箱、商店展开前后、战斗、地图和牌组共 9 个画面，未发现遗漏的当前活动 NScrollableContainer／ScrollContainer；这些场景的固定布局与已核对的原生代码一致。网格、奖励、地图和时间线另有各自的原生浏览机制，不能仅凭没有这两种控件就判断不可浏览。
- 逐文件来源、调用位置、容器列表及计数见本地 verification.json；完整 JSON 直接来自相同最终 DLL 的 structuredContent，文字 JSON 在验证器中逐次核对。

| 当前实测响应 | 本地 evidence.json 下标 | 内容 |
| --- | --- | --- |
| [rewards.full.json](2026-11-02-browsable-content-examples/rewards.full.json) | gui-reviewed/rewards/verify：0 | 完整基础观察，保留 null；六行奖励，无未展开候选或悬停解释 |
| [rewards.default.json](2026-11-02-browsable-content-examples/rewards.default.json) | gui-reviewed/rewards/verify：3 | 同一奖励列表，应用公共空值规则 |
| [rewards.summary.json](2026-11-02-browsable-content-examples/rewards.summary.json) | gui-reviewed/rewards/verify：4 | 同一奖励列表，顶栏复用四字段摘要；房间主体尚未另定摘要 |

## 审阅、失败记录及边界

独立只读审查未发现生产 Critical／Important 问题，发现一项测试条件错误：夹具最小高度使裁剪矩形没有真正缩小。已清除／恢复最小尺寸并断言实际高度，最终整套 8 类通过。首批 green 及历史夹具准备失败记录均保留，未将其写成整批成功；细节见本地[问题报告](../../.tmp/2026-11-02-browsable-content-report.md)。

有效 RED 分别是 gui-red-rewards 的 5 行／预期 6 行，以及 gui-red-history-long 的离屏标签遗漏、滚动后返回改变；此前历史夹具的缺失进度／历史和短列表未溢出不属于有效复现。没有为迁就测试修改生产点击、入口或历史数据。

本轮核对现有读取分支并实测上述容器与边界，没有穷举所有事件内容、所有结算解锁组合或第三方 Mod 页面。原有历史英文转写、历史卡牌展开等独立问题未混入本次修复；正常 View Run 入口仍遵循目标游戏自身限制。
