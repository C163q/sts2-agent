# 卡面附魔进入基础观察与手牌摘要

## 基线与结果

核对日期为 2026-11-01，游戏为 Linux `v0.107.1`（release `59260271`），RitsuLib 为 `0.6.10` 的 `0.107.1` 兼容运行时。实现基线 `c6a4f28`，更新后 Mod `0.35.0`、MCP `0.32.0`、原始观察 schema `17`；公开工具名称、数量与参数不变。

原先 `inspect_hand(full)` 的原生共享悬停提示已经包含附魔说明，但基础手牌与 summary 缺少结构化的附魔身份。原生卡面无需悬停就展示附魔图标、部分计数和置灰状态，这些可见信息应进入基础观察。已将它们加入共用 `CombatObservation.Card`，供 `get_observation` 和两种手牌详情预设读取；全文仍只由完整详情提供。

可选字段格式：

```json
{"enchantment":{"name":"Sharp","dimmed":false,"amount":3}}
```

没有可见附魔时省略对象。`amount` 仅在真实计数标签可读时出现，不默认填零或读取内部 Amount；`dimmed` 表达当前原生图标材质的置灰表现，不代表未来效果、永久禁用或卡牌可打出判断。详细契约以[基础手牌字段](../development/observation.md#手牌与身份)为准。

## 原生依据与实现

本次重新核对安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll` 及 `SlayTheSpire2.pck`，本地证据位于 `.tmp/2026-11-01-hand-enchantments/source/`：

- `NCard.UpdateEnchantmentVisuals` 展示 `%Enchantment/Icon`，用 `DisplayAmount` 填入 `%Enchantment/Label`，由 `ShowAmount` 决定标签是否显示。
- `NCard.SetEnchantmentStatus` 在 Disabled 时将图标 `UseParentMaterial` 设为 true 并使用置灰着色；正常时为 false。读取这一实际 UI 标记，不读取模型 Status 推演状态。
- `EnchantmentModel.Title` 及 `localization/eng/enchantments.json` 提供图标身份的英语名称。名称识别要求卡牌身份可读、附魔标签与图标在屏幕中可见，且实际纹理与当前模型图标匹配。
- `CardModel.HoverTips` 原本已经合入 `Enchantment.HoverTips`；保留这条完整说明路径，不将效果复制到基础观察或 summary。
- `Sharp`、`Swift` 显示计数，`Clone` 不显示计数。`CardCmd.Enchant<T>(CardModel, decimal)` 是本次测试夹具使用的原生同步附魔入口。

实现不移动鼠标、切换语言或刷新卡牌预览。可见附魔字段进入原始观察正文及状态指纹，筛选和摘要不会删改用于动作校验的令牌。未知/锁定身份、隐藏/视口外标签、隐藏/缺失图标均不补附魔信息；隐藏计数不由模型值补齐。Python 只声明嵌套字段及类型、剔除未知属性，再让 summary 保留已经校验的对象。

共用读取还会服务通过 `CombatObservation.Card` 输出的原生选牌卡面；这不扩展牌组克隆预览等其他读取路径，也不授权读取不可见的牌堆或未来结果。`get_observation(actions_only)` 仍只输出原有动作上下文，不附手牌。

## 验证

新增 `test_card_enchantments.py` 的 5 项测试，覆盖三种读取中的字段一致性、无计数不补默认值、嵌套效果/私有字段过滤、筛选与合并错误、坏类型拒绝及旧版无附魔字段兼容。先观察旧实现失败，再运行修复后检查。完整 Python 回归为 335 项通过；无游戏 C# 检查为 27 项通过，Mod 构建零警告、零错误。

新增 `play:enchantments` 测试场景，用原生附魔入口准备 Sharp 3、置灰 Swift 2、模型数值 7 但不显示计数的 Clone，以及无附魔的同名打击。测试初始 Swift 状态由夹具配置，不代表实际通过玩法触发了禁用。

17 项嵌入检查全部通过：显示名称与计数、正常/置灰、无附魔、无数字 Clone、隐藏标签/图标/卡牌/计数、视口外标签、空纹理、显示计数 73 与模型数值 3 不同时仍读 73、UI 置灰与模型状态不同时仍读 UI、NotSeen/Locked 身份不泄露，最后确认检查恢复原始卡面。它们是测试专用的短暂 UI 控制，未对正式游戏执行。

真实 stdio MCP 在同一个独立图形进程完成四个场景：附魔手牌、普通手牌、武装选择期间查看战场、打开/关闭查看页后直接行动。验证基础观察、full、summary 的附魔字段一致，基础/摘要没有效果正文；过滤、无效 ID、读前后快照和直接出牌/结束回合保持正常。Sharp 3、置灰 Swift 2 与无数字 Clone 的截图已实际查看。

证据统一在 `.tmp/2026-11-01-hand-enchantments/`：

- `python-red-outside.log`、`red-gui/`：旧实现缺少字段的失败，保留未覆盖。
- `python-red.log`：沙箱中的 asyncio 检查在有限超时后终止；按已知 socket 限制在沙箱外复查，不计为产品测试失败或通过。
- `python-green.log`、`python.log`、`csharp.log`：新检查与完整回归日志。
- `green-gui/report.json`：四项图形场景全通过；附魔步骤的 evidence 包含 17 项检查结果及各次实际响应。
- `green-gui/enchantments/verify/screenshots/enchantments-hand.png`：当前卡面截图。

最终测试 DLL SHA-256 为 `c7b0f7e4590069dfa834ac0bbd80a560be2160cb2578b10be10bbdecda3242d2`，构建目录与隔离运行时一致。本次未替换正式安装的 Mod，未连接正式 IPC、修改正式存档或停止其他 agent 的游戏进程。未执行整份默认图形清单、完整 LLM 通关、其他 Mod 自定义附魔材质或全部附魔生命周期实测。

独立只读审阅核对了原生图标语义、可见性、身份与计数边界、共享读取范围、状态指纹及测试恢复流程，未发现 P0–P3 问题；另独立运行新增 5 项 Python 检查通过。
