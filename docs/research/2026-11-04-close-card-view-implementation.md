# 卡牌浏览关闭的具体原因与许可恢复

> 当前状态：实现、验证及独立审查完成，共 3 项，已完成 3 项；CLOSE-01–02 已修复，close_card_view 已核销。批准范围无遗留，未验证范围见下文。暂无阻塞。

## 范围与基线

依据[关闭审阅定稿](2026-11-04-close-card-view-review.md#输出定稿)及[实施计划](../superpowers/plans/2026-11-04-close-card-view.md)，修复 CLOSE-01–02。代码基线 `62d998a`；Mod `0.60.0`、MCP `0.62.0`，观察 schema 仍为 `40`。现行版本统一见 [README](../../README.md#当前版本与前提)。

目标游戏 Linux `v0.107.1`、release build `59260271`，RitsuLib `0.6.10`。API 及 NCapstoneContainer.CloseInternal／原生返回按钮的依据沿用所属审阅；游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。最终构建与隔离运行时 Mod DLL SHA-256 均为 `edef5d60ef876df356077e3648ee0515872ebd51ce3c05546f1d1d22f7b8206b`。所有 GUI 均使用隔离运行时／存档，未安装正式 Mod。

## 实现

CardView.CloseUnavailableReason 与 CanClose 共用判定，保留原来的受支持页面、遮挡和按钮可见／启用条件，分别说明没有浏览页、当前是选择页、浏览页被覆盖／隐藏／未就绪、返回按钮缺失／隐藏／禁用。原因仅描述当前 UI 可理解的范围，不公开内部异常，也不承诺选择一定能取消。

RequestDispatcher 在 UiChanged／ForceClick 前的明确拒绝返回 public_message 与 ui_unchanged:true。MCP 只给 close_card_view 增加已登记工具标记，复用现有严格证据校验：仅保留已有许可；缺少正向保证、已交互、矛盾证据、未知结果或无旧许可均不能据此授权。共用许可状态机不改。

成功仍先校验完整原生观察再投影 actions_only，default/full 不变，不增加参数或 summary；关闭在首个 await 前同步完成，之后只采样，不继续关闭新页面。文件／MCP 的正常点击、地图和待处理选择语义均保持原样，现行契约见[牌组与关闭指南](../development/deck-inspection.md)。

## 验证记录

新增四项 Python 测试，明确未交互拒绝后直接 end_turn 的用例先因恢复提示和许可未保留而失败，登记后转绿。全套 **627 项通过**（43.002 秒），包括缺省／交互／矛盾保证、无旧许可、坏原生字段先校验、旧关闭／牌组契约、超时及取消。**91 项 C# 检查通过**；最终原生构建无警告／错误，日志在 `.tmp/2026-11-04-close-card-view-implementation/`。

新 GUI 清单先对旧隔离 DLL 运行，在第一个无浏览页的拒绝后观察到通用错误和 get_observation 恢复提示，按预期失败，证据 gui-red 保留。新版 **三局 GUI／30 次真实 MCP 调用全部通过**，报告 gui/report.json；战斗中无页拒绝及成功后的重复关闭拒绝均可直接 end_turn，火堆选牌拒绝后可直接 selection_option，安全原因分别描述无页／选择范围。普通 default/full 成功返回保持最小结构；地图单独打开时拒绝且不关闭，地图叠牌组关闭后保留地图；选择战场页关闭后可直接返回选择。每局正常 reset，所有自有游戏进程已关闭。

[11 份完整实际返回](2026-11-04-close-card-view-implementation-examples/README.md)保存真实参数、来源条目和 SHA-256；每次 GUI 调用均核对 text JSON 与 structuredContent 相等。旧审阅 20 份样本保持原基线，不重写为新错误语义。

独立只读审查未发现 Critical／Important 生产问题，确认关闭合法性与原判定一致、明确未交互只保留旧许可、点击后及未知结果不获得恢复例外。一项 Minor 为 README 仍将观察 schema 写为39，实际已在牌堆改造时变为40；按照文档规范对已发现现行事实偏差的维护要求修正为40，本实现没有再次改观察 schema。审查未运行游戏，也不替代尚未实测的按钮／覆盖／中途再开页等范围；结论由当前源码、专项测试及明确边界共同限定。

同步现行指南、工具清单与原有用户 TODO：工具累计核销9项，错误恢复／准确性提前覆盖10个工具；未新增用户待办，不安装正式Mod、不推送或合并。

尚未新建实际测试条件：返回按钮隐藏／禁用／缺失、卡牌或遗物详情与模态覆盖、关闭后反馈等待中人为再开页面、所有非战斗背景、多人或第三方页。这些边界的控制判定和关闭顺序已核对源码，不以构建通过或普通页面成功代替全场景验证。
