# inspect_rewards 核验与参数建议

> 当前状态：三项修复、summary、reward_ids、约定验证与一次独立审查完成，22333e2 已合入 main，本项已核销。结果见[实施记录](2026-11-05-reward-inspection-presets-implementation.md)；下方问题及原返回保留审阅基线。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)；源码、问题编号与测试依据单列在[开发核验](2026-11-05-inspect-rewards-development-notes.md)。

## 优先问题

| 问题 | 优先级与实际影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 拒绝原因过于笼统 | 中：非奖励场景、奖励被地图或选牌遮住、尚未就绪，都只显示“操作不可用”，不说明如何恢复 | 区分固定原因，提示先完成当前选择、关闭相应覆盖页或等待入场；保持纯读取的已有许可恢复 | 已修复，约定检查通过 |
| 矛盾的成功响应仍会被接受 | 中：响应声称奖励可见，却同时声称被地图覆盖、隐藏或未就绪，公开层仍显示内容并刷新操作许可 | 核对奖励详情与场景／画面状态一致；矛盾结果返回 transport_error，清除许可 | 已修复，损坏响应回归通过 |
| 旧奖励全流程验证器已过时 | 低：开启截图后仍要求工具总数为 43，当前为 44，会在领取验证开始前失败 | 修正目录断言，继续验证原来的领取／跳过行为 | 已修复，旧 basic 全流程通过 |

真实 GUI 的覆盖读取会被拒绝；第二项针对损坏成功响应的接收校验。三项修复与新参数按已确认的实施计划处理。

## 审阅基线的正常行为

当前参数只有 `preset:default/full`，默认 default。工具不需要先调用 get_observation；它是纯读取，成功结果也可以支持下一步合法操作。

- 结果由 scene、screen 和 rewards 组成；可用操作列表通过 get_observation 获取。
- `rewards` 包含状态、标题、当前全部可滚动奖励行和原生跳过／前进按钮。行和标签按 UI 显示状态读取。
- 每行包含稳定奖励 `id`、`type`、可见 `text`、`enabled`、`linked_group` 和 `hover_tips`。full 保留普通 null；default 按统一规则过滤，空 hover_tips 当前保留为 []。
- 奖励 id 标识当前奖励对象，领取其他行后保持稳定；linked_group 标识互斥组。
- 只读取当前最上层奖励页；嵌套奖励打开后读取子页，返回后再读取父页。全部领完或无掉落时仍可读取空 items 与 Proceed 按钮。
- 悬停说明来自原生奖励行实际使用的提示。卡牌奖励的候选在打开入口后通过 inspect_selection 读取；追回指定卡牌的奖励提供其已公开的预览文字。
- 纯读取保留原有奖励内容、顺序与滚动位置。领取、跳过或处理药水槽位使用相应动作工具。

纯读取遇到明确非法操作时，已有操作许可会保留，错误的 recovery 为 choose_legal_action；首次读取失败则没有许可可保留，仍要求读取。旧状态、超时、损坏响应与异常沿用保守处理。因此这里没有此前动作工具的“拒绝后被迫重新观察”问题。

## 已确认参数

增加以下两个选项，现有 default/full 保持：

| 选项 | 建议语义 |
| --- | --- |
| `preset:summary` | 沿用基础观察的奖励内容，只省略各行 hover_tips，保留标题、条目身份／文本／启用状态、互斥组及跳过／前进按钮；普通 null 沿用 default 规则 |
| `reward_ids` | 按稳定奖励 id 筛选当前页；省略或 null 表示全部，[] 表示不取条目，去重并维持原生列表顺序；未找到的 id 合并报告，其他有效条目仍返回 |

reward_ids 的作用范围为当前最上层奖励页的 items。title 和 proceed 保留整页信息，每行通过已有 id 标识。缺失 ID 按请求顺序合并到 errors，代码为 reward_ids_not_found。

summary 用于查看静态奖励行；需要悬停说明时使用 default/full。get_observation 的 full/default/summary 奖励部分均采用这个静态格式，full 保留普通 null，default/summary 过滤普通 null。

## 修复后样本

[11 份完整新返回](2026-11-05-reward-presets-examples/README.md)展示 full/summary、reward_ids、基础观察对照和具体拒绝。

## 审阅基线 JSON 与范围

[9 份典型完整返回](2026-11-05-inspect-rewards-examples/README.md)覆盖普通混合奖励、互斥组、空列表、嵌套奖励、追回／逃脱和错误，其中八份 full、一份 default。不同奖励内容不要求各自提供重复结构的样本。

卡牌移除奖励及未知第三方奖励仅核对共同读取与类型分支，未单独实测；多人和所有遗物组合不作穷举。当前阶段范围为[实施计划](../superpowers/plans/2026-11-05-reward-inspection-presets.md)列出的契约与验证。
