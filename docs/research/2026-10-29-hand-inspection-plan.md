# 当前手牌详情读取实施记录

当前状态：已完成。共 3 项，已完成 3 项；文件读取、英语渲染、独立游戏验证和 Mod 0.4.0 安装均完成。已产出独立战斗 JSON 供审阅；正式游戏仍须重启加载新版，当前正式场景详情尚未采样。MCP 配置保持禁用，未新增 MCP 工具。

## 已确认范围

依据 [观察约定](../observation.md)、[数值说明](../development/observation.md#数值预览说明) 和 [来源核查](2026-10-29-hand-inspection-sources.md)，增加只读文件操作 `inspect_hand`，一次返回全部当前手牌的英语详情，沿用基础观察 ID。先交付 JSON 格式，不增加 MCP 工具，不修改用户的 MCP 配置。

玩法输出仅有 `hand` 与适用的 `notes.card_values`。每张牌复用名称、类型、稀有度、费用等基础字段，新增 `description` 和 `hover_tips: [{title, description}]`。不附带敌人意图、牌堆内容、目标预测或动作令牌。原始响应仍保留 `snapshot_id`；只读调用不要求 `expected_state`，也不自动推进游戏。

英语文本复用游戏 `GetDescriptionForPile`、`HoverTips` 和已配置的 SmartFormat。仅在同步读取调用栈内启用线程局部的英语格式化，退出或异常时恢复；不修改全局语言。关键词和药水提示的工厂缓存在此范围内绕过，防止读取或写入其他语言的缓存。保留资源图标含义，不输出原始 BBCode。读取现有动态预览，不调用 `UpdateVisuals` 或刷新数值。

## 执行步骤

- [x] 输出契约：先运行会失败的手牌输出检查，再允许顶层 `hand`，仅此结果提供卡牌数值说明；保留既有意图说明适用范围。
- [x] 游戏读取：增加 `HandInspection` 与受限的英语渲染，扩展文件分发和 CLI，版本升为 `0.4.0`；隐藏、遮挡或出牌过程中拒绝读取，未知牌不补真实内容。
- [x] 验证交付：构建、Python 回归、独立中文游戏中的实际读取及不变性检查；验证关键词补充解释、缓存与异常恢复、图标、ID 和原观察不附送详情。安装新 Mod，输出真实游戏样本并同步文档，独立审阅后提交。

## 重点核查

- 中文 UI 和已有提示缓存不被英语输出污染；英语作用域异常退出后也必须恢复。
- 卡牌数值取当前预览；不将原始模板或升级后的静态数值当成战斗预览。
- “虚无”提示包含游戏自动追加的“消耗”解释。
- 非战斗、遮挡、无可读手牌和未知卡牌不泄漏隐藏内容。
- 无法热加载旧进程；独立实例样本与正式场景样本须明确区分。

## 已处理问题

- 首次独立加载失败：补丁游戏 `LocManager.SmartFormat` 时，随附的 MonoMod 无法生成该异常处理块的 IL。改为初始化时补丁较小的 `LocString.GetFormattedText`，资源原文通过 `LocTable.GetRawText` 处理；日志保留在 `.tmp/2026-10-29-hand-initializer-failure.log`。
- 随后加载遇到 Linux 原生辅助库缺少 `_Unwind_RaiseException`。`readelf` 核实辅助库没有 `DT_NEEDED`，相关符号未定义，而系统 `libgcc_s.so.1` 已导出该符号。`ctypes` 最小实验先复现失败，再以 `RTLD_NOW | RTLD_GLOBAL` 加载系统库后成功；Mod 增加相同的 Linux 初始化处理，不修改用户启动参数。随附版本为 Harmony `2.4.2.0`、MonoMod.Backports `1.1.2`、MonoMod.ILHelpers `1.1.0`。
- 独立审阅发现详情筛选少了视口条件；已与基础观察共用 `CombatObservation.CardVisible`，保持隐藏、屏外和裁剪行为一致。
- 动态数值检查最初误认为首张攻击牌只有一句伤害描述；实际首张是附带易伤正文的 Bash。检查改为验证其伤害句确实使用临时设置的预览值，并在 `finally` 恢复原值。
- 未扩大验证范围：其他 Mod 的自定义文本及非中文 UI 数字标点尚未验证；游戏部分数字格式器直接使用全局文化设置。

## 验证结果与证据

- C# 构建：SDK `9.0.122`，0 个警告、0 个错误；引用游戏随附程序集，无新增下载包。
- Python：19 项回归通过；新增玩法输出检查先因缺少 `hand` 失败，再通过。旧 Mod 上的只读验证也先确认缺少 `inspect_hand` 路由。
- 最终独立图形实例：中文 UI，Mod 加载及主线程入口正常，最终 `game.log` 无 `[ERROR]`。截图为 `.tmp/roundtrip/observation.png`。
- 真实手牌采样：`.tmp/roundtrip/hand-inspection.json`，包含 Bash、Strike、Defend 共 5 张牌；完整原始前后响应位于 `.tmp/roundtrip/hand-inspection-check.json`。ID 和顺序与基础观察一致，读取前后 `snapshot_id` 一致，基础观察未附送详情。
- 8 项手牌检查通过：关键词组成的完整正文、“虚无”追加“消耗”解释、英语提示、全局语言不变、关键词缓存不变、异常作用域恢复、图标保留、正文使用当前预览数值。证据为 `.tmp/roundtrip/hand-checks.json`。
- 27 项既有显示过滤检查全部通过，证据为 `.tmp/roundtrip/observation-checks.json`；最终独立实例已关闭，没有对正式游戏执行动作。
- 独立只读审阅已完成；屏外卡牌问题已修复，未发现其余阻断。额外核对正文沿用 `NCard` 的现有 `_previewTarget ?? Model.CurrentTarget` 上下文，不重新选择目标。
- 新版 DLL 与清单已安装到配置示例的 Steam Mod 目录，并逐文件校验与验证构建的 SHA-256 相同；安装使用编号备份，保留旧文件，不截断旧进程已加载的 DLL。用户须重启 Steam 游戏使其生效。

持续维护的调用及格式说明见 [当前手牌详情 JSON](../development/hand-inspection.md)。
