# 手牌升级选择核对与验证

## 基线与问题

核对日期为 2026-10-30，游戏为 Linux `v0.107.1`、分支 `v0.107.1`、提交 `59260271`，RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。游戏目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。反编译文件只存放于被忽略的 `.tmp` 目录。

Mod `0.18.0` 的 `CardSelection.Current` 只将 `NPlayerHand.Mode.SimpleSelect` 接为 `hand`，其余手牌模式标记 `unsupported`。武装获得格挡后开启 `UpgradeSelect`，因此停止边界正确识别为等待选择，但候选、确认和眼睛均不可用。旧版文档明确列过手牌升级未接通；此前将武装作为不支持场景验证，未验证其完整游玩，不能据此声称所有选牌已完成。

## 程序集证据

| 类型与成员 | 已核实行为 |
| --- | --- |
| `Models.Cards.Armaments.OnPlay` | 获得格挡后，未升级版调用 `CardSelectCmd.FromHandForUpgrade`，返回原牌后才 `CardCmd.Upgrade`；升级版直接升级所有可升级手牌 |
| `Commands.CardSelectCmd.FromHandForUpgrade` | 先按 `IsUpgradable` 过滤；零张直接返回空，一张直接返回唯一候选，两张以上才开启原生手牌升级选择，并走玩家选择同步 |
| `Nodes.Combat.NPlayerHand.SelectCards`、`UpdateSelectModeCardVisibility` | 使用 `UpgradeSelect` 和选择筛选器，原生眼睛启用，非查看战场时只显示合格手牌 |
| `NPlayerHand.SelectCardInUpgradeMode` | 改选时恢复之前原牌，将新牌移入升级预览，刷新确认按钮；不直接升级 |
| `NPlayerHand.OnSelectModeConfirmButtonPressed` | 完成原生选择任务，由调用者继续执行实际效果 |
| `Nodes.Cards.NUpgradePreview.Reload` | `%Before` 展示原牌，`%After` 展示升级克隆，后者不是可选项；后者使用 `CardPreviewMode.Upgrade` |
| `NUpgradePreview.ReturnCard` | 左侧原牌 holder 的 `Pressed` 调用手牌 `DeselectCard`，清空预览 |

证据位置：`.tmp/2026-10-30-play-card/Armaments.cs`、同目录 `CardSelectCmd.cs`、`.tmp/decompiled/MegaCrit.Sts2.Core.Nodes.Combat.NPlayerHand.decompiled.cs`、`.tmp/2026-10-30-hand-upgrade/NUpgradePreview.cs` 与 `NPreviewCardHolder.cs`。以上均来自目标程序集，不将一代接口用于二代。

## 实现范围

Mod `0.19.0`、MCP server `0.15.0` 增加选择类型 `hand_upgrade`，不增加工具或参数。候选读取原生可见手牌 holder 和预览左侧原牌，原生 `Pressed` 支持初选、取消和替换，启用的确认按钮负责提交。已经展开的升级预览用 `upgrade_preview.before/after` 表示，两侧使用同一个原手牌 ID；右侧克隆不会作为额外候选。只读取原生已经显示的预览，不预生成隐藏升级结果。眼睛与遮挡规则沿用既有流程，隐藏时预览为 `null`。

工具的长期使用语义见[选牌指南](../development/card-selection.md)。本次不接通专门牌组升级、变化、附魔或卡牌包选择，它们仍作为 `unsupported` 边界返回。第三方选择、多人联机、其他版本和全卡牌机制组合没有覆盖。

## 验证证据

证据目录为 `.tmp/2026-10-30-hand-upgrade/`。旧版真实图形 MCP 失败复现为 `red.json` 与 `red/initial.png`；新测试在 `status == visible` 断言处失败，实际返回 `unsupported`。新字段过滤测试在旧 Python 投影层被拒绝，随后修复。

英语图形实例通过 `green2.json` 和五张 PNG 验证：未选时不提供启用确认、候选及正文读取、初选预览、确认前未升级、查看战场与禁止输入、牌组覆盖页隐藏、返回后保留选择、替换、再次点击取消、确认后原 ID 对应升级牌。最初一次测试错误地假设未选时必定显示禁用确认按钮；截图表明原生完全隐藏此按钮，测试已修正为“不存在启用确认项”。

中文零费图形实例通过 `final-zhs-free.json` 与五张 PNG 重复完整流程。已核对中文截图“防御 5 → 防御+ 8”与英语 JSON 一致；费用为 0，使用后能量仍为 20。格式化的实际公开响应保存在 `llm-preview.json`。

| 验证 | 结果与证据 |
| --- | --- |
| 完整 Python 测试 | 162 项通过，`python-final.log` |
| C# 检查 | 15 项通过，`csharp.log` |
| Mod 构建 | 0 警告、0 错误，`build.log` |
| 武装边界 | 普通、零费、过滤已升级牌、唯一候选、无候选、武装+ 共 6 项通过 |
| 出牌回归 | 打击与防御、发现、冲锋 3 张候选、微光通过 |
| 药水与回合 | 技能药水、赌徒药水、暴政通过 |
| 选择回归 | 选择悖论、双选网格、普通牌组、保留一张手牌、连续选择、未支持页面边界、战斗牌堆、滚动并发输入通过 |
| 原生回归总计 | 21 项全部通过，`regression/results.json`、`regression.log` 及各项原始响应与游戏日志 |
| 独立代码审阅 | 空上下文只读审阅，无 Critical、Important 或 Minor 问题，`review.md`；审阅者未重跑测试 |

用户中断时前 12 项回归已通过。恢复后确认测试进程已停止，跳过成功项，使用新的隔离实例继续剩余 9 项，不对未知状态的旧实例重发动作。部分 headless 游戏日志包含 Godot dummy 渲染器的纹理、shader 或 RID 错误；这些实例的功能断言仍通过，两组真实图形流程另行验证。不能把本次结果表述为全部日志无诊断。

已备份并安装 Mod `0.19.0`；构建产物、隔离实例与正式安装文件哈希一致，记录见 `install.json`。MCP 为 `0.15.0`；正式对局、用户配置、截图和创意工坊 RitsuLib 未修改。运行中游戏不会热更新 DLL，须完整重启游戏及重连 MCP；正式进程重启后的加载与原现场恢复没有验证。

构建、单元测试不能代替图形行为验证；本次没有完成一整场 LLM 自动战斗，也未声称覆盖所有选牌页面。
