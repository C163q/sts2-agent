# 奖励详情预设、筛选与诊断实施计划

> 当前状态：已完成，共 1 项已完成 1 项。约定实现、验证和一次独立审查完成，22333e2 已合入 main，临时分支已删除，无阻塞。
>
> 执行方式：executing-plans 当前会话实施，结束时一次独立代码审查；本地合并按项目协作约定执行。

**目标：** 完成奖励详情三项修复，新增 summary 与 reward_ids，并将相关文档改为直接描述行为。

**架构：** 共用奖励查看可用原因，详情与 available_actions 使用同一入口；Python 完整校验后投影摘要和筛选。摘要使用 rewards_details 的基础格式，与 get_observation 奖励部分一致。

**技术：** C#／Godot、Python MCP、unittest、隔离 GUI 套件。

**规格：** [已确认审阅](../../research/2026-11-05-inspect-rewards-review.md)及[开发依据](../../research/2026-11-05-inspect-rewards-development-notes.md)。

## 已确认契约

- inspect_rewards 支持 default/full/summary，默认 default。summary 省略行内 hover_tips，保留奖励状态、标题、行 id/type/text/enabled/linked_group 和 proceed；普通空值沿用 default。
- reward_ids 为当前奖励页的稳定 ID 列表。省略或 null 取全部，[] 取空；去重、保持原生顺序。缺失 ID 按请求顺序合并为 errors:[{code:"reward_ids_not_found",reward_ids:[...]}]，有效行同时返回。
- 筛选作用于 items；标题与 proceed 保留当前整页内容。每行已有 id。
- get_observation 的 full/default/summary 奖励部分均为静态行，无 hover_tips；full 保留普通 null，default/summary 过滤。inspect_rewards.summary 的 rewards 与后两者一致。
- 使用固定公开拒绝原因；纯读取的已有许可恢复保持。矛盾 scene/screen/rewards 成功返回 transport_error，清除许可；先完整校验，再精简或筛选。
- 文档直接说明行为、作用域和可验证限制，删去预防假设误解的重复否定句。

## 审查重点

1. 原生可用性与工具列表一致，地图／牌组／选择覆盖的恢复提示准确。
2. 空列表、嵌套页及互斥组在筛选后仍保留整页标题、按钮与稳定 ID。
3. summary 和空筛选是否仍拒绝损坏的完整响应；合法空值与默认格式兼容。
4. []／null／重复／缺失 ID 的顺序、错误聚合与有效结果是否一致。
5. 旧验证器是否仍经过真实 stdio 领取、跳过和原生后续流程。

### Task 1: 实现奖励详情契约并完成交付

**文件：** 新建 output/reward_presets.py 和 tests/python/test_reward_presets.py；修改 reward_details.py、tool_registry.py、RewardInspection.cs、GameAdapter.Rewards.cs、GameAdapter.AvailableTools.cs、奖励 GUI 核验器与旧 verify_rewards.py；同步相关文档、版本和清单。

**接口：** reward_inspection_arguments 返回 preset/reward_ids，输出专用参数经 native_keys:() 留在 Python。reward_preset 在完整解析后筛选；summary 复用 rewards_details(full=False)。RewardInspection.InspectionUnavailableReason(NRewardsScreen?) 返回固定原因或 null。

- [x] 新增回归并观察 RED：静态摘要与基础观察一致、full/default 兼容、ID 顺序／部分缺失／空筛选、参数前置拒绝与许可、损坏的被过滤行和矛盾画面清除许可。
- [x] 实现 Python 投影和上下文一致性；实现共用原生拒绝入口，更新 available_actions 与读取分支；运行针对性回归观察 GREEN。
- [x] 修正旧验证器的目录发现；扩充七类奖励 GUI 的摘要、ID 筛选及三预设观察对照，增加牌组覆盖和旧流程场景。完整 Python、C# 与构建通过后准备隔离运行时，执行 GUI。
- [x] 保存典型真实 JSON，更新接口文档、审阅规格和 TODO 既有覆盖记录；整理文档表达。校验样本来源／哈希、链接和进程退出。
- [x] 提交、一次独立审查；处理必要发现后合入 main、清理分支。使用 `env PYTHONPATH=src:. .tmp/mcp-venv/bin/python .tmp/2026-11-05-reward-inspection-presets/verify_delivery.py` 核对完整检查与 GUI 证据后记录 task-done，归档本计划 workspace，更新核销。
