# 第 7 阶段：架构重构验收

> 当前状态：已完成并验证，阶段清单 5/5，整体 7/7。RF-01–RF-14、组合回归、完整样例与清单收尾均已完成；当前无正在执行步骤，暂无阻塞。

## 范围与基线

按[重构计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)收尾，从 `b45b9fe` 继续。前六阶段的行为基线、实施和失败修复证据分别保留在原阶段记录，本页核对最终职责与本轮验证，不改写历史报告。

核对 Linux 游戏 `v0.107.1`（release build59260271）和 RitsuLib `0.6.10`。游戏目录 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。来源版本仍为 Mod `0.55.0`、MCP `0.57.0`、schema `36`；本轮仅清理内部转发及补充验收，不新增公开行为。持续维护的版本表只在 README。

## 兼容入口处理

| 入口 | 当前使用者与处理 |
| --- | --- |
| `player_result`／`game_output.gameplay_fields` | 原有直接调用、文件客户端的错误分支及大量片段验证仍使用；保留兼容输出，不用于生产成功解码 |
| `roundtrip_client.player_result`、脚本 Client／main 导入 | 文件客户端、旧验证器与测试实际引用，保留 |
| `output.presets` | 多个 GUI／Python 验证器及 CLI 引用；仅转发共用 null 规则，没有第二份实现，保留 |
| `game_output.observation_details/TOP_BAR` | 旧测试仍引用，保留；实际定义在领域读取器／纯契约 |
| `mcp_server.GameTools/ControllerLease` | 服务组合和既有导入使用，保留 |
| 原生 `ObservationContext.Inspection` | 唯一调用者可直接使用 ResponseBuilder；移除转发，让 ObservationContext 只负责场景／页面判断 |

未以“重构”删除仍有使用者的片段接口，也不将旧文件客户端的输出范围统一成 MCP 回执。源码与调用者核对使用 `rg`，快照／响应纯检查和完整输出基线验证转发移除没有改变结果。

## RF-01–RF-14 核对

本表对应[初始审查问题](2026-11-03-architecture-refactor-audit.md)，以职责与行为证据验收，不以文件大小或检查数量替代验证。

| 问题 | 最终处理与保留边界 | 代码与验证入口 |
| --- | --- | --- |
| RF-01 原生职责混杂 | Capture／代际由 GameObservation 持有，生产路由、测试路由、页面／等待、响应分别负责；领域原生操作保持原流程 | GameObservation、RequestDispatcher、TestRequestDispatcher、ResponseBuilder；快照纯检查与组合 GUI 的路由／页面／跨场景 |
| RF-02 输出依赖 | 纯 contracts 与领域读取器向下依赖；生产成功统一 decode_success，领域不反向依赖总装配 | test_output_architecture 对函数内导入也检查无环及方向 |
| RF-03 多处登记 | ToolSpec 为 catalog、handler、reader、preset 与执行规则的来源；原生 RecordedActions 独立但有跨层一致性检查 | tool_registry、test_tool_registry；原生测试操作不进入目录 |
| RF-04 恢复规则 | GameSession／PermissionState 统一许可；读取、页面、副作用和明确未提交证据独立，不按 inspect 名称猜测 | test_session_policy、test_inspection_errors、test_action_observations；0 能量拒绝后 end_turn |
| RF-05 媒体耦合 | 私有 response_options 控制捕图，执行事实在 Capture／UI／提交处记录；丢弃媒体的回执不因 PNG 失败拒绝 | test_native_response_contract、native_responses 占卜故障夹具；故障为注入，不冒充自然问题 |
| RF-06 重复转换 | 生产完整校验、工具装配、筛选／摘要、null 过滤各一层；卡牌模式由调用范围指定。大范围投影仅保留给直接片段兼容 | response_pipeline、public_output、card_format；冻结输出回放与坏嵌套值检查 |
| RF-07 成功上下文 | hand／targets／potions／relics 同次快照补 scene/screen；详情不因此添加 available_actions | ResponseBuilder.Inspection、inspection_details；本轮四个工具的完整实测样例 |
| RF-08 来源引用 | 遗物映射与提示均引用未筛选下标；筛选不重编号来源 | relic_preset／linked_help；筛选 Lantern 的原下标与提示样例 |
| RF-09 筛选空值 | 可选 sources／card_ids／relic_indices 省略或 null 全部、[] 为空；工具特有匹配含义保留 | optional_filter、参数矩阵；本轮真实 UI／手牌／战斗对象／遗物／选牌调用 |
| RF-10 展示与悬停 | 共用遗物展示集合，无法悬停保留静态字段，full/default note，summary 不读说明 | RelicInspection、HoverAccess；31 项原生遗物检查与来源筛选样例，关闭入口为夹具 |
| RF-11 位置策略 | 遗物计数／melted 与条目同用展示规则；真实裁剪和隐藏继续排除。战场身体、可点击入口、浏览列表不机械合并 | 第 6 阶段调用点清单；容量／熔化、充能球入场与裁剪、地图／牌堆 GUI |
| RF-12 事件组装 | TransitionResult／ResponseBuilder 结构化组装、统一 complete 与事件缓冲附加；领域 stop_reason 和捕获机制保留 | NativeResponseChecks、事件／奖励／商店／火堆／宝箱、战斗交接与结算 |
| RF-13 客户端分流 | MCP 与非 raw CLI 生产成功共用 decode_success；CLI 的历史默认和完整观察范围显式保留 | test_tool_contracts 的 MCP／文件基线、test_output_boundaries、标准库 CLI |
| RF-14 页面与可用性 | 场景／页面来自共用快照；单人条件移入 RunContext，悬停／静态片段由领域共用。原生跨 await 复核及不同 UI 入口条件保留 | ObservationContext、AvailableTools 的 Can*、RunUi／RunContext／HoverAccess；顶栏、浏览覆盖、场景与回执检查 |

