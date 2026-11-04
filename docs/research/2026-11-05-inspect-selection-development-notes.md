# inspect_selection 开发核验记录

> 当前状态：现状核验完成，进入设计讨论；20 类组合场景、70 项相关 Python 检查通过，采集 100 份完整公共返回。已确认三项问题，玩法实现未修改，工具未核销；暂无阻塞。用户决策说明见[审阅与建议](2026-11-05-inspect-selection-review.md)。

## 已确认问题

| 编号 | 优先级 | 原因、影响与证据 | 处理状态 |
| --- | --- | --- | --- |
| SELECTION-01 | 中；错误恢复 | ToolSpec.changes_view_with_arguments 使带 view_upgrades 的请求成为 view；SelectionRequest 在无选择或选择隐藏时返回普通 FileMailbox.Error，既没有 ui_unchanged 保证，也未登记 unchanged_view_rejections。GameSession 因此不保留已有许可，即使 execution 表明尚未交互。无选择场景已实测普通拒绝后 end_turn 成功、带 false 拒绝后 observation_required | 待实现；应复用明确未交互拒绝协议，只对原生前置检查保证安全的路径标记，不能仅按错误码或当前显示相同推断 |
| SELECTION-02 | 中；错误说明 | GameAdapter.Selection.cs 的显式拒绝没有 publicMessage:true；error_output 只公开 public_message，不公开内部 message。原生具体诊断在 MCP 丢失。把泛化提示直接改成长文不能解决原因丢失 | 待实现；提供明确的前置拒绝原因及安全公开字段，不把任意异常 Message 暴露给调用方 |
| SELECTION-03 | 中；静态信息完整性 | CardSelection.Prompt 除 reward/choose_one 外只读 Prefs.Prompt；bundle 不使用该 prefs，view_cards 使用基类 _infoText，因此两个原生可见文本始终丢失。共用 SelectionInspection 使 get_observation 同样受影响 | 待实现；实际可见时读取对应原生文字，提供英文文本并复用 prompt；覆盖或隐藏时不补全 |

## 核对基线

