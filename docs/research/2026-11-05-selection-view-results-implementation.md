# set_selection_view 修复及精简实施记录

> 当前状态：完成。实现、全部验证和一次独立整分支审查完成，修复提交 `f41fffe` 已合入 main，临时分支已删除，工具已核销。8 组主 GUI、9 组回归、688 项 Python、124 项 C# 和 6 项原生检查通过；已提供[6 份典型新返回](2026-11-05-selection-view-fixed-examples/README.md)。无遗留修复项。依据见[设计定稿](2026-11-05-selection-view-review.md#设计定稿)及[实施计划](../superpowers/plans/2026-11-05-selection-view-results.md)。

## 行为与职责

- VIEW-01：明确未切换的前置拒绝使用 view 专用 `ui_unchanged:true`；Python 登记 `unchanged_view_rejections`。只保留已有许可，首次拒绝不创建许可；缺少保证、已交互、矛盾证据和未知结果不恢复。
- VIEW-02：无选择、不支持、非单人、覆盖、无原生眼睛、眼睛禁用或隐藏分别提供固定的公开原因。切换后选择改变公开重新观察提示，不附未交互保证；任意异常继续只作为私有诊断。
- 成功使用共用 `actions_only_result`，仅保留 scene、screen、available_actions、selection 的 type/status，default/full 参数不变，没有 summary、actions_only 参数或 transition。完整状态仍先解码，成功许可仍取同次底层快照。
- 原生切换拆到 `Adapter/GameAdapter.SelectionView.cs`；前置条件位于 `SelectionAvailability.ViewUnavailableReason`，available_actions 与实际请求共用。两种合法选择视图均允许；只在目标不同时点击眼睛，重复请求不点击。原生等待、状态复核及选择／预览保留继续执行。

## 基线与产物

