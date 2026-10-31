# MCP 动作回执精简验证

## 变更与适用范围

基线为 `98c31e2`，MCP 从 `0.27.0` 升至 `0.28.0`。本次精简 Python 对外输出，并补齐网格选择的有限动画等待，发布 Mod `0.33.0`；观察 schema 保持 `16`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10`。游戏及依赖版本依据见[动作稳定性验证](2026-11-01-action-settling.md)。不替换游戏程序集或 RitsuLib，不操作正式对局。Mod 安装后完整重启游戏，重连 MCP 后应用新输出。

全部 21 个游戏动作在完整验证、取消检查和动作许可处理之后才精简。字段契约以[MCP 动作返回格式](../development/mcp.md#动作返回格式)为准。纯详情、查看页面及 `get_observation` 的完整和 `actions_only` 输出保持现有格式；占卜动作不返回图像，但完整观察和 `inspect_event` 仍返回图像。购买失败和奖励未获得的原生结果保留。

## 字符数对照

以下使用上一版真实图形动作链中同一份完整结果计算新投影，保留全部事件及必要操作提示。统计紧凑 JSON 字符数，不是 token 数，也不代表整局调用总成本。

| 动作样本 | 原格式 | 新格式 | 减少 |
| --- | ---: | ---: | ---: |
| 打出 Defend+ | 2331 | 556 | 76.1% |
| 打出 Strike | 2314 | 704 | 69.6% |
| 使用 Block Potion | 2078 | 511 | 75.4% |
| 丢弃药水 | 2020 | 434 | 78.5% |
| 使用 Skill Potion，进入选择 | 1874 | 469 | 75.0% |
| 结束回合，两次样本 | 3534 / 3711 | 1341 / 1518 | 62.1% / 59.1% |

样本源为 `.tmp/2026-11-01-action-settling/gui-release-chain.json`，新投影和完整示例保存在 `.tmp/2026-11-01-compact-actions/samples.json`。事件不包含所有资源和牌面变化，不能作为完整差量同步协议。

## 验证方法与证据

新增契约测试先在原实现上出现 12 个子用例失败，再实现投影；覆盖六类战斗动作、选择提示、人工输入、超时、购买/领奖回执及占卜媒体。原有过期、并发、取消、坏响应和图像损坏测试继续覆盖完整内部校验。完整 Python/stdio 测试已通过 280 项，日志位于 `.tmp/2026-11-01-compact-actions/`。

图形动作链已经验证首次观察之后连续执行十个原生动作，选择候选及升级预览通过专项查看读取；五次发现连续选择也只使用首次观察，并逐次查看实际候选。外部动作仍导致 `stale_state`，不自动刷新或重试。

图形验证先逐条保存实际 MCP 精简回执，状态断言按需显式调用公开观察或专项详情。生物退场与稳定性检查需要比对原动作响应时，测试辅助函数仅读取已经返回的 IPC 缓存文件并核对其投影，不刷新 MCP 许可；底层完整文件响应不提供给 LLM。

独立审阅确认所有游戏动作共用最终投影，完整验证和许可规则保持原样。审阅发现的商店、升级提示及变牌测试辅助函数的旧格式假设均已同步。未验证其他客户端、长期 LLM 调用行为或完整自动通关；是否减少整局上下文和额外查看次数需要后续实测。

## 网格选择描边等待

图形锻造场景在 Mod `0.32.0` 下连续两次复现：选择升级牌后取消预览，`choice_required/complete=true` 回执和随后明确观察使用同一令牌；下一次取消整个选择被 `stale_state` 拒绝。失败后仅采样诊断，不重试动作，前后完整公开状态的唯一差异是 `selection.cards[0].outline` 从 `cyan` 变为 `none`。

游戏安装目录相对程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` 的目标版本源码链为 `NDeckUpgradeSelectScreen.CancelSelection` → `NCardGrid.UnhighlightCard` → `NCardHighlight.AnimHide`。最后一步将 shader width 淡出至 0，耗时 0.5 秒；原有 0.25 秒静默判定会提前完成。描边观察按真实可见 width 读取，因此不能删除该字段或放宽令牌来掩盖变化。

