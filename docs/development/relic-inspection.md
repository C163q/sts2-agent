# 遗物详情 JSON

文件操作 `inspect_relics` 与同名 [MCP 工具](mcp.md) 适用于 Linux 游戏 `v0.107.1`、Mod `0.31.0`。一次只读查看当前遗物栏中可见、可悬停的遗物，以英语返回原生正文和附带解释。支持无遮挡战斗及原生可查看的战斗背景（例如[建筑师](run-ending.md)）、当前暴露的[先古之民](ancients.md)和[商店](shop.md)，可用于查看已持有的添水等遗物说明。MCP 与文件客户端返回相同的玩法 JSON。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启，在无遮挡战斗或暴露的商店中执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_relics > .tmp/live/relic-inspection.json
```

MCP 调用 `inspect_relics()` 无须参数，成功时刷新状态令牌；完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。文件调用不需要动作令牌，可用时列入 `available_actions`，不执行游戏动作。默认客户端移除控制信息；加 `--raw` 保留原始响应和状态令牌。

## 格式

| 字段 | 内容 |
| --- | --- |
| `relics[]` | 当前可见且可悬停的遗物，沿用遗物栏顺序 |
| `relics[].name` | 原生悬停提示的英语名称 |
| `relics[].counter` | 当前屏幕计数标签；不可见或不可解析为整数时为 `null`，可见的 0 保留为 0 |
| `relics[].description` | 当前实例的原生英语正文，包括原生提供的动态值及用尽、熔化等说明 |
| `hover_tips[]` | 附带的关键词或卡牌解释，以 `title/description` 共同去重 |
| `hover_tips[].relic_indices[]` | 对应本次 `relics` 数组的位置，从 0 开始，仅对本次结果有效 |

主正文保留在遗物条目内；重复附带解释集中保存，同名但正文不同的解释分别保留。没有可读条目时返回 `relics: []`；没有额外解释时为 `hover_tips: []`。本调用不包含手牌数值、敌人意图 notes。

例如 Lantern 的正文为 `Start each combat with an additional <Energy>.`，附带 `Energy` 解释；Pen Nib 初始可见计数为 `0`。图标沿用 `<Energy>`、`<Star>` 等文本表示，保留正文换行，去除格式标签。原始响应中的解释位于各遗物的 `hover_tips`，文件客户端将它们合并为上述共享结构。

## 读取边界

遗物来自实际 `NRelicInventory.RelicNodes`，不遍历玩家模型中未展示的遗物。必须有可见的 holder、遗物节点和带纹理的图标，holder 须启用且接受鼠标事件。隐藏、透明、屏幕外、被裁剪或不可悬停的条目排除；整个遗物栏隐藏，或当前不属于无遮挡战斗、暴露的先古之民/商店时返回 `illegal_action`。可见性采用现有节点及矩形规则，不能精确判断任意像素遮挡。

正文和附带说明取自已显示遗物实例的 `RelicModel.HoverTips`，与原生悬停入口相同。只输出原生悬停正文，不附送风味文本、内部计数、获取楼层、未来触发结果或概率推演。不会调用 `OnFocus`、触发动画、切换语言、设置目标或打开遗物检查页。格式化对 `EnergyVar.ColorPrefix` 的临时修改在 `finally` 恢复，未知提示类型整次报错，不静默丢弃。

## 验证

运行脚本时避免手动改变游戏：

```sh
python3 scripts/verify_relics.py --ipc-dir .tmp/live/ipc --output .tmp/live/relic-inspection.json --report .tmp/live/relic-inspection-check.json
```

脚本检查重复读取一致、前后基础观察令牌不变、名称和计数与基础观察按顺序对应、共享解释去重及下标有效。令牌只覆盖已导出的基础观察，不是全部游戏内部状态的版本。

独立中文实例使用 `scripts/run_roundtrip.py --windowed --capture --check-relics`；在原有测试入口通过 `RelicCmd.Obtain` 准备 Anchor、Lantern 和 Pen Nib，加上初始 Burning Blood。不要为正式游戏设置测试标志。已完成独立游戏的 24 项检查及只读 JSON 导出，得到 4 个遗物、2 条共享解释；原有观察、手牌、界面、药水和战斗对象检查均通过，Python 全套 62 项通过。样本位于 `.tmp/roundtrip/relic-inspection.json`，证据及未验证范围见 [实施记录](../research/2026-10-29-relic-inspection-plan.md)。多人、非战斗界面、其他 Mod 改写悬停、全部遗物和全部特殊状态尚未穷举验证。

正式游戏重启后已完成只读采样：返回 Burning Blood 和可见计数为 2 的 Silver Crucible，均有英语正文，没有原生附带解释，因此 `hover_tips: []`。重复详情及前后基础观察令牌一致，未执行游戏动作。JSON 位于 `.tmp/live/relic-inspection.json`，证据位于 `.tmp/live/relic-inspection-check.json`；正式与独立样本分别保存。

正式游戏另完成 MCP server 0.6.0 的真实 stdio 只读采样，取得相同的两个遗物和可见计数；与文件 JSON 一致，重复读取及前后状态不变。JSON 为 `.tmp/live/mcp-relic-inspection.json`，协议证据为 `.tmp/live/mcp-relic-evidence.json`，验证范围见 [MCP 实施记录](../research/2026-10-29-mcp-relic-inspection.md)。
