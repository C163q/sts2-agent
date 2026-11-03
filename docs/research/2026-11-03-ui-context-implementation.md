# inspect_ui 修复与场景上下文统一

> 当前状态：已完成，3/3 项交付。原生上下文与顶栏、MCP 校验与预设、验证与文档均完成：496 项 Python、60 项纯 C#、目标程序集构建、11 局跨场景 GUI 及独立终章通过。无本轮阻塞；原奖励夹具取消链和未新实测的既有变体保留明确边界。

需求、修复前完整样本及集中问题表见 [inspect_ui 核验](2026-11-03-inspect-ui-review.md)。本记录负责该次实施证据；现行契约见 [UI 帮助](../development/ui-inspection.md)和[统一上下文](../development/observation.md#场景上下文)。

## 基线与范围

- 起始提交 `0ad1060`，Mod `0.49.3`、MCP `0.50.8`、schema `32`；本轮更新为 Mod `0.50.0`、MCP `0.51.0`、schema `33`。当前版本仍统一维护于 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`、release、build `59260271`，RitsuLib `0.6.10` 兼容包。目标游戏程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 最终构建与隔离运行时 DLL 的 SHA-256 一致：`eedee2ff5b7ba98325f8b42bf03fe19767094ba8fa0b807864820ee59ca80e30`。GUI 使用中文 UI、新建测试存档与真实 stdio MCP；不安装正式 Mod、不修改正式存档。
- 保留原生动作、合法性与信息边界，不补读被遮住的战斗资源。本轮不扩展地图／牌堆内容摘要，不修复原先记录的自定义奖励 Pending 取消链。

## 实现

### 1. 原生上下文与 UI 区域

- [ObservationContext](../../src/Sts2Agent/Observation/ObservationContext.cs)统一场景、可见／覆盖状态与页面判断；AvailableTools 只枚举动作，场景判定不再混在动作列表中。
- [InspectionSuccess](../../src/Sts2Agent/Adapter/GameAdapter.Inspections.cs)从内容响应对应的观察快照复制 snapshot_id、scene、screen，避免重新采样后把旧令牌与新上下文混合。地图、牌组、牌堆采用打开／修改后的快照；选牌升级切换也更新所复制的快照。
- 所有原先返回 scene 的详情工具迁移到该入口，包括 UI、战斗对象、选牌、地图、牌组、牌堆、各房间与结算。MapInspection、DeckInspection、PileInspection、CombatantInspection 不再按内容类型写场景。
- [UiInspection](../../src/Sts2Agent/Observation/UiInspection.cs)将顶栏、战斗区域和共同提示整合分别处理；可用列表及执行入口共用 CanRead。结算提前返回分支也检查可见顶栏，保留没有可读区域时的拒绝。
- 顶栏生命来源改为 top_bar.hp/top_bar.max_hp；头像与进阶帮助关联 top_bar.ascension，消除非战斗 player:null 时的错误来源。

### 2. MCP 校验、筛选与摘要

- [scene_context](../../src/sts2_mcp/output/scene_context.py)提供共同上下文校验与投影；不为旧 map/deck/card_pile 场景值保留别名。页面仍按对应工具的 screen.view、打开状态与内容结构校验。
- 牌堆共享提示改按牌堆数据识别，不再依赖 scene:card_pile。动作许可仍依据完整原生响应，不因 summary、筛选或部分未匹配来源而改变。
- [ui_presets](../../src/sts2_mcp/output/ui_presets.py)新增 sources 精确筛选和 summary；summary 仅省略帮助正文，保留标题、匹配来源与上下文。完整校验先于筛选，坏的未选中条目仍拒绝；非法参数不进入 IPC，并保留既有本地参数拒绝许可策略。

## 实施审阅发现与处理

| 编号 | 影响与证据 | 处理及验证 |
| --- | --- | --- |
| REV-01 | 建筑师打开牌组后，新 inspect_ui 被 Python 的 covered/deck 白名单拒绝，合法观察可能 transport_error | 补白名单；EndingUiHelpTests 正向回归与原有覆盖动作负向回归通过；终章 GUI 增加牌组与地图往返 |
| REV-02 | 结算动画未就绪、顶栏已可读时，新 inspect_ui 被 not_ready 白名单拒绝 | 补合法查看动作，同时拒绝无顶栏却广告 UI 帮助；已先复现后通过对应正／负回归 |
| REV-03 | 战斗对象详情额外限制 combat/epilogue，可能拒绝战斗结束钩子期间的合法 unrecognized 背景读取 | 移除额外场景白名单，保留公共场景及内容校验；新增 unrecognized 合法详情回归。瞬时游戏窗口未人工复现，依据目标程序集 CombatManager.EndCombatInternal 先结束战斗再等待钩子的执行顺序 |

以上为独立只读审阅发现的实施遗漏，均已修改，复核未发现新实质问题。审阅覆盖快照绑定、页面迁移、可见性边界、全量响应校验、参数拒绝及摘要许可链；不替代游戏行为验证。

## 验证证据

- 新增单元回归先验证旧页面场景、非战斗 UI 校验及未实现摘要失败，再补实现；终章白名单也先复现拒绝后修复。
- 目标程序集构建通过，0 警告、0 错误；纯 C# 检查 60 项通过。最终 Python 全量 496 项通过，结果为 `.tmp/2026-11-03-ui-context-implementation/python-final-2.log`；旧断言迁移与实施审阅的失败日志另存，不覆盖最终证据。
- [跨场景套件](../../tests/game/data/gui_suite_ui_context.json)共 11 局，通过真实 MCP 检查 UI full/default/summary、来源筛选、缺项合并、空列表、重复读取、上下文一致与读取不变性。覆盖战斗／球槽、事件、火堆、宝箱、先古之民、商店、奖励、手牌选择、试炼确认及占卜，含地图／牌组／弃牌堆覆盖。
- 第一轮 GUI 在先古之民不变性断言处停止。原始快照差异只有选项 enabled、available_actions 及对应令牌：入场动画完成后选项自动启用。验证器改为等原生交互就绪再建立基线，保留严格不变性检查；占卜只排除随视觉动画变化的 PNG 字节，仍比较完整逻辑状态。最终套件使用新目录重跑全部 11 局通过。
- 最终套件证据：`.tmp/2026-11-03-ui-context-implementation/gui-final/report.json`，每局含真实 MCP evidence.json、截图、日志和进程／对局身份。第一轮失败证据保留在同目录的 `gui/`，不覆盖。

- 独立终章验证通过：建筑师、其牌组／地图覆盖、返回对话、通关结果和摘要；每处比较 UI/相关详情与基础观察的 scene/screen。证据为 `.tmp/2026-11-03-ui-context-implementation/ending-final/`，与最终套件 DLL 哈希相同。
- 两段最终 GUI 共 402 次 MCP 调用，其中 inspect_ui 205 次；导出的[上下文比较](2026-11-03-ui-context-examples/context-pairs.json)包含 53 对相同画面的上下文，既有 scene 的全部 13 个详情工具（含 UI） 均有实测。12 份 UI 完整返回及来源见[样本清单](2026-11-03-ui-context-examples/manifest.json)。
- 文档链接、内嵌 JSON、公开工具 schema、11 个套件用例清单、最终构建／运行时哈希一致性核对通过，见 `.tmp/2026-11-03-ui-context-implementation/docs-validation.json`；样本均逐字段对应最终原始证据。所有自有游戏进程已关闭。

## 交付边界

头像进阶、双首领、修改快捷键等既有变体按源码保留，未在本轮重新逐项制造。战斗结束瞬时窗口以源码和协议回归核对；不声称所有动画帧均有 GUI 采样。原奖励夹具清理限制继续见 `.tmp/2026-11-03-inspect-ui-sampling-report.md`，不将其混作 inspect_ui 读取故障。

本次 Mod 和 MCP 需一并更新；旧地图／牌组／牌堆 scene 值不再适用。正式安装与游戏重启尚未执行。
