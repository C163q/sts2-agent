# 先古详情预设与可见信息修复计划

> 当前状态：实施中，共1项，已完成0项；实现与验收已完成，剩余独立审阅、提交合并与清理。无阻塞。

## 目标与范围

依据已确认的[核验与建议](../../research/2026-11-07-inspect-ancient-review.md)，解决四项问题并提供summary、option_ids；[开发依据](../../research/2026-11-07-inspect-ancient-development-notes.md)中的目标版本源码是原生接口依据。保留旧审阅样本。

- full/default保留馈赠正文、对话、名称／称号／页面说明、按钮；summary去掉全部hover_tips及false的lethal_warning，继续使用通用default空值过滤。get_observation三个完整预设使用同一静态先古主体。
- option_ids为非负Int32数组或null；省略/null全部，[]为空，重复去重，保持页面顺序，缺失ID合并errors。保留对话及按钮；悬停不可用note只保留选中ID，summary省略此note。
- 成功详情要求scene:ancient、screen:{status:visible}和可见主体；先完整校验再筛选。悬停不可用来源须引用存在且无悬停解释的选项，不允许重复或伪造来源。
- 原生读取取消视口矩形过滤，仍区分隐藏、透明、真实裁剪和未揭示内容。动作点击仍检查真实在屏幕及可操作条件。可见而无法悬停的选项保留正文与空hover_tips，并给note。
- 只读拒绝具体说明无先古房间、非单人或覆盖页；已有读取许可沿用共用规则，不新增动作恢复策略。
- 原生WillKillPlayer回调给出lethal_warning。schema升级46区分必需警告的新数据；<=45旧数据允许无此字段，不能伪造false。Mod0.78.0、MCP0.80.0，README统一维护基线。
- 不改choose_ancient_option或advance_dialogue的动作拒绝恢复，不正式安装或推送。

## 文件职责

AncientInspection负责页面可读诊断、显示／悬停判断和原生字段读取；GameAdapter.Ancient仅分离只读分支。ancient_details负责完整结构与页面交叉校验；ancient_presets负责参数和输出筛选／摘要；observation_details复用静态主体。共用上下文、notes装配与null过滤继续复用。

Testing中的AncientDisplayFixture只控制隔离页面的显示／禁用／裁剪；AncientFixture新增原生披风安全／致死警告场景。新私有入口有testMode及先古场景门控，纳入双模式禁用检查；不加入公开工具。

## Task 1: 实施并验收先古详情契约

- [x] 编写test_ancient_inspection_presets，覆盖实际GameTools参数、摘要／基础观察、筛选、坏上下文／坏帮助来源撤销许可、拒绝恢复和旧schema；运行RED。
- [x] 编写实际GUI验证器与夹具；仅构建测试夹具，原产品逻辑下运行离屏／致死警告RED，保留原报告。
- [x] 修改原生读取与诊断，再接入Python字段校验、summary和筛选；更新版本、schema及受影响旧检查。
- [x] 运行专项Python GREEN和完整Python、C#检查；构建最终DLL并准备隔离运行时。
- [x] 运行普通／对话／引用／覆盖／嵌套／选择／安全与致死警告／显示边界及旧先古验证回归。记录真实样本与未验证范围。
- [ ] 同步当前指南、工具清单、定稿和实施记录；验证文件链接、样本来源、进程退出及DLL哈希。提交feat: add ancient inspection presets。
- [ ] 一次独立整分支审阅；重要问题做一次测试先行的修复，轻微建议记录。完成后归档并清理本计划工作目录，合入main、删除分支。

### 验证命令与预期

- `timeout 60s .tmp/mcp-venv/bin/python -m unittest tests.python.test_ancient_inspection_presets`：RED因缺少参数／警告／交叉校验失败；产品接入后全部通过。
- `timeout 180s .tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'`：全部通过；异步stdio在沙箱外运行。
- `dotnet build Sts2Agent.sln -m:1 --no-restore`：配合.env的Sts2Dir/RitsuLibDir，90秒超时，零错误；`dotnet run --project tests/csharp/Sts2Agent.Checks --no-build --no-restore`全部通过。
- `scripts/gui_suite.py --suite tests/game/data/gui_suite_ancient_inspection.json --output <新目录>`：自有隔离进程、实际stdio、各场景通过并退出；运行时保持最终构建哈希。
- 交付检查脚本验证真实JSON、原始证据、链接、最终版本和进程退出；无新增代码后不重复构建。

### Review Focus

核查未揭示台词和真实裁剪仍被排除；读取离屏不等于允许离屏点击；按钮禁用／无鼠标与键盘悬停时不泄露帮助；致死警告完全来自原生回调，安全披风false与致死披风true区分。完整上下文／帮助来源验证先于筛选，[]不可遮掩坏响应，旧schema缺失不补造警告；基础观察与summary一致。私有夹具必须门控且可还原，正常对局不暴露测试能力。只有此次独立实现需要审查，后续动作的恢复设计保持原范围。
