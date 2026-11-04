# 选牌查看修复实施计划

> 当前状态：已完成，共 3 项，完成 3 项；28 组 GUI 组合、676 项 Python、124 项 C# 及一次独立审查通过，三项问题修复，文档与样例收尾完成。暂无阻塞。
> 执行方式：使用 superpowers:executing-plans 在当前会话完成，最后进行一次独立审查。三项范围已经用户确认，无需重复请求实施许可。

目标：修复[审阅](../../research/2026-11-05-inspect-selection-review.md)中的 SELECTION-01–03，保持现有参数、卡牌格式与空值规则。

架构：选牌查看的前置诊断与实际读取分开；仅保证未交互的拒绝使用现有 ui_unchanged 协议。提示文字由共用选择读取提供，基础观察和详情保持一致。

技术：C#／Godot、Python MCP、现有隔离 GUI 套件。

## 约束与重点

- `prompt` 有文字时所有预设保留，null 时 full 保留、default/summary 省略；不改变公共过滤。
- 无初始许可时拒绝不能创建许可；点击后失败、状态过期及未知结果仍清除许可。
- 不公开任意异常文本，不读取隐藏页面，不推测随机变牌结果。
- 卡包横幅和结果说明仅在实际显示时读取；支持中文 UI 下的英文输出，不切换游戏语言。
- 复用当前干净工作区的临时分支及隔离运行时；完成后自动合入 main，不安装正式 Mod。

## 任务 1：明确拒绝与安全恢复

文件：Adapter/GameAdapter.Selection.cs、Observation/SelectionInspection.cs、tool_registry.py、test_selection_upgrades.py、verify_selection_review.py。

接口：SelectionInspection.UnavailableReason(CardSelection?) 返回明确前置拒绝原因；供查看分支调用，其他选择动作的完整审阅不扩大到本项。

- [x] 新增 Python 对带升级参数的明确未交互拒绝、无许可、交互后失败和状态过期的测试；GUI 修改旧故障断言为正确恢复，先运行观察失败。
- [x] 共用前置诊断，显式拒绝提供 public_message、ui_unchanged；注册 unchanged_view_rejections。点击后的失败仅公开固定说明，不给未交互保证。
- [x] 跑针对测试及 GUI 无选择／覆盖／手牌升级，确认原因可读、可直接继续、未知不放行。
- [x] 提交独立修复。

## 任务 2：共用可见提示文字

文件：Actions/CardSelection.cs、Observation/SelectionText.cs、Testing/Checks/SelectionPromptChecks.cs、Testing/GameAdapter.Testing.cs、verify_selection_review.py 及套件注册／清单。

接口：SelectionText.Prompt(CardSelection) 保留原有其他类型规则，新增 bundle Banner 和 view_cards BottomLabel 的可见文字读取；CardSelection.Prompt 委托给该入口。

- [x] GUI 新增卡包／结果页：full/default/summary 的观察和详情均有相同非空 prompt；隐藏对应标签时 prompt 为 null，恢复后不改变 UI；先在旧 DLL 上复现文字缺失。
- [x] 实现实际可见的英文文字读取，使用当前程序集核实的 Banner.label、BottomLabel 及 _infoText，不硬编码事件结果。
- [x] 跑卡包、结果页及原有全部选择／升级回归。
- [x] 同步 Mod/MCP 版本并提交。

## 任务 3：验证、文档与集成

- [x] 全部 Python、C# 检查及最终 GUI 组合通过，导出修复后的完整样例；旧审阅样例保留原状。
- [x] 独立审查完整变更；重要发现一次修复并验证，不追加重复审查。
- [x] 持续维护文档写最终行为，审阅记录三项状态及未验证边界，核销 inspect_selection；验证链接、样例及进程清理。
- [x] 英文 Conventional Commits 提交并合入 main，删除已合并临时分支；不推送或正式安装。
