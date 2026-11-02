# 地图和卡牌浏览覆盖时的顶栏读取修复

> 当前状态：本轮修复与验证已完成。6 类 GUI 场景、17 个浏览位置、170 项原生检查、459 项 Python 及 60 项 C# 回归通过，顶栏观察与底层房间遮挡已分离，无本任务遗留。地图／牌组／牌堆的内容及实际摘要设计仍留待对应工具核验。

## 范围与根因

基础观察复用 RunUi.TopBarReadable；旧实现只接受未被遮挡的战斗、当前选择或非战斗房间。地图覆盖战斗、牌组／牌堆覆盖任何房间时，这些上下文判断失败，导致仍可见的顶栏返回 null；遗物和药水的只读查看也被同一条件排除。屏幕本身的 covered 与顶栏是否可见是不同条件。

前一轮[浏览覆盖核验](2026-11-02-get-observation-browsing.md)保留 24 份旧行为 full 示例；本轮不重写历史样本。已有问题报告为 `.tmp/2026-11-02-observation-browsing-review-report.md`。

## 核对基线

- 核对日期：2026-11-02，代码基线 34598f4；修复目标 Mod 0.49.1，MCP 为 0.50.1，schema 仍为 31。
- 游戏 Linux v0.107.1、release 59260271，RitsuLib 0.6.10。安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 重新核对程序集的 `NTopBar.AnimShow/AnimHide`、`NPotionHolder.OnFocus`；浏览与地图上下文沿用已核实的 CardView、MapView。源码证据仅存于 `.tmp/2026-11-02-top-bar-visibility/source/`。NTopBar 会独立移动至屏幕外，不能只依当前房间判断；药水悬停与使用流程分开。
- 本轮隔离 DLL SHA-256 为 `f6c4b3be3952e4020679c885292ca27ef5586fecdb54e6d943531b8eec5ae1f9`。

## 实现规则

[RunUi.TopBarReadable](../../src/Sts2Agent/Observation/RunUi.cs) 在原有可读上下文之外接受当前暴露的地图或受支持卡牌浏览页；先检查顶栏本身的视口、显示与透明度。新分支复用 MapView.Current 和 CardView.Current，继续排除弹窗、其他详情、未知覆盖和换页过渡。

生命、金币等仍取实际控件标签；单个标签不可读就保留其未知状态，不用模型补数值。遗物和药水详情沿用各自的可见、启用和可悬停规则。[动作可用性](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)及 CanHandlePotions 没有放宽；浏览覆盖继续阻止下层出牌、结束回合和原本不可用的药水操作。

所有预设共享修复后的原生读取。本次 0.50.1 验证中的 summary 浏览入口完整沿用 default；后续已将顶栏独立复用共用摘要，见[分工修复](2026-11-02-shared-top-bar-summary.md)。top_bar 预设仍使用其既有投影；本轮不增加地图节点详情或浏览卡牌列表。Python 的战斗地图白名单同步允许 inspect_potions，只接受只读查看；使用、丢弃和目标查询仍仅允许原来支持的非战斗地图。

## 验证与交付

新增 [GUI 套件](../../tests/game/data/gui_suite_top_bar_views.json)和[验证器](../../tests/game/verifiers/verify_top_bar_views.py)，覆盖战斗、待处理选择、事件、换幕、确认框和占卜。每个浏览位置检查多种预设、实际查看工具、原生隐藏控件及读前后状态。原生检查仅在 testMode 与隔离 suite 标志同时开启时可调用，不增加 MCP 工具。

- 构建 0 警告、0 错误；C# 60 项、Python 全套 459 项通过（35.458 秒）。构建与测试日志为证据根目录的 build.log、csharp.log、python.log。
- 6 类 GUI 场景通过，共 203 次真实 MCP 调用，17 个浏览位置的 170 项原生检查通过。涵盖地图、牌组、三类非空牌堆、地图叠牌组、选择背景、事件、换幕、占卜及确认框；查看、各预设和原生检查前后状态一致，下层非法动作被拒绝。
- GUI 证据分两批：gui-verified 前四项 combat／selection／event／entry 完成采样和局清理；该报告在确认框测试末尾因验证器未恢复许可而 failed。修正测试顺序后 gui-remaining 的 confirmation／divination 两项通过，报告 passed；两批使用同一 DLL，不把失败总报告写成整批通过。所有自有游戏进程均已退出。
- RED 证据：gui-red 使用旧 DLL 复现 top_bar:null；gui-green 在原生恢复后被旧 Python 白名单拒收，先补 Python 失败断言再修复。gui-final 则因测试连续发送非法动作、未恢复许可而失败；确认框同类测试顺序已一并修正。生产动作许可语义没有放宽。占卜入场实际支付金币，验证基线使用入场后的 UI 值。
- 本轮未穷举所有自定义覆盖页、所有分辨率／控制器布局或任意像素级遮挡；未知页面继续沿用原有保守规则。未测试每种资源在覆盖期间的变化事件组合，事件仍由各自可见性与生命周期约束。

证据根目录：`.tmp/2026-11-02-top-bar-visibility/`；汇总为 verification.json，完整样本映射为 samples-manifest.json。

本轮不安装正式游戏 Mod。修复需更新 Mod 后完整重启游戏；Python 公共参数和预设未变。

## 修复后的实际 full 样本

以下 9 份文件逐对象等于真实 get_observation(preset:full) 返回，保留所有原有空值和完整数组；不是由 inspect_* 响应拼接。证据下标从 0 开始，截图为相邻请求，未宣称同一帧原子采样。测试局数值不代表正常开局配置。

| 场景 | 完整 JSON | evidence.json 的场景／下标 |
| --- | --- | --- |
| 战斗地图 | [combat-map.full.json](2026-11-02-top-bar-visibility-examples/combat-map.full.json) | combat：2 |
| 战斗牌组 | [combat-deck.full.json](2026-11-02-top-bar-visibility-examples/combat-deck.full.json) | combat：31 |
| 抽牌堆 | [draw-pile.full.json](2026-11-02-top-bar-visibility-examples/draw-pile.full.json) | combat：42 |
| 弃牌堆 | [discard-pile.full.json](2026-11-02-top-bar-visibility-examples/discard-pile.full.json) | combat：55 |
| 消耗堆 | [exhaust-pile.full.json](2026-11-02-top-bar-visibility-examples/exhaust-pile.full.json) | selection：48 |
| 换幕地图 | [act-entry-map.full.json](2026-11-02-top-bar-visibility-examples/act-entry-map.full.json) | entry：3 |
| 换幕地图上的牌组 | [act-entry-deck.full.json](2026-11-02-top-bar-visibility-examples/act-entry-deck.full.json) | entry：13 |
| 占卜上的地图 | [divination-map.full.json](2026-11-02-top-bar-visibility-examples/divination-map.full.json) | divination：4 |
| 确认框：顶栏继续隐藏 | [confirmation.full.json](2026-11-02-top-bar-visibility-examples/confirmation.full.json) | confirmation：4 |
