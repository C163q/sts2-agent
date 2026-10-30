# 升级牌名称一致性核对

## 基线与根因

核对日期为 2026-10-30。游戏为 Linux `v0.107.1`、分支 `v0.107.1`、提交 `59260271`，RitsuLib `0.6.10`；相对游戏目录的 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。代码基线为 `7f06f6e`、Mod `0.19.0`、MCP server `0.15.0`。

`CardModel.TitleLocString` 只返回基础本地化条目；`CardModel.Title` 才在升级后追加 `+` 或多次升级的 `+N`。目标查询和两处事件记录原先读取前者，丢失后缀；基础观察则已经从可见标题保留后缀。程序集证据为 `.tmp/decompiled/MegaCrit.Sts2.Core.Models.CardModel.decompiled.cs` 的 `TitleLocString/Title`，以及同目录 `MegaCrit.Sts2.Core.Nodes.Cards.NCard.decompiled.cs` 的 `FindOnTable/UpdateTitleLabel`。反编译文件不纳入 Git。

真实中文 MCP 复现中，观察及手牌详情返回 `True Grit+`，`inspect_targets` 对同一 ID 返回 `True Grit`；证据 `.tmp/2026-10-30-card-names/red.json`、`red/hand.png`。此时没有出牌，因此这次失败本身只证明命名不一致。

## 实现

Mod `0.20.0` 将既有可见名称规则提取到 `EnglishText.CardName(NCard?)`，由基础观察、目标查询和事件共同调用；手牌和选牌沿用基础观察的卡牌读取。后缀只取实际可见标题，不从隐藏升级级数补齐；未知、锁定及不可读标题保持原有边界。MCP 版本、工具、字段和参数不变。

事件记录继续只缓存已经实际看见的名称。完整流程测试另发现：选牌后原牌移出普通手牌容器，确认动作创建新记录时未记住确认区中的牌，随后消耗事件名称变为 `null`。`green-zhs.json` 保留此失败；修复为开始记录时缓存当前 UI 内实际可见且已识别的牌，包括确认区，不读取隐藏牌堆。

## 验证

新增 `scripts/verify_card_names.py` 使用隔离图形实例 `--play-scenario card_names`。场景同时含 `True Grit+`、升级和普通的打击及防御，检查观察、详情、目标查询一致性，再实际出牌、选牌、确认、攻击和结束回合，检查出牌、来源、消耗和弃牌事件。已有武装图形检查也增加真实升级后再次查询名称的断言。

验证命令：准备隔离运行目录后，运行 `python3 scripts/run_roundtrip.py --windowed --play-scenario card_names`，另开终端执行 `.tmp/mcp-venv/bin/python scripts/verify_card_names.py --report .tmp/name-check/run.json`。检查会操作测试游戏，必须使用全新的隔离实例与报告目录，不能连接正式对局。

## 验证结果与交付边界

证据目录为 `.tmp/2026-10-30-card-names/`。

| 检查 | 结果与证据 |
| --- | --- |
| 最终中文图形 MCP 名称流程 | `final-zhs.json`、两张 PNG；五张升级与普通牌的观察、详情、目标查询一致，坚毅+出牌、确认后消耗、打击+及其伤害来源、回合弃牌名称均符合预期；打击+实际造成 9 点伤害 |
| 武装实际升级后查询 | `upgrade-zhs.json`、五张 PNG；零费武装完整预览、改选、取消、确认及视图切换通过，确认后按原 ID 查询得到完整升级名称 |
| 完整 Python 测试 | 162 项通过，`python-final.log` |
| C# 检查与构建 | 15 项通过，`csharp.log`；构建 0 警告、0 错误，`build.log` |
| 原生回归 | 基本出牌、发现、技能药水、Hellraiser 自动出牌、保留手牌共 5 项通过，`regression/results.json` |
| 图形观察与往返 | 可见性检查及原生读回、过期令牌、重复请求回归通过，`observation-final.checks.json`、`observation-final.log` |
| 独立审阅 | 无 Critical / Important；对已知 ID 的事件名称可能为 `null` 的测试漏检建议已采纳，强化断言后新实例通过；`review.md` |

完整观察回归初次失败在旧 `verify_observation.py` 的 `schema_version == 3` 断言，当前 `GameAdapter` 和指南均为版本 `5`。游戏内可见性检查当时已经成功；修正单行旧断言后用全新实例重跑，整条验证通过。`final-verification.log` 与 `observation.json` 保留原失败，不能将其当作成功记录。

观察指南还遗留“动作最多等待 2 秒”的早期描述，与现有统一动作等待实现冲突，已改为引用 `end-turn.md` 中的实际契约，未改变等待逻辑。详细差异报告为 `.tmp/2026-10-30-card-names-report.md`。

已备份并安装 Mod `0.20.0`，构建、隔离实例和正式安装文件哈希一致；MCP 仍为 `0.15.0`，不增加工具、参数、字段或提示词。正式现场、用户配置、截图和创意工坊 RitsuLib 未修改。运行中的旧 Mod 不会热更新，须重启游戏并重新观察；正式进程重启后的加载、其他版本、第三方自定义标题及所有卡牌组合未验证。
