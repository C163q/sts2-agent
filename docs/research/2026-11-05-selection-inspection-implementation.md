# 选牌查看修复与验证

> 当前状态：实施中，共 3 项，已完成 2 项；三个修复已通过五类针对验证，Python 全量与 C# 检查通过，正在执行完整游戏回归。独立审查、文档收尾及合入尚未完成，无阻塞。

范围依据：[已确认的三项问题](2026-11-05-inspect-selection-review.md#优先处理的问题)及[实施计划](../superpowers/plans/2026-11-05-selection-inspection-fixes.md)。基线为 `6b92200`，不扩展其余选择动作的完整审阅，不增加参数或预设，不修改公共空值过滤。

## 修复内容

| 问题 | 实现 |
| --- | --- |
| 明确未交互的拒绝清除许可 | 将查看分支从选择动作处理拆为 InspectSelection；前置拒绝使用现有 ui_unchanged 保证并注册 unchanged_view_rejections，显式升级参数也能保留已有许可。无初始许可不创建许可，切换后失败或未知结果仍要求读取 |
| 具体原因丢失 | SelectionInspection.UnavailableReason 集中诊断无选择、非单人、未支持、查看战场及覆盖状态；只对固定、明确的拒绝公开 public_message，异常诊断仍不公开 |
| 可见文字漏读 | SelectionText.Prompt 集中读取选择提示；补充卡包原生 Banner.label 对应的 CHOOSE_A_PACK 和结果页 BottomLabel 对应的 _infoText。只在文字显示时返回英文，不切换 UI 语言或补隐藏内容，基础观察和详情共用 |

`prompt` 的规则保持：非空文字在 full/default/summary 均保留；null 只在 full 保留。卡牌内容、筛选、比较身份及随机变牌规则不变。

## 测试与基线证据

任务目录 `.tmp/2026-11-05-selection-inspection-fixes/` 保存完整日志，未覆盖旧审阅证据。

- Python 新回归先失败：明确未交互、带 view_upgrades 的拒绝返回 get_observation，预期 choose_legal_action；修复后与无初始许可、交互后失败、stale_state、game_error 和 prompt 规则检查一起通过。
- 原生旧 DLL 的三次 RED：gui-rejection-red 验证具体原因丢失；gui-bundle-red 和 gui-view-cards-red 分别验证可见文字仍为 null。均保存失败原文，未重试动作掩盖失败。
- build-green.log：编译通过，0 警告、0 错误。
- python-final.log：676 项全量 Python 检查通过；csharp.log：124 项 C# 检查通过。
- GUI：gui-focused 验证五项针对场景；gui-regression-0/1 验证现有选择、升级开关与完整候选组合，仍在运行。

测试基线为 Linux 游戏 v0.107.1、release build 59260271，RitsuLib 0.6.10；程序集 SHA、重新反编译的 API 位置沿用[本项审阅核验](2026-11-05-inspect-selection-development-notes.md#核对基线)。当前版本唯一来源为 [README](../../README.md#当前版本与前提)。正式 Mod 未安装。

## 集成与限制

复用当前干净工作区的临时分支及已准备隔离运行时，不另建 worktree；测试局的 IPC、存档与日志独立，运行期间不更新共享运行时。用户已明确批准三项修复，实施计划仅补充落实细节，没有额外审批等待。

未实测控制器模式、第三方自定义选择页、真实切换过程中跨局或异常竞争；Python 检查覆盖交互后失败、过期和未知结果的许可处理，但不能代替这些原生竞争场景的实测。
