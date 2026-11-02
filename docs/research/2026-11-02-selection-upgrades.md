# 选牌界面的升级预览

当前状态：已完成。共 3 项，已完成 3 项；实现、文档、Python 409 项、C# 60 项、构建及最终 7 个隔离图形场景均通过，独立审阅完成。无剩余实施项和阻塞，未安装正式 Mod。

## 要求与计划

1. 回归测试覆盖 `view_upgrades` 参数、原生状态转写、稳定卡牌 ID、摘要／筛选兼容，以及不支持时的部分成功错误。
2. `inspect_selection` 增加可选布尔参数 `view_upgrades`：省略保留当前状态，显式指定则点击原生复选框并等待画面稳定，不实际升级卡牌。返回 `selection.can_view_upgrades` 和 `selection.view_upgrades`；隐藏时后者为 `null`。候选内容遵循实际显示的普通／升级牌面，ID 始终关联原牌。不支持切换时保留当前数据并附 `errors:[{"code":"upgrade_view_unavailable"}]`，MCP `isError:false`；与无效卡牌 ID 错误合并。选牌被遮挡、消失或发生竞争时保持顶层错误，不伪装成部分成功。
3. 完整 Python、C#、构建及隔离 GUI 验证；同步接口说明、版本和 schema，独立审阅后提交，不安装正式 Mod。

参数与已有 `inspect_deck.view_upgrades` 一致。原生开关需要可见、启用、没有确认预览覆盖；切换后保留界面状态。`full`／`summary`、`card_ids` 只控制返回内容；打开升级预览不自动选择或确认候选，不改变实际牌组、随机状态或选择数量。

## 原生依据

核对基线：`268da71`，Mod／MCP `0.45.0`、schema `26`；Linux 游戏 `v0.107.1`、RitsuLib `0.6.10`。目标为安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。本次反编译证据位于忽略目录 `.tmp/2026-11-02-selection-upgrades/source/`。

| 当前接口类型 | 原生类型与依据 | 升级预览入口 |
| --- | --- | --- |
| `deck_upgrade` | `NDeckUpgradeSelectScreen._Ready/ToggleShowUpgrades` | `%Upgrades` 复选框，覆盖火堆及事件等牌组升级选择 |
| `deck_transform` | `NDeckTransformSelectScreen._Ready/ToggleShowUpgrades` | 同一复选框，查看待变牌候选的升级牌面，不揭晓随机变牌结果 |
| `view_cards` | `NSimpleCardsViewScreen.ConnectSignals` 调用 `NCardsViewScreen.ConnectSignals/ToggleShowUpgrades` | 结果页继承的 `%Upgrades`，例如潘多拉魔盒结果 |
| 其他已接通选择 | 普通牌组移除、附魔、小型候选、奖励、网格、战斗牌堆、手牌、卡牌包 | 未发现当前页面的升级复选框；手牌升级的选中前后比较独立保留 |

上述原生控件在控制器模式隐藏；不能以后台存在控件就认定可操作。右键打开的独立卡牌详情不在本参数范围。

`NGridCardHolder.SetIsPreviewingUpgrade` 将 `CardNode.Model` 切换为升级克隆，但 `CardModel` 仍指向原牌。基本观察必须用原牌 ID 配合实际可见牌面；完整浏览列表通过隔离克隆按 `NCardGrid.IsShowingUpgrades` 格式化。现有 `SelectionInspection` 固定读取未升级列表、可见克隆 ID 也可能漂移，均需修正。

原选牌文档称 `inspect_selection` 不切换视图：省略新参数时继续成立；显式传入本参数会操作原生升级复选框，工具注解和文档须同步反映 UI 副作用。

## 验证记录

Python RED：5 项新增测试中 3 项失败、1 项报错，原因是旧参数校验拒绝 `view_upgrades`，以及旧投影丢弃升级模式。旧 Mod GUI RED：火堆锻造详情没有 `can_view_upgrades`，新增断言失败；证据 `.tmp/2026-11-02-selection-upgrades/gui-red/`，自有进程已关闭。

首次完整 Python 与图形复现并行运行，`GuiSuiteTests.test_timed_out_verifier_and_its_children_are_stopped` 在超时子进程检查处失败；图形进程关闭后串行重跑完整 409 项通过（32.675 秒）。该测试原本有严格的 2 秒清理观察窗口，本次未修改测试来放宽断言；最终记录串行结果，后续图形与全量 Python 分开执行。

原文档与工具注解称详情绝不切换 UI，本次新参数允许显式操作原生复选框，已同步文档和 `readOnlyHint:false`；默认读取行为不变。Mod／MCP 更新为 `0.46.0`、schema `27`。独立只读审阅未发现功能问题；后续图形测试发现结果页网格使用普通路径 `CardGrid` 而非 `%CardGrid`，已修正 `CardSelection.Grid` 并采用原生结果页的 `PileType.Deck` 显示上下文。最终 7 个场景均通过，包含火堆、事件升级、变形、潘多拉结果页、卡牌奖励、普通移除及多张升级确认。

首次新版火堆验证器误比较响应请求 ID，导致断言失败；修正为只比较原生 `state`，前后永久牌组实际未改变。该失败与结果页路径失败的完整现场保留在 `gui-green/`、`gui-final/`。

多张升级确认新增仅测试夹具：原生选择两张，再在确认后调用游戏升级命令。真实图形检查通过，确认原有比较逻辑已在原牌不可读时返回未知，不需要修改该逻辑。专项图形清单保存为 `tests/game/data/gui_suite_selection_upgrades.json`，共 7 场景；最终证据位于 `.tmp/2026-11-02-selection-upgrades/gui-complete/`，同一自有进程 PID 21342 已关闭；7 局均独立创建并完成清理，总执行时间 147.185 秒，均使用 DLL SHA-256 `bd61aac0d043aedf65e18ceac0fa2957389d38fd18e0c64cc5a377a95617b0b1`。

图形验证覆盖：开关切换及持久状态；full／summary／筛选组合；普通／升级牌面下 ID 集合与基本观察一致；原生非法参数拒绝；只看升级不修改永久牌组；升级候选可直接选中，取消确认后模式保留；确认预览中不强行切换；随机变牌结果仍不提前公开；无控件页面部分成功，并与缺失 ID 错误合并；正常选择及提交仍可继续。火堆、潘多拉升级页和多张确认截图已人工核对。

最终构建 0 警告、0 错误；C# 60 项通过。最终 Python 409 项串行通过（32.094 秒）。未覆盖控制器隐藏／禁用控件、不可升级卡牌混合列表、等待期间人工换页的竞争，以及全部其他游戏场景；没有安装正式 Mod 或操作正式存档。当前 DLL 与 Python 须配套更新，重启游戏并重连 MCP。当前接口入口见[选牌与查看战场](../development/card-selection.md)。