Mod `0.33.0` 在 `CardSelection.AwaitingInput` 补充等待：受支持的网格选择中，当前可见候选的 `NCardHighlight._curTween` 尚在运行时，不宣告选择边界。只检查有限 Tween，不等待需要玩家作答的父任务，未知选择保持原处理。取消预览之外的网格选择共用此条件。

复现与诊断保存在 `.tmp/2026-11-01-compact-actions/gui-rest.json`、`gui-rest-diagnostic.json` 及 `gui-rest-diagnostic.diagnostic.json`。目标版本反编译证据位于 `.tmp/2026-10-31-rest-site/source/NDeckUpgradeSelectScreen.cs` 和 `.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Cards.NCardGrid.cs`、`MegaCrit.Sts2.Core.Nodes.Cards.NCardHighlight.decompiled.cs`。本次不把这两次失败归因于 JSON 精简，也不通过测试自动刷新或重试隐藏失败。

只补描边等待的候选版本已通过原失败点，随后在返回火堆再选择锻造时暴露另一处过期。诊断唯一差异为 `rest_site.description` 从已显示说明变为 `null`。目标版本 `NRestSiteButton.RefreshTextState` 调用 `NRestSiteRoom.FadeOutOptionDescription`，`_descriptionTween` 将 alpha 淡出至 0，耗时 1 秒；源码位于 `.tmp/2026-10-31-rest-site/source/NRestSiteRoom.cs:585`。最终就绪条件同时等待该有限 Tween。中间候选证据保留为 `build-grid.log`、`build-grid-artifact.json`、`gui-rest-green.json` 和对应 `.diagnostic.json`，不能作为最终通过证据。

最终 DLL 的首次击杀场景在私有 `start_test_combat` 创建阶段预加载角色资源超过文件客户端 40 秒，尚未调用 MCP 出牌，测试实例按 finally 回收；日志为 `gui-final-card.json.log`。将该测试的独立场景创建预算调整为 120 秒后，在全新实例、全新报告中重新验证。公开 MCP 的 40 秒超时和原生动作的 25 秒等待不变，不在旧实例重试未知结果请求。

首次最终结算验证已实际返回主菜单，但测试辅助函数随后无必要地补读了主菜单观察，重新取得令牌，使末尾预期的 `observation_required` 变成原生 `illegal_action`。辅助函数改为在终点 `main_menu` 直接保留回执，避免为不需要详情的终点创建许可；不改生产令牌行为。原报告为 `gui-final-ending.json`，新实例复验单独保存。

## 最终验证与安装

最终 Mod DLL SHA-256 为 `b6fa027414c566a7681c2282e2b35ebddadc8a8d04ce78cf8cba1c205defd42b`，编译 0 警告、0 错误。24 项纯 C# 检查通过；实际 Godot 生命周期由以下图形用例验证，不以编译或纯检查代替。

固定该 DLL 后共 10 类图形回归通过：锻造取消/重选/确认、十步动作链、五次连续发现选牌、击杀后延迟续接、战后奖励、送货员补货、添水限制、占卜、宝箱变牌、死亡结算返回菜单。最终结算共 45 次公开调用，经过教程、时间线、纪元及解锁页，实际到达 `main_menu`；随后动作因没有许可被拒绝。逐条核对其中 66 份真实动作回执，均仅含约定字段。部分场景通过显式观察补查详情；动作链和连续发现用例仅首次观察，后者逐次使用 `inspect_selection`，未靠重复观察获取许可。

证据汇总为 `.tmp/2026-11-01-compact-actions/final-matrix.json` 和 `final-fields.json`；280 项 Python/真实 stdio 单元测试的通过日志为 `python-final.log`，最终源码在合入后另跑完整测试。测试中的原生初始化、早期候选失败和最终成功报告分别保留，不将失败或未经验证的截图计入最终通过结论。

已将同一份 DLL 和 `0.33.0` 清单备份安装，旧 `0.32.0` 文件位于 `.tmp/mod-backups/2026-11-01-023938-compact-actions/`，安装及前后哈希见 `.tmp/2026-11-01-compact-actions/install.json`。正式游戏进程未操作，运行中旧 DLL 仍需完整重启游戏后替换；MCP 同时重连加载 `0.28.0`。RitsuLib 由创意工坊管理，本次未修改。正式重启加载、整局通关和 LLM 的实际补查成本仍待后续实测。