代码基线 `ad4f829`。游戏 v0.107.1、release build 59260271、RitsuLib 0.6.10；重新核对安装目录相对文件 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。原生依据见[审阅核验](2026-11-05-selection-view-development-notes.md#基线与原生依据)；NPeekButton、原生隐藏／启用和 `_isEnabled` 均按该程序集核对，不新增依赖 API。

实测版本为 Mod 0.67.0、MCP 0.69.0，schema 40；现行版本统一见[README](../../README.md#当前版本与前提)。构建目录与隔离运行时 DLL 均为 `f6ed9c480f73f1675442da0ea26e438c0f8b28cb6be81ea28b3185031508db63`。游戏测试期间没有重建或覆盖运行时；未正式安装或推送。

## 验证证据

目录 `.tmp/2026-11-05-selection-view-results/` 保存失败与通过记录，不覆盖重跑。

| 证据 | 结果及解释 |
| --- | --- |
| 首次 Python 审批 | 自动权限审批超时，命令未启动；按返回允许重试一次成功启动，不计作测试失败 |
| `python-red.log` | 39 项检查有 3 个预期失败及 3 个测试错误；冻结通用状态没有 selection，新增期望错误地强取该字段 |
| `python-red-corrected.log` | 期望按 selection 是否存在调整，39 项检查有 6 个预期失败，分别证明旧恢复和旧完整输出不符合新契约 |
| `gui-red/` | 旧 DLL 在无选择场景返回笼统错误，具体原因断言按预期失败；旧产物 `50de6a77d5866847bf4fcd7c8e72d932f242bbb970b8628f86e378fc60c9ec38` |
| `python-focused.log` | 57 项中 6 处仍按通用视图原样输出的旧预设期望失败；对应进程内和 stdio 两套同一断言，不是运行时恢复失败 |
| `python-focused-corrected.log` | 通用预设期望同步为最小结果后，57 项通过 |
| `build.log` | 构建通过，0 警告、0 错误，5.970 秒 |
| `python-full.log` | 688 项通过，47.934 秒；包括完整解码失败仍清许可、无新增预设、直接续接和交互证据矩阵 |
| `csharp.log` | 124 项通过 |
| `gui/` | 8 组通过，165.301 秒，70 次 MCP；往返、重复目标、首个无许可切换、覆盖页、无眼睛页面、已选项和手牌升级预览保留均核对 |
| `gui-regression/` | 9 组通过，145.439 秒，63 次 MCP；候选点击 2 组、按钮 1 组、选牌详情 2 组、覆盖页关闭 2 组、无基础观察直接续接 1 组及原生入口门控 1 组 |

合计 17 组游戏组合、133 次成功场景 MCP；含旧 DLL 的 RED 尝试为 134 次。三个自有游戏 PID 均已退出，见 processes.json。测试过的 C# 源码和 DLL 后未改；公共工具描述只补充实际返回字段，交付检查另核对描述及参数。

## 原生边界与旧验证器

`check_test_selection_view` 仅在 testMode、suite 与 grid_manual 场景同时满足时执行，未加入 MCP。临时设置原生眼睛 `_isEnabled` 或 Visible 来验证禁用和隐藏的拒绝、可用操作一致性、未交互保证及原生参数诊断，finally 恢复。6 项检查全过，包括恢复后的原始快照；这是人为条件验证，不表示自然游玩出现过同种静止状态。

精简结果不公开候选 ID；主 GUI 仅用另列的原生证据验证保留状态，不用它为公开操作取得新 ID。首次未读候选时显式 inspect_selection；已有公开 ID 或按钮则不插入读取。回归 `verify_observation_sources` 在不调用 get_observation 的条件下成功续接。

需要预览详情的旧 `verify_hand_upgrade.py` 改为切换后显式读取基础观察；该独立旧脚本未单独启动，本项主 GUI 的 hand_upgrade 验证实际相同的往返保留和确认，相关详情回归另已通过。原始文件客户端继续得到完整状态，不要求按 MCP 精简结果修改。

## 典型 JSON 与未测范围

只提取两份成功状态与四份不同诊断，[6 份新样例](2026-11-05-selection-view-fixed-examples/README.md)均逐份匹配公共记录及参数，不补入原生快照或执行标记；旧 [6 份审阅返回](2026-11-05-selection-view-examples/README.md)继续保留并校验原始哈希。

`verify_delivery.py` 核对主／回归清单及实际调用数、688 项 Python／124 项 C# 日志、6 项原生检查、样例来源和请求参数、旧样例哈希、文档链接、当前预设和精简提示，以及相同 DLL 和进程退出证据。`git diff --check` 通过。

## 实现取舍

- 用户已确认修复和精简方案，直接在当前会话执行，复用干净 checkout 的临时分支及准备好的隔离环境；不重复请求相同批准。只有一个实现者写代码，最终审查只读，避免工作区并发写入。
- 完整底层解码保持不变。原生证据仅验证选择和预览保留，不用它替公开操作取得尚未公开的 ID；首次不知道候选时显式读取。否则测试会绕过产品应遵守的信息边界。

## 独立审查与收尾

审查范围 `ad4f829..f41fffe`，一次只读审查结论可以合入 main，Critical／Important／Minor 均为 0，无新增重构建议。五项重点均符合定稿，无修复轮次、延期 minor 或复审。

审查未判断的范围均已裁定：控制器／第三方眼睛修改保留未测兼容边界；真实并发替换、未支持／非单人表现不从源码核对升级为实测；旧独立手牌升级脚本不重复启动，适配部分已审查且主场景和回归覆盖其本项变化；正式安装及其他工具全面行为仍在本项之外。各项限制与裁定见 `.tmp/2026-11-05-selection-view-results/review-result.md`。

按已有授权本地快进合入 main，没有 pull、push、正式安装或重建；集成后源代码与已测试提交一致，仅运行交付资料检查，不重复全量测试。任务专属工作区逐文件哈希校验后归档到 `.tmp/2026-11-05-selection-view-results/inline-workspace/`，再清理原目录；其他任务目录保持原样。

控制器、第三方修改眼睛、真实并发替换选择、未支持页面与非单人拒绝保留源码核对边界，未计入游戏实测。没有扩大为其他工具的全面审查，也没有正式安装后的加载证据。
