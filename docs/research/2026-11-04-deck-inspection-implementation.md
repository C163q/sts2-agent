# 牌组筛选、基础观察与关闭返回实施

> 当前状态：实现、验证及独立审查完成。4 项计划已完成 4 项，无未完成的批准功能；交付提交由所属 Git 历史定位。没有安装正式 Mod。依据[实施定稿](../superpowers/plans/2026-11-04-deck-inspection.md)；总清单中的工具核销在最终验证后更新。

## 已实现契约

- inspect_deck 新增 card_ids 字符串筛选；省略／null 全部、[] 为空、去重按原生排序；无效 ID 合并 errors，有效牌及其共享解释保留。不向原生转发筛选，完整原生数据先校验。
- 原生牌组明确拒绝公开安全具体原因，分别说明入口、选择覆盖、升级／排序控件及读页变化。异常和路径仍留在私有诊断。
- 原生显式 error.ui_unchanged 是“该请求未交互”的保证，只有登记的 inspect_deck 才据此保留已有许可；没有旧许可不生成许可，其他页面工具不继承。与正向交互或提交事实矛盾的保证按坏响应拒绝。
- close_card_view 的成功输出统一为 get_observation.actions_only：scene、screen、available_actions，以及实际存在的 selection.type/status。原生完整快照仍校验，之后才裁剪；所有公开通用 preset 返回相同最小结构并刷新许可。MCP 与普通 CLI 不为该结果请求占卜棋盘图像。
- 基础观察在已打开、就绪且未受更高层遮挡的牌组页，提供完整 deck、view_upgrades 和 sort。full/default/summary 的牌面分别为 face_full／face_default／共用摘要，均不带正文和悬停解释；排序、ID 和升级状态与专用工具一致。

DECK-03 不再以“补齐关闭后的房间正文”为目标：关闭是操作，确认后的目标是最小操作上下文。原审阅指出的是旧输出白名单与当时说明的矛盾；现行要求及说明已统一。需要详细画面时按信息需要读取，不强制为续接许可再观察。

## 小范围重构

- DeckInspection 由 GameObservation 持有；基础观察和专用详情共用实例 ID、网格顺序及克隆预览，分别选择静态或完整内容。不把两次不同读取的 ID 表拼接。
- 原生读取只读取当前页面，页面操作仍在适配器中；升级／排序的可用性检查在交互前进行，明确拒绝不会点击其他控件。
- Python 参数／筛选从响应校验中分离为 deck_presets；CLI 与 MCP 使用同一请求归一化和投影。close_card_view 复用观察校验与 actions_only 投影，地图及旧 close_deck 的兼容读取移至 view_details，不改变这些未定稿工具的公开行为。

## 核对基线及证据

- 实施基线 `456ec34`；Mod `0.58.0`、MCP `0.60.0`、观察 schema `39`。当前兼容表唯一维护在 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`，release build `59260271`，RitsuLib `0.6.10` 兼容运行时。目标程序集为游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 已核对 NDeckViewScreen、NCardsViewScreen、NCardGrid、NTopBarDeckButton 的 ShowScreen、SetCards、IsShowingUpgrades、ToggleShowUpgrades、排序和显示入口；反编译证据沿用[审阅来源](2026-11-04-inspect-deck-review.md#核对基线及来源)，不纳入 Git。
- GUI、构建及隔离运行时 DLL 的 SHA-256 均为 `40e3ba694e13236c862d8f80dff3c6c6294861ab5569eebd36e50125601c3ed6`。正式安装未更新。
- [14 份完整真实 JSON](2026-11-04-deck-inspection-implementation-examples/README.md)及 manifest 保留完整来源；不是手工补全后的预期输出。

## 验证

证据根目录为 `.tmp/2026-11-04-deck-implementation/`。

- 新专项测试先失败于筛选未接受、关闭返回过多、观察缺少 deck 以及明确拒绝清除许可，`python-red.log` 记录 16 个失败子用例与 1 个缺字段错误；对应 45 项专项转绿见 python-green.log。
- GUI RED 在旧 Mod 上失败于 get_observation 未返回已打开牌组，不是启动或编译错误；随后接入原生共享读取。
- 构建 build-final.log：零警告／零错误；csharp.log：91 项通过。
- Python 完整回归 **615 项通过**（35.901 秒），包括普通 CLI 禁用棋盘图像的独立 RED→GREEN 回归；最终日志 python-verified.log。
- 六个 GUI 测试局全部采样及清理通过：战斗、事件、火堆、锻造选择拒绝恢复、商店、建筑师；共用一个自有进程，153.522 秒，另启动 10.801 秒、退出 10.413 秒。报告 gui/report.json，测试入口为 [gui_suite_deck_inspection.json](../../tests/game/data/gui_suite_deck_inspection.json)。
- GUI 比较三个观察预设与共用卡牌格式；覆盖普通／升级费用降序、重复与混合失效 ID、空筛选／null、共享提示、返回地图、关闭后直接 end_turn。连续被动观察的原生快照保持相同。锻造页拒绝 inspect_deck 后直接 selection_option 成功，没有额外观察。
- 现有 verify_deck 与更新后的 verify_mcp_deck 在额外隔离测试局均通过；文件、stdio 和关闭后的操作上下文一致，报告 legacy/report.json。
- 额外的矛盾保证回归先确认 action_submitted:true 与 ui_unchanged:true 会被误接受，再补校验并转绿；证据 contradiction-red.log／contradiction-green.log。没有把这个失败归为旧测试过时。
- 固定历史 JSON 未批量重生成；只在回放测试中明确列出已批准的最小关闭与空参数归一化差异。通用预设探针原先没有真实上下文，已补最小上下文及关闭的独立期望。

独立审查由 review_deck_implementation（gpt-6.1-sol/high，只读）完成，没有重要发现或阻塞项。唯一非阻塞建议是为 close_card_view 再加一个被最小投影省略字段的损坏回归，例如 player.hp:false，并断言清除许可；当前完整校验顺序正确，共用响应测试已检查被省略数据的类型，建议保留在本记录，未加入用户 TODO。审查未新增的长列表／特殊卡牌／手柄／人工中断验证仍按下述边界处理。

compileall、全部文档 1962 个相对链接、14 份样本与原始 structuredContent／参数／文件校验值、git diff 检查通过。两个自有测试进程均已退出。所有批准功能完成，保留当前 feature 分支、原始冻结 JSON 与 raw 文件入口的媒体行为；普通 CLI 的最小关闭不捕获棋盘。

## 边界

新 GUI 测试局的永久牌组为 10 张；长列表仍依原生完整网格读取及已有检查，不称为新长列表实测。未穷举所有卡牌、附魔／Affliction、手柄隐藏控件、跨帧人工替换、多人和第三方界面。读取不采缓存，不修改实际卡牌，不展示被更高层页面挡住的牌组。

地图和战斗牌堆的基础观察内容／summary 仍待各工具核验；用户 TODO 的联合事项不整体勾销。close_card_view 的其余错误、遮挡及生命周期未因此自动完成整项工具审阅。
