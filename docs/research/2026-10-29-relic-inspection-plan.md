# 遗物详情实施记录

当前状态：本次实施完成。共 3 项，已完成 3 项；文件 JSON、独立游戏验证、回归、独立审阅、安装和正式场景只读采样均完成。MCP 接入不在本次范围内，无实施遗留或阻塞。

## 要求与方案

沿用批量只读查看约定，新增文件操作 `inspect_relics`，本次不接 MCP。仅支持无遮挡战斗，枚举当前遗物栏实际可见、可悬停的图标，不读取玩家隐藏收藏、未来随机结果或额外检查界面。优先复用原生实例 `HoverTips`；静态本地化表不能替代动态正文，调用 `OnFocus` 会触发动画，因此不采用这两种方式。

原始响应包含 `snapshot_id` 和 `relics[]`；各项为 `name/counter/description/hover_tips`。客户端移除控制信息，附带解释按标题及正文共同去重到平级 `hover_tips[]`，用从 0 开始、仅对本次结果有效的 `relic_indices[]` 关联。主正文保留在遗物条目中。无可见计数时 `counter: null`。可见空栏返回空数组，不可读界面返回 `illegal_action`。不增加数值 notes 或动作授权。

## 核对基线

- Linux 游戏 `v0.107.1`，main，commit `59260271`；证据为安装目录的 `release_info.json` 与 `data_sts2_linuxbsd_x86_64/sts2.dll`。
- `MegaCrit.Sts2.Core.Nodes.Relics.NRelicInventoryHolder.OnFocus` 使用 `_relic.Model.HoverTips`；`RefreshAmount` 控制 `%AmountLabel`，隐藏计数不能从 `DisplayAmount` 补齐。
- `RelicModel.HoverTips` 为主提示及 `ExtraHoverTips`；`HoverTip` 使用 `DynamicDescription`，包含用尽、熔化包装；不额外提供 `Flavor`。
- `DynamicDescription` 会写入 `EnergyVar.ColorPrefix`，需要 `finally` 恢复。`HoverTipFactory.FromRelic` 不缓存说明，无须新增拦截。
- `RelicCmd.Obtain<T>(Player)` 可在独立测试入口准备遗物；正式游戏不会设置测试标志或调用该入口。
- 本地反编译证据位于被忽略的 `.tmp/decompiled/`，包括 `RelicModel`、`NRelicInventoryHolder`、`NRelicInventory`、`RelicCmd.cs`、`Lantern.cs`、`PenNib.cs`。

## 实施步骤

- [x] 1. 在 `scripts/test_player_result.py` 先验证遗物投影、共享下标、同名异文、空数组和源数据不变；确认现有客户端失败，再实现 `roundtrip_client.py` 的投影和 CLI 操作。
- [x] 2. 新增 `RelicInspection.cs`，在 `GameAdapter` 路由并升级 Mod 至 0.8.0；新增 `RelicInspectionChecks.cs` 及 `--check-relics`，在独立中文实例通过正常 `RelicCmd` 准备附带关键词、能量和计数遗物。检查英文动态正文、隐藏/透明/屏幕外/禁用图标、能量变量恢复、语言与原生提示不变、重复读取一致；新增 `verify_relics.py` 验证完整文件链路。
- [x] 3. 构建及回归、独立审阅，更新持续文档并安装；分别保存独立 JSON 及用户重启后的正式只读样本。验证后创建本次 Git 提交。

## 验证关注点

计数 0 与不可见计数区分；部分图标不可读不能借玩家模型补齐；重复提示不合并不同正文；原生文本格式化不改变变量或语言；未支持界面保守报错。实现与游戏检查共用原生对象，不以纯模型测试替代游戏加载验证。

## 执行结果

- 先运行客户端测试，新增两项均因缺失 `relics` 投影而失败；实现后通过。最终 Python 全套 62 项通过，10.806 秒，日志为 `.tmp/relic-python-tests.log`；MCP 异步测试在允许本地 socketpair 的沙箱外运行。包含故意输入错误响应产生的预期诊断。
- .NET 9 构建零警告、零错误。独立中文图形实例成功加载 Mod 0.8.0，遗物专项 24 项全部通过。包括原生动态值、能量图标、计数 0、隐藏计数、隐藏/透明/屏幕外/禁用/无纹理图标、空可见列表、熔化正文、变量与中文提示不变。
- `.tmp/roundtrip/relic-inspection.json` 含 Burning Blood、Anchor、Lantern、Pen Nib 和 2 条共享解释。`.tmp/roundtrip/relic-inspection-check.json` 证明重复详情及前后观察令牌一致；`.tmp/roundtrip/relic-setup.json` 记录主菜单拒绝及独立测试入口准备。
- 原有观察 27、手牌 8、界面 15、药水 15、战斗对象 31 项原生检查均通过，各自只读导出也通过。测试实例已停止，未向正式游戏发送动作。
- 独立审阅未发现 Critical、Important 或 Minor 问题。持续文档的本地链接和 `git diff --check` 通过；同步修正了界面说明中将已实现 powers 调用写为“后续”的旧描述。
- 已使用带编号备份的 `install` 安装至本机 Steam 游戏 Mod 目录，构建与安装文件校验值一致。用户重启后，正式战斗只读采样返回 Burning Blood 和 Silver Crucible；后者屏幕计数为 2，两者均有英语正文，无附带解释。`verify_relics.py` 验证重复详情和前后基础观察令牌一致。JSON 与完整响应证据分别保存为 `.tmp/live/relic-inspection.json` 和 `.tmp/live/relic-inspection-check.json`，未执行正式游戏动作。

未验证范围：多人与非战斗界面、全部原生遗物和全部特殊状态、其他 Mod 改写悬停行为。当前状态令牌只表示基础导出内容相同，不证明所有游戏内部字段不变；额外通过变量、语言和原生提示检查验证读取副作用。
