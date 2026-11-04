# 战斗牌堆筛选与基础观察实施

> 当前状态：实现、验证及独立审查完成，共 4 项，已完成 4 项；inspect_pile 已核销，批准范围无遗留。新增 19 份真实 JSON 示例；未穷举范围与退出清理限制见下文。暂无阻塞。

## 范围与基线

依据[审阅定稿](2026-11-04-inspect-pile-review.md#输出定稿)和[实施计划](../superpowers/plans/2026-11-04-pile-inspection.md)，实现 PILE-01–05、card_ids、已打开牌堆的基础观察以及固定帮助精简。代码基线 `f076c0c`；Mod `0.59.0`、MCP `0.61.0`、schema `40`。现行版本统一见 [README](../../README.md#当前版本与前提)。

游戏 Linux `v0.107.1`，release build `59260271`；RitsuLib `0.6.10`。目标程序集及反编译成员核对沿用所属审阅，游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。构建与隔离运行时 Mod DLL 的 SHA-256 均为 `09e9ea505f49b918b20ae3b558ea55628753a588d2097e8251d4116dc5ed7788`。未安装正式 Mod，所有游戏验证使用隔离运行时／存档。

## 实现结果

- 原生共用 PileUnavailableReason 提供安全具体原因；inspect_pile 仅在请求未进行任何 UI 交互时声明 ui_unchanged:true，关闭旧页／点击之前即标记交互。MCP 复用已登记浏览工具的严格证据校验及已有许可保留，不凭失败创建许可。
- 参数／筛选迁至 pile_presets，响应类型／上下文校验仍在 pile_details。card_ids 仅作用 Python 输出和关联解释，底层只收到 pile；全量数据先校验。empty 可报告缺失，unavailable 不判断成员。
- GameObservation 持有 PileInspection，静态观察和专门查看共用战斗内身份表。full:false 读取完整网格静态牌面，full:true 增加正文及悬停解释。基础观察校验 pile/cards/message 的原子组合，当前页关闭或遮挡后不附缓存。
- 基础观察 full/default/summary 分别为 face_full／face_default／summary；两入口的 opened 固定 message 在 summary 省略，empty／unavailable 反馈保留。共享装配不向 get_state 添加空或完整 hover_tips。
- 普通文件 CLI 支持 --card-ids，复用同一参数归一化与输出投影；旧 MCP 专项关闭断言改为 actions_only，历史冻结 JSON 保留原基线，测试中仅适配已批准差异。

现行完整契约见[牌堆指南](../development/pile-inspection.md)。

## 游戏验证发现的额外正确性问题

**PILE-06：选牌战场视图打开牌堆后，同页再读被错误拒绝。** 初次打开成功，但选牌容器中的入口按钮被当前卡牌页隐藏，旧整体门控仍要求下层按钮可见，导致 inspect_pile 从 available_actions 消失，后续同页读取得到 illegal_action。证据为 `.tmp/2026-11-04-pile-implementation/gui/pile_battlefield/verify/evidence.json`。

修复范围仅允许上下文仍有效、当前已暴露且就绪的牌堆页复用，不依赖被覆盖的下层入口；换堆仍检查实际目标按钮，隐藏目标不点击也不补内容。首批 GUI 前三局通过、第四局因此失败，原失败目录保留；修复后以同一用例复测，不删断言或放宽遮挡边界。

## 验证与未覆盖范围

新增 8 项 Python 专项先观察到缺功能失败，之后转绿；首轮全套发现公开 schema／summary 冻结预期及简化分发探针与新投影不符，采用精确差异适配，没有批量重生成样本。全套 **623 项通过**（40.517 秒），日志 `.tmp/2026-11-04-pile-implementation/python-all.log`；C# **91 项通过**。原生构建无警告／错误，证据目录同时保存失败、转绿和最终构建日志。

最终四局 GUI 及正常局清理全部通过，报告 `gui-final/report.json`；覆盖非空三堆、空堆／隐藏入口、null／[]／重复／部分成功筛选、固定帮助、静态观察与完整原生状态前后相等、同一 ID、关闭后直接 end_turn、火堆选牌拒绝后直接 selection_option，以及战场视图的重复查看和返回选择。前一批 gui 的 PILE-06 失败证据保留；修复后的同一用例转绿，不改失败断言。

更新后的 verify_piles、verify_mcp_piles 在真实游戏中均通过。原生边界 **30 项通过**，报告 `native-final/report.json`；包括长列表／离屏卡、原生重排、跨堆身份、临时能量／星数费用、Corruption 上下文、模型／RNG／语言不变，以及关闭／覆盖／换页期间拒绝并保留人的新页面。

首批 `native/report.json` 的 29/30 项通过，空弃牌气泡总数断言失败：两份专项刚产生的既有气泡在前后计数间消失。返回的 empty、关闭后的 screen 与变化后的 token 正确；核对 NThoughtBubbleVfx 的 2 秒展示和 0.4 秒淡出后，验证进程在暴露战场等待 3 秒让既有反馈结束，再执行相同原生检查，30/30 转绿。未改生产逻辑或原生断言，原失败日志保留。两个原生独立实例均在检查结束后 terminate 等待未退出而强制清理，exit_code 为 -9；检查通过不代表正常退出已验证。所有自有游戏进程均已关闭。

[19 份完整真实 stdio 示例](2026-11-04-pile-inspection-implementation-examples/README.md)及 manifest 保存参数、来源条目和 SHA-256；实际返回的 text JSON 与 structuredContent 在每次 GUI 调用中逐对象核对。旧审阅 31 份示例保持原基线，未重写为新行为。

独立只读代码审查未发现 Critical／Important／Minor 问题；额外核验 19 份示例哈希及原始参数／返回均一致。审查未启动游戏，不单独判断原生测试和所有未覆盖场景；实际游戏验证由上述隔离检查提供，剩余边界继续明确保留，不据此宣称穷尽验证。

尚未穷举所有卡牌／附魔／Affliction、所有选牌来源、多人、第三方页面或任意转场。现有待办仅更新已授权事项：牌组／牌堆覆盖完成；错误恢复与错误准确性提前覆盖九个工具，其他工具仍待逐项核验。交付保留当前 feature 分支及证据，不安装正式 Mod、不推送或合并。