- 代码 `50e0ad6`；Mod `0.65.0`、MCP `0.67.0`、schema 40。现行兼容基线见 [README](../../README.md#当前版本与前提)。
- Linux 游戏 v0.107.1、release build 59260271；游戏安装目录相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，重新计算 SHA-256：d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 使用既有隔离运行时，未重建或正式安装 Mod；构建目录及隔离运行时 DLL 的 SHA-256 均为 2cc9d5d3ecee7c3dc5298dcf45c6dc2b1d3eb7edf526a5b12ee82239bb9af385。
- RitsuLib 0.6.10；本项未修改其调用或队列规则，不借用内部随机状态。重新反编译的原生证据保存在 .tmp/2026-11-05-inspect-selection-review/source/，不纳入 Git。

## 原生与项目链路

| 范围 | 证据位置与核对结论 |
| --- | --- |
| 选择识别和状态 | Actions/CardSelection.cs：Current 识别十二种已支持类型和 unsupported；Exposed/Status 排除覆盖及过渡；CanViewUpgrades 以实际控件可用性为准 |
| 原生列表 | NCardGrid.SetCards/GetCardVisibility/CurrentlyDisplayedCardHolders；项目 SelectionInspection 对非预览 grid 使用 selection.Cards 完整列表，通过 BrowsedCard.Read 生成牌面，不按虚拟化行或滚动位置截断 |
| 卡包 | NChooseABundleSelectionScreen._Ready 将 CHOOSE_A_PACK 写入 Banner.label；NCardBundle 创建整包卡牌，点击整包才打开预览。项目将包内容与实际整包操作分开 |
| 结果确认 | NSimpleCardsViewScreen.ShowScreen 设置 _infoText；NCardsViewScreen.AfterCapstoneOpened 将它写入 %BottomLabel。项目当前只读取候选和按钮，遗漏该文字 |
| 升级开关 | GameAdapter.Selection.cs 只在实际需要切换时 UiChanged/ForceClick，并等待 SettledObservation 和同一选择检查；不支持开关时返回当前数据及软错误，不执行升级 |
| 普通确认预览 | NDeckCardSelectScreen.PreviewSelection 使用所选原牌创建可悬停预览；项目继续放在 cards，不伪造 before/after |
| 数据校验与格式 | selection_details 校验完整原始选择及比较身份；public_output 只合并主 cards 的共享提示，比较两侧和包内卡牌仍保留独立解释，避免同 ID 的不同牌面混合 |
| 筛选与摘要 | selection_presets 处理 cards/bundles/四类比较；selection_summary 与公共 card_summary 相同；selected_ids、按钮及操作级附魔说明不被筛掉。统一 null_fields 保护比较两侧的 null |
| 上下文与许可 | InspectionSuccess 从同一次快照附 scene/screen/schema；inspection_details 统一公开上下文。无 view_upgrades 的明确读取拒绝保留已有许可；本地参数错误不进入 GameSession |

相对源码路径均以 src/Sts2Agent 或 src/sts2_mcp/output 为根，分派元数据位于 src/sts2_mcp/tool_registry.py。玩法信息的可见性、格式投影、动作许可分层仍适用，无需为本项重新做大范围结构迁移。

## 验证与原始证据

任务目录：.tmp/2026-11-05-inspect-selection-review/。完整 GUI 报告记录测试进程、局身份、用例与 DLL 哈希；公开样例保留返回原文及来源行号。

- python-baseline.log：58 项现有选牌、摘要、升级、卡牌格式及会话检查通过。
- python-suite.log：12 项套件编排检查通过；与前述 58 项合计 70 项。
- gui-baseline/：十二种已支持类型、单张与多张附魔、献祭和重掷，共十四类组合通过，338 次 MCP 调用，370.500 秒。
- gui-errors/：无选择的许可差异和原因丢失已复现；第二例错误使用战斗外删牌夹具，打开牌组被正确拒绝。该失败属于审阅脚本设定错误，原始日志保留，不计为工具缺陷。
- gui-errors-corrected/：更正为 combat_pile 的原生眼睛与牌组覆盖；无选择、覆盖及 hand_upgrade 三类通过，26 次 MCP 调用，75.737 秒。通过表示已复现记录的旧行为，不表示 SELECTION-01/02 已修复。
- gui-boundaries/：四十张候选及附魔、升级模式、隐去身份和多张升级比较，共三类通过，51 次 MCP 调用，62.912 秒。

合计 20 类组合场景、415 次 MCP 调用；每套使用独立进程与存档，复用同一只读隔离运行时。提取 [100 份返回](2026-11-05-inspect-selection-examples/README.md)，其中 full 53 份、summary 47 份；普通 default 的空值规则由相关 Python 检查验证，未另外采集该预设的游戏样本。

四个自有游戏进程（包含失败尝试）均已确认退出；100 份样例逐份与原报告核对，256 个相对文档链接及 git diff --check 通过。原始核对结果保存在任务目录 verification.json、processes.json；未重建 DLL、未修改玩法代码或版本。

卡包和结果确认页的截图分别位于 gui-baseline/bundle/verify/screenshots/candidates.png、gui-baseline/view_cards/verify/screenshots/candidates.png；前者实际显示“选择一组”，后者底部显示“经由潘多拉魔盒变化的卡牌。”。对应 JSON 的 prompt 均为 null。截图使用中文 UI，工具按现有约定返回英文；不把截图中的汉化文字直接写成英文 API 输出。

## 持续维护文档差异

card-selection.md 原先笼统写“失败后须重新观察”，但本地参数错误和普通读取拒绝实际保留已有许可。已按当前行为限定其适用范围，并单列带升级参数的已知恢复缺陷；这只是纠正文档，不表示错误路径已修复。卡包及结果页文字遗漏也已补充为已知缺口，避免把 prompt:null 误读为 UI 没有显示说明。

## 验证边界

正常游戏用例使用真实 stdio MCP、独立游戏实例和测试存档；未操作正式游戏、未安装 Mod。普通调用不主动切换眼睛或滚动；显式 view_upgrades 按原生点击改变当前模式。原生按钮点击后的动作仅用于推进到要观察的页面，不代表其余三个选择工具已经完成独立审阅。

未实测控制器模式、第三方自定义选择页面及切换升级模式期间的跨局／异常竞争。unsupported 与该类竞争的拒绝须按当前源码边界说明，不据正常页面测试宣称全面覆盖。完整候选的读取不等于可以读取隐藏页面、随机结果或原生未揭示身份。