## 组合回归与样例

[组合清单](../../tests/game/data/gui_suite_architecture_refactor.json)共 24 场景、30 步，复用现有验证器；完整结算独立进程。覆盖战斗与拒绝恢复、附魔／Affliction、充能球／奥斯提／君王之剑、升级比较、地图／牌组／牌堆、遗物／药水、奖励／火堆／宝箱／商店／事件／先古之民、占卜、战斗交接及建筑师背景。

本机证据根目录：`.tmp/2026-11-04-refactor-stage-7/`。本轮构建与隔离运行时 DLL SHA-256：`4a0b79dd4b7e5cb901ddf6f37f1b4f2d3b0b24972c3bc540e624c96bab98bae6`。组合 GUI 分主批 23 场景／29 步与补充药水动作 1 场景／1 步，全部通过；完整返回和逐项请求见[26 份样例](2026-11-04-refactor-contract-examples/README.md)。样例与通过的源条目逐份 JSON 值相等，源证据／样例文件哈希、实际请求、公开字段边界及同 DLL 哈希已全部核对。独立胜利结算与解锁至返回主菜单同构建通过。

## 未扩大范围

- 用户 TODO 完成数和逐工具核销仍保持原状；本次没有对照用户保存的全部错误实测记录。
- 不实现地图／牌组／牌堆主体 summary、占卜文字、商店上下文或知识库。
- 没有穷举第三方 Mod 的自定义 UI、像素遮挡及提示；不把人为关闭悬停入口当作自然机制。
- 不安装正式 Mod，不推送或改写提交历史。后续恢复原清单的逐工具审阅。

核对新增组合范围时发现手牌旧 GUI 断言仍只允许 hand／资源字段，尚未纳入第 5 阶段的 scene/screen；已按当前契约补齐，并核对其与同次基础观察一致。该调整只更新验证，不修改玩法来满足旧断言。

## 独立审查

最终源码只读审查核对 RF-01–14 与跨阶段的许可、媒体、筛选和原生生命周期，未发现 Critical／Important／Minor。审查者独立通过 24 项窄纯检查和 diff 检查；混合异步检查在其沙箱内 55 秒超时，未得到完整结果，不算通过。全量、C#、编译及真实 GUI 由实施者执行，不宣称审查者独立验证了这些结果。

审查时完整 JSON／manifest 尚在生成，不能据此预判验收。实施者须逐文件对照通过运行的源证据、实际请求、文件哈希和统一 DLL 哈希。第三方任意渲染与用户尚未对照的历史实测仍保持原范围，不借本轮核销。

## 本轮验证结果

- 全量 Python **582 项通过**（39.949 秒），C# 纯检查 **91 项通过**，Mod 编译零警告、零错误。
- 输出依赖检查通过：62 个输出模块、146 条导入边，无循环；43 个工具的 catalog／handler／reader／参数登记对应，21 个 transition／记录事件工具与原生名单一致。统计本身不替代相应行为断言。
- 组合 GUI **24 场景、30 步通过**（主批 23/29，补充药水触发战斗 1/1），包括本轮新增 null／[]、四种详情上下文、附魔及升级比较。补充场景复用既有假商人夹具以验证 use_potion 动作和跨场景回执；没有重跑已经通过的其他场景。两个报告分别是 `gui/report.json` 和 `gui-potion/report.json`，均使用同一 DLL。
- **26 份完整公开 JSON**核对通过：每份记录实际 MCP 参数、源文件与条目索引、源文件／样例 SHA-256；未人工删改字段。Lantern 提示仍指向位置 2，筛选后的缺失悬停 note 仍指向 relics.3；五组 null／[] 的真实结果分别验证。
- 独立 victory_unlock **通过**（`gui-ending/report.json`）：127 次工具调用，包含奖励、建筑师对白、胜利结算、发现、解锁和返回主菜单。同样使用上文构建哈希。标准库 CLI `--help`、compileall 与 diff 检查通过；完整汇总见 `.tmp/2026-11-04-refactor-stage-7/verification-summary.json`。

本机汇总及日志保留于上文证据目录；已提交的样例不依赖 ignored 目录来阅读，历史原始输入仍按原有边界保留。

## 交付与后续入口

七个阶段全部完成；原[逐工具核验清单](2026-11-02-mcp-tool-review.md)恢复内容审阅，仍只核销 inspect_ui、inspect_hand、inspect_targets、inspect_combatants 四项。get_observation 的浏览主体和其余工具仍按原范围处理，不因架构验收增加完成数。用户 TODO 未改动，正式 Mod 未安装。

实现保留三类有意差异：工具各自的信息范围与预设、卡牌／对象身份生命周期、CLI 的历史默认与片段兼容。它们不再各自复制共用校验和许可规则。最终源码独立审查没有延期问题；样例形成晚于该审查，由实施者按逐文件相等及哈希校验完成验收，未宣称样例获得独立二次审查。

内部转发清理独立提交为 `00f8b12`（`refactor: remove redundant inspection response forwarding`）；组合清单、验证器、样例和验收文档作为后续独立测试提交交付。
