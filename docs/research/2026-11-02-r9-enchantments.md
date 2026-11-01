# r9 附魔显示与安装版本核查

当前状态：已完成。已确认版本差异，补充 Spiral 图形回归，并将正式安装更新至经过本次验证的 Mod `0.43.0`。未修改生产读取逻辑；无剩余实施项。

## 差异与原因

2026-11-02 的 r9 报告中，第六张 `Defend+` 的蓝色 Spiral 图标可见，`inspect_hand(full)` 包含 `Replay 1.` 与 Spiral 提示，但 `get_observation` 和 `inspect_hand(summary)` 缺少结构化 `enchantment`。这与[手牌摘要契约](../development/hand-inspection.md#参数与返回范围)不一致；“summary需求延续”不在本次范围内。

只读核对正式安装发现 Mod 仍为 `0.34.4`，DLL SHA-256 为 `c0b0cd9cc94c2940a97bc5241c3e422cdcc322aea1060d0f5fa348b33ca79205`。正式 IPC 留存响应 `eb64d1967ae041ab8529e932e6e89bda.json` 的时间为本地 2026-11-02 02:48:01，schema 为 `16`，手牌 ID、名称与报告完全对应。反编译该安装 DLL 的 `CombatObservation`，确认没有附魔字段读取逻辑。

附魔基础字段已经在后续实现中加入共用 `CombatObservation.Card`，供基础观察和手牌详情使用，Python 摘要保留这一对象。旧 DLL 本来就能通过原生悬停提示提供 full 的附魔效果，full 可读并不能证明游戏端已经加载结构化字段。原因是新 Python 搭配旧游戏端，而非当前摘要投影删除字段。公开响应继续兼容旧版可选字段，不把缺字段解释为确定没有附魔。

## 验证范围

基线为提交 `d5f382d`、Mod `0.43.0`、MCP `0.41.0`、schema `25`；游戏 Linux `v0.107.1`（release `59260271`），RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。游戏程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。

核对原生 `Spiral.CanEnchant` 与 `EnchantPlayCount` 后，扩展已有 `play:enchantments` 隔离夹具：保留 Sharp 3、置灰 Swift 2、无计数 Clone 与普通牌，增加第六张升级后的 `Defend+` 并经 `CardCmd.Enchant<Spiral>` 附魔。回归同时断言基础观察、full、summary 均有 `{"name":"Spiral","dimmed":false}`，不补隐藏计数；只有 full 提供 `Replay 1.` 和 Spiral 悬停效果。

保留原有隐藏、离屏、未知身份、显示计数与模型不同、置灰材质和读取不改变 UI 的检查，另回归普通手牌与武装选牌摘要。隔离实例使用独立进程、IPC 和存档，不连接正式游戏执行测试动作。

本地证据位于 `.tmp/2026-11-02-r9-enchantments/`：`old-installation.json`、`source/installed-CombatObservation.cs`、`source/Spiral.cs`、构建与回归日志及图形套件报告。反编译产物和原始游戏响应不纳入 Git。

## 结果与安装

- 构建零警告、零错误；完整 Python 回归 377 项通过，纯 C# 检查 60 项通过。
- 同一个独立图形进程完成附魔手牌、普通手牌和武装选牌摘要三局回归；18 项附魔嵌入检查全部通过。第六张 `Defend+` 在基础观察、full、summary 均有 Spiral 身份，不显示不存在的计数，full 保留原生 `Gain 8 Block.\nReplay 1.` 及悬停提示。读前后快照、ID 筛选、合并错误及直接行动检查通过。
- 已查看实际截图，确认蓝色 Spiral 图标与输出相符。完整证据见 `gui/report.json`、`gui/card_enchantments/verify/evidence.json` 和同目录 `screenshots/enchantments-hand.png`；摘要样本另存 `summary-example.json`。
- 已确认正式游戏及自有测试进程退出，备份原正式 DLL/清单后，仅替换游戏安装目录的这两个文件。正式安装版本为 `0.43.0`，DLL SHA-256 为 `74ea6bf672678f82f8de7863a48a66b947423630b732cd561300f30bbb8dcc4c`，与本次构建和图形测试记录完全一致。安装记录为 `installation.json`，另存 `.tmp/live-install/0.43.0-installation.json`；旧文件备份位于 `.tmp/mod-backups/before-0.43.0-r9-425242b5/`。

本次未启动正式存档验证 Boss 现场，也未执行整份图形套件或完整通关。重新启动正式游戏后才会加载新 DLL；Python 代码未改，不要求为本次安装重连 MCP。
