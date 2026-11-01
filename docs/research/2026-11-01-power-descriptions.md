# 状态说明的英语格式化与偷窃草蜢回执

## 基线与结论

核对日期为 2026-11-01，游戏为 Linux `v0.107.1`（release `59260271`），RitsuLib 为 `0.6.10` 的 `0.107.1` 兼容运行时。实现基线为 `efa14e1`，修复后 Mod 为 `0.34.4`，MCP 保持 `0.30.0`，公开工具参数和观察 schema 不变。正式游戏现场未参与本次测试，也未替换已安装的 Mod。

r7 报告指出 Escape Artist 图标计数为 5、4 时，`inspect_combatants` 均显示 `Tries to escape the combat this turn.`。独立中文实例复现了错误；原生中文悬停会显示实际计数，原生英文模板也包含正确的复数分支。问题位于工具的英语格式化路径，不是计数读取错误或游戏英文资源写错。

同一复现还发现 Vulnerable 的 2 回合被写成 `2 turn`，Shrink 说明混入中文施加者名称。原生 `PowerModel.HoverTips` 的预编译或内联调用可以绕过 `LocString.GetFormattedText` 的 Harmony 拦截；底层原始文本仍被替换成英文，但原生格式化继续使用中文规则，导致复数分支与缓存变量替换失效。直接格式化同一个 Escape Artist `LocString` 则得到正确英文，定位了这两条路径的差异。

## 原生依据与修复

