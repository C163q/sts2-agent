# 药水详情 JSON 实施记录

当前状态：已完成，共 3 项。文件接口、独立审阅、中文独立实例和正式战斗只读采样均已完成；Mod 0.6.0 已安装并由用户重启加载。本轮交付 JSON 审阅，未增加 MCP 或药水使用动作。

## 范围与格式

项目基线为 `184fde4`，游戏为 `v0.107.1`、分支同名、提交 `59260271`，证据来自安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`。目标类型反编译在未跟踪的 `.tmp/decompiled/`，截图依据为用户的 `~/Pictures/STS2_battle-4.png`。Mod 升为 `0.6.0`。

文件操作 `inspect_potions` 一次读取当前可见药水栏位。输出三部分：`slot_tip` 固定只出现一次，包含通用槽位标题和说明；`potion_slots` 按界面位置排列，药水为 `name/description` 对象、空槽为 `null`；共享 `hover_tips` 对药水额外提示按标题及正文去重，用从 0 开始的 `slot_indices` 关联槽位。即使全部槽位有药水，也保留通用 `slot_tip`，这是明确允许的通用说明，不要求当时存在空槽。

不附送稀有度、使用目标规则、隐藏生成结果、敌人意图或数值说明 notes。不能把不可读槽位当成空槽：本轮仅支持无遮挡战斗，容器、槽位或已占用药水图标不可见或不允许悬停时拒绝整次读取，不压缩位置。原始协议保留 `snapshot_id`，玩法结果移除它；无需动作令牌，不加入 `available_actions`。

## 已核实来源

- `NPotionHolder.OnFocus` 对空槽生成 `static_hover_tips/POTION_SLOT`，对药水使用 `Potion.Model.HoverTips`；不能调用悬停方法本身，因为会修改动画、播放随机音效。
- `PotionModel.HoverTip` 组合 `Title` 和 `DynamicDescription`，`HoverTips` 再拼接 `ExtraHoverTips`。`DynamicDescription` 使用当前实例的 DynamicVars，并可能修改 `EnergyVar.ColorPrefix`，读取必须在 `finally` 恢复。
- `SkillPotion` 的随机卡牌生成仅在 `OnUse` 执行，不读取或触发它。`BlockPotion.ExtraHoverTips` 提供原生 Block 解释，供额外提示去重验证。
- 复用已有主线程英语作用域及缓存绕过；共享普通文本与预览卡提示的渲染，保持手牌原行为。

## 实施步骤

1. 已完成客户端投影及共享提示测试，验证固定槽位说明、全空与全满、位置保持、同文去重和不同正文保留。新增 `PotionInspection` 和共享提示渲染，接入 `GameAdapter`、命令行并更新清单。
2. 已完成独立游戏检查：通过测试模式的原生药水获取流程准备样本，检查英语正文、额外提示、动态前缀、语言和缓存不变、隐藏/禁用/视口外过滤。验证 `get_state → inspect_potions → get_state` 的令牌及位置一致，回归手牌和通用界面说明。
3. 已完成独立审阅、安装新版和正式场景只读采样，导出 `.tmp/live/potion-inspection.json`。文档已更新，单独执行 Git 暂存及提交，随本记录交付。

## 验证边界

不使用、不丢弃正式药水，不生成供玩家选择的随机牌，不改变正式游戏状态或 MCP 禁用配置。非战斗场景、其他游戏版本及其他 Mod 自定义提示不在本轮范围。

## 验证结果

- 新增 4 项客户端测试先因缺少药水输出失败；实现后 `.tmp/mcp-venv/bin/python -m unittest discover -v -s scripts -p 'test_*.py'` 全部 `42/42` 通过，包含既有 MCP 的真实 stdio 握手和令牌检查。
- SDK `9.0.122` 对目标游戏程序集构建通过，`0` 警告、`0` 错误。
- 中文独立 GUI 实例通过原生 `PotionCmd.TryToProcure` 取得 Skill Potion、Block Potion、Block Potion，全满时仍保留一份通用槽位说明；两个 Block 提示合并为一条，关联 `[1, 2]`。样本为 `.tmp/roundtrip/potion-inspection.json`，读取前、中、后令牌一致，证据在 `potion-inspection-check.json`。
- `.tmp/roundtrip/potion-checks.json` 的 `15/15` 项通过，包含英语正文、满栏规则、额外解释、能量前缀恢复、隐藏/禁用/视口外过滤、语言与缓存保持、重复读取一致。主菜单拒绝证据为 `.tmp/roundtrip/potion-setup.json`。
- 手牌说明、界面说明及基础观察分别通过既有 `8`、`15`、`27` 项游戏内检查；手牌与界面的新回归产物为 `.tmp/roundtrip/potion-hand-regression*.json` 和 `potion-ui-regression*.json`，读取前后令牌均未改变。游戏日志无 `[ERROR]`。
- 正式场景为进阶 `6`、楼层 `3`、第 `1` 回合、生命 `65/80`，敌人为 Leaf Slime (S)、Twig Slime (M)、Twig Slime (S)。用户重启新版后，读取 `2` 个槽位：第一个 Skill Potion，第二个 `null`；通用说明仅一份，额外提示为空。`.tmp/live/potion-inspection-check.json` 确认前、中、后观察令牌一致，未执行正式游戏动作。
- 独立审阅无阻断问题；指出的空槽图标路径验证缺口已由上述正式样本覆盖。全部独立测试实例已停止。其他药水类型、非战斗场景及自定义提示未完整覆盖。
