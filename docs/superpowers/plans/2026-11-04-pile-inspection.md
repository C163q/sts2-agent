# 战斗牌堆查看实施计划

> 当前状态：实现、验证及独立审查完成，共 4 项，已完成 4 项；批准范围无遗留。证据及未覆盖边界见[实施记录](../../research/2026-11-04-pile-inspection-implementation.md)。暂无阻塞。

## 定稿与约束

依据[牌堆审阅](../../research/2026-11-04-inspect-pile-review.md)及已确认要求实施。基线 `f076c0c`；游戏 API 依据该审阅的目标程序集与反编译证据，不新增依赖。

- 修复 PILE-01–05：安全具体原因；仅原生显式保证未交互的拒绝保留已有许可；补基础观察；更新旧关闭断言；提示词用 status 表达空／不可用，避免错误承诺默认 null。
- inspect_pile 保留 pile、default/full/summary。新增 card_ids，严格 `pile:N`；省略／null 全部、[] 为空、去重并按原生顺序返回；缺失 ID 合并为 `errors:[{code:"cards_not_in_pile",card_ids:[...]}]`，有效项仍成功，解释同步裁剪。不提供升级或排序参数。
- 筛选只影响输出，原生请求仅含 pile；先完整校验，再筛选／摘要。空堆为已知空集合；unavailable 不判断成员，不制造缺失 ID 错误。所有非法参数在 IPC 前拒绝并保留已有许可。
- 基础观察在当前牌堆页暴露且就绪时返回 pile、cards、message；卡牌 full/default/summary 分别采用 face_full／face_default／共用 summary，不含正文或悬停解释。与专门工具共用身份表和完整网格，绝不输出真实抽取顺序、改动 UI 或继承前次输出筛选。关闭／覆盖时不附缓存；actions_only/top_bar 不增加牌堆内容。
- 页面底部固定 message 在两入口的 full/default 保留、summary 省略；inspect_pile 的 empty／unavailable 对应气泡／原因在 summary 保留。
- 保留已有状态门控与正常原生点击流程；已有交互、未知结果、过期及格式异常不能恢复许可。所有游戏读写遵循游戏线程，异步等待不阻塞游戏线程。
- 当前 feature 分支原地实施，范围限于本任务；相互依赖的原生／Python 协议统一验证后提交。不安装正式 Mod、不推送或合并。证据置于 `.tmp/2026-11-04-pile-implementation/`。

## 1. 具体拒绝与未交互恢复

**文件**：GameAdapter.AvailableTools.cs、GameAdapter.Views.cs、RequestDispatcher.cs、tool_registry.py；测试 test_pile_inspection.py。

- [x] 用真实 GameTools 和传输替身验证显式 ui_unchanged:true 后可直接 end_turn；无保证／已交互／矛盾证据／无旧许可不能授权；安全原因公开而私有诊断隐藏。先观察失败。
- [x] 共用 `PileUnavailableReason()` 供 available_actions 与操作前置检查调用；交互前置 true，关闭旧页／点击前标记交互；复用现有 GameSession 机制。
- [x] 针对检查转绿，保留未知结果与其他工具门控。

## 2. 筛选及 CLI

**文件**：新增 output/pile_presets.py；pile_details.py、tool_registry.py、roundtrip_client.py；测试 test_pile_inspection.py。

- [x] 覆盖三预设、null／[]／重复／缺失、提示关联、empty／unavailable，固定 malformed 全量响应不能被空筛选掩盖；CLI ID 不转发原生。先观察失败。
- [x] `pile_arguments(arguments)` 归一化筛选；`pile_preset(payload,preset,card_ids=None)` 投影并按状态处理固定帮助；参数与投影迁出响应校验模块。
- [x] 本地非法 ID 不请求、不清旧许可；有效空筛选仍读取、维持页面并更新许可。专项测试转绿。

## 3. 共用牌堆读取与基础观察

**文件**：PileInspection.cs、GameObservation.cs、GameAdapter.cs；pile_details.py、observation_details.py、observation_presets.py、public_output.py；版本及 schema。

- [x] 固定三种观察卡牌格式、固定帮助省略、无悬停正文、隐藏／不完整／错页面的回复拒绝与输入不变。先观察失败。
- [x] `GameObservation.Piles` 持有战斗内身份表，专用查看与快照共用 `PileInspection.Read(...,full)`；full:false 仅取静态牌面。基础观察暴露字段由 `pile_observation(state)` 整组校验，旧 schema 无字段保持兼容。
- [x] 共享装配只在专用牌堆详情中生成 hover_tips；被基础观察省略的数据仍须先完整校验；actions_only／top_bar 不附牌堆内容。
- [x] 更新 Mod／MCP／schema 及 README；专项与全 Python／C# 检查通过后构建隔离运行时。

## 4. 游戏验证及交付

**文件**：verify_mcp_piles.py、verify_pile_inspection.py、gui_suite_pile_inspection.json、suite.py，持续维护指南、审阅、总清单与既有 TODO 状态。

- [x] 真实 GUI 覆盖三个非空牌堆、空堆、隐藏入口、筛选组合、当前观察与 ID 一致、静态读取无副作用、关闭后的动作，以及前置拒绝后合法操作续接。
- [x] 更新并执行旧 MCP／文件专项脚本，运行原生长列表／上下文／生命周期检查；保留失败证据，有限超时并清理自有进程。
- [x] 同步当前文档、核销与用户原有 TODO 范围，保留审阅旧样本；导出新真实 JSON、来源和校验值。
- [x] 独立最终审查，重要问题通过回归处理；最终核验并创建 Conventional Commit。

## 审查重点

1. unavailable 的未知集合不能伪报 ID 不存在；empty 的已知空集合可以报告。
2. 空筛选和 summary 不能掩盖坏卡或原生回复。
3. 基础观察不泄露正文／悬停解释，IDs 与专用查看共享且无 UI 副作用。
4. 交互后的失败不能误标 ui_unchanged；失败不能凭空创造许可。
5. 读取中断、地图／选牌覆盖不泄露缓存或自动重开页面；旧 schema 与文件 CLI 保持可用。