证据来自安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`、`SmartFormat.dll` 及 `SlayTheSpire2.pck`：

- `PowerModel.HoverTips` 根据当前实例构造 smart/remote 或普通说明，填入 Amount、拥有者、施加者等变量，再附加 `ExtraHoverTips`。
- `NPower.OnHovered` 直接展示当前 `Model.HoverTips`。
- `localization/eng/powers.json` 的 Escape Artist smartDescription 使用 `Amount:plural`；计数 1 对应 `this turn`，其余对应 `after N turns`。中文同一条目直接代入 Amount。
- `PluralLocalizationFormatter` 根据格式化 provider 的语言选择复数规则；中文规则选择第一分支。
- `ThievingHopper.AfterAddedToRoom` 施加计数 5；`EscapeArtistPower.AfterSideTurnEnd` 递减计数，到 1 开始闪烁。实际逃跑由原生怪物流程执行，工具不靠计数模拟招式。

修复在 `PowerModel.HoverTips` getter 内重绑定三个 `LocString.GetFormattedText` 调用，显式经过已有英语格式化函数。英语读取作用域内使用英文模板和英文 culture，需要替换的缓存变量另建字典；作用域外仍调用原生格式化。保留原生变量填充、smart/remote 分支及附加提示，不硬编码某个状态的说明，不修改真实 Amount、DynamicVars、LocString 或 UI 语言。

可见性筛选、屏幕计数读取、提示去重和 `sources` 保持原样。普通观察和 `end_turn` 不自动展开状态正文；其他状态仍通过专门详情读取。

## 同类审查与范围

`--check-combatants` 除原有可见性、动态变量、施加者缓存、语言恢复、共享提示和异常恢复检查外，增加计数 5 的 Escape Artist 断言。独立中文实例的 33 项检查全部通过。

另扫描当前英语 `powers.json` 中 555 条说明模板：289 条普通说明、261 条 smartDescription、5 条 remoteDescription，其中 94 条使用复数格式。每条以计数 1、2、5 和两组布尔上下文格式化，对照原生英文与中文环境中的英语作用域，共 3330 组，零差异。覆盖了 Asleep、Blur、Buffer、Burst、Double Damage、Intangible、No Escape、Sandpit、The Bomb、Weak 等同类复数或倒计时模板，并包含条件格式。

这项扫描使用控制变量，验证模板格式化的一致性，不等于 555 条说明对应的真实状态生命周期均已实机验证。实际可见实例覆盖 Escape Artist、Vulnerable、Strength、Shrink；Swipe 通过原生偷牌后产生。远程说明的模板对照不能替代多人实测，模型专用附加提示也不能仅由模板扫描证明完整。

## 草蜢首回合与信息边界

测试场景 `turn:thieving_hopper` 使用原生 `ThievingHopperWeak` 战斗，不替换敌人行动，也不手动设定偷取结果。真实 stdio MCP 连续验证计数 5、4、3、2、1，再确认原生逃跑结束战斗。计数 5、4、1 时，在独立实例内分别触发中英文原生 `NPower.OnHovered` 并保存截图；详情中的英文说明与原生英文提示相同。测试结束恢复语言；这些测试专用操作不属于公开 MCP 工具。

首回合测试玩家未出牌或防御，`end_turn` 返回 `player_ready/complete=true`，共 13 条事件：5 张已见手牌弃置、Swipe 施加、17 点生命伤害、Escape Artist 从 5 变 4、下一回合抽到 5 张牌。与 r7 中有格挡和遗物的实际存档不同，伤害和额外触发不能逐条套用。

回执没有专门的偷牌事件，也没有输出被偷牌名、从抽牌堆还是弃牌堆偷取、随机选择规则、原牌堆顺序或未来行动。Swipe 提示可以展示 UI 中已经公开的被偷卡牌预览及归还说明；这些信息仍需 `inspect_combatants` 读取。卡牌事件只涉及原先可见手牌和期间实际抽到的牌，不由内部被偷卡牌的身份补写战报。

首回合完整 MCP 玩法 JSON 保存在 `.tmp/2026-11-01-power-descriptions/final-gui/hopper/verify/hopper-first-end-turn.json`。这是实际响应，不是手工构造的示例。

## 验证与证据

本地证据统一保存在忽略目录 `.tmp/2026-11-01-power-descriptions/`：

- `source/`：本次目标版本反编译与资源证据；不纳入 Git。
- `red-embedded/`：旧行为的 Escape Artist、Vulnerable 和 Shrink 失败证据。
- `green-embedded-v6/combatant-checks.json`：33 项检查及 3330 组模板对照通过。
- `hopper-gui/`：首轮完整草蜢战斗及六张原生悬停截图；计数 5、4、1 的中英文提示均已核对。
- `final-gui/`：最终构建的草蜢与查看续接通过；第三项先古选牌在入场按钮尚未启用时被旧验证脚本点击而失败。该目录原样保留，不能称为一次全绿的三项套件。
- `ancient-regression-gui/`：修正验证脚本的初始等待后，独立重跑先古多选回归通过，结果见 `report.json`。
- `python.log`、`python-final.log`：完整 Python 回归均为 318 项通过，最终一轮耗时见日志。
- `csharp.log`：27 项无游戏 C# 检查通过。

调查中的失败证据保留：`green-embedded/` 是直接拦截 `LocManager.SmartFormat` 时 Harmony/MonoMod 无法生成带异常过滤器的方法替身，导致测试 Mod 初始化失败；该方案已撤销。`green-embedded-v2/`、`v3/` 是批量克隆脱离实际流程的 power 模型时独立实例退出，未计为通过，最终扫描不再克隆模型。`v4/`、`v5/` 分别暴露了模板夹具的 StringVar、EnergyVar 类型设置错误，已按程序集签名修正；未把原生格式化返回原模板的错误计为成功。

先古选牌失败时，观察中的三个选项均为 `enabled=false`，且未声明 `choose_ancient_option` 或 `advance_dialogue`；游戏正确返回 `illegal_action`。仅给 `verify_selection_scene.py` 的先古分支补上最长 10 秒、只读的初始输入就绪等待，不自动重试失败动作，也未放宽游戏可行动条件。

最终构建 DLL SHA-256 为 `c0b0cd9cc94c2940a97bc5241c3e422cdcc322aea1060d0f5fa348b33ca79205`，上述最终实例检查与图形回归使用同一构建。最终三个图形场景分别通过，跨两个进程；保留中间失败，不宣称单次三项套件全绿。独立只读审阅未发现 P0–P3 问题。

未执行全套默认图形清单或完整 LLM 通关；没有修改 summary，也未为战报新增偷牌事件。持续维护的现状说明见[战斗对象详情](../development/combatant-inspection.md)与[结束回合](../development/end-turn.md)。同时修正[底层协议指南](../development/roundtrip.md)中地图一行未区分文件协议无参数与 MCP 输出参数的过时描述。
