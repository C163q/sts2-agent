# 当前药水详情 JSON

文件操作 `inspect_potions` 与同名 [MCP 工具](mcp.md) 适用于 Linux 游戏 `v0.107.1`、Mod `0.16.0`。一次读取当前可见药水栏位、完整英语说明和额外悬停解释，不使用或丢弃药水，不生成技能药水等效果中的随机选项。MCP full 与文件客户端提供相同的玩法 JSON，默认 default 省略普通空值；数组空槽仍保留，规则见[公共预设](mcp.md#输出预设)。动作另用 [药水工具](potion-actions.md)。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启游戏，进入无遮挡的战斗后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_potions > .tmp/live/potion-inspection.json
```

MCP 调用 `inspect_potions()` 无须参数，成功时刷新状态令牌；完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。文件读取无须动作令牌，可用时列入 `available_actions`。加 `--raw` 保留文件协议的 `id/ok/state`、`state.snapshot_id` 和逐药水额外提示；默认输出移除控制信息，并合并共享提示。不附带手牌或敌人意图的数值解读 notes。

## 格式

| 字段 | 内容 |
| --- | --- |
| `slot_tip` | 通用槽位提示的 `title/description`，每次成功读取固定只显示一份，即使全部槽位有药水 |
| `potion_slots[]` | 从左到右按位置排列；有药水时为 `name/description`，已确认空槽为 `null`，不重复槽位说明 |
| `hover_tips[]` | 药水额外解释，按标题和正文同时相同去重；不重复药水本身的正文 |
| `hover_tips[].slot_indices` | 从 0 开始的关联槽位下标，按槽位顺序排列且不重复 |

同一提示的标题相同、正文或动态数值不同时保留为不同条目。空栏位和全满栏位均只有一个 `slot_tip`；无额外解释时 `hover_tips: []`。英语正文来自当前药水实例的原生 `HoverTip/DynamicDescription`，例如技能药水显示选择 3 张随机技能牌中的 1 张及本回合免费的规则，不附送实际随机选项。

共享解释的示例来自独立中文游戏：两个 Block Potion 分别在下标 1、2 的槽位，共享一个 `Block` 提示，`slot_indices: [1, 2]`。正文保留换行，格式标记移除，资源图标按现有约定转成 `<Energy>`、`<Star>` 等。未知提示类型显式报错，不静默丢弃。

## 读取边界

支持可见战斗顶栏及 [药水动作支持的战斗外页面](potion-actions.md#场景与停止边界)，选牌背后的战场查看沿用原有只读范围。Mod 0.49.1 起也支持当前暴露的地图、牌组和三类牌堆浏览页上的可悬停药水；只读查看不代表允许在覆盖页使用或丢弃，见[观察边界](observation.md#mcp-输出预设)。容器、任一槽位或已占用药水图标隐藏、在视口外、被裁剪或不能悬停时，整次读取返回 `illegal_action`，不把未知内容当成空槽，也不压缩位置。没有可用药水不等于读取失败；可读且全空的栏位仍返回各位置的 `null` 和一份通用说明。

通用槽位说明即使没有空槽也提供，是 [信息边界](../observation.md) 明确允许的固定帮助文本。稀有度、内部模型 ID、使用目标、未来随机结果和其他游戏状态不随详情返回；目标规则单独查询。

读取在游戏主线程同步完成，复用独立英语作用域，不触发 `NPotionHolder.OnFocus` 的动画、随机音效或使用流程。动态描述会暂时设置能量图标前缀，读取在 `finally` 中恢复；关键词和药水提示缓存不改动。其他版本、其他 Mod 自定义提示及非中文界面的数字格式未验证。

## 只读验证

运行期间应避免手动改变游戏状态：

```sh
python3 -m tests.game.verifiers.verify_potions --ipc-dir .tmp/live/ipc --output .tmp/live/potion-inspection.json --report .tmp/live/potion-inspection-check.json
```

脚本核对读取前、中、后的观察令牌一致、槽位位置及名称与基础观察对应、通用说明只出现一次，以及共享提示和所有槽位关联一致。

已在中文独立实例验证满栏与重复 Block 提示，在正式战斗验证 Skill Potion 加空槽的排列；两次采样前后观察令牌均一致。正式场景还完成了真实 stdio MCP 读取，与文件输出一致且前后观察未变，见 [MCP 实施记录](../research/2026-10-29-mcp-potion-inspection.md)。旧详情专项验证仅覆盖上述战斗样本；新药水动作验证另覆盖战斗外页面。

独立实例可用 `scripts/run_roundtrip.py --windowed --capture --check-potions`。该标志仅用于测试：通过原有 `start_test_combat` 测试入口创建战斗时，使用游戏正常获取流程加入 Skill Potion 和两个 Block Potion；检查满栏、英语正文、可见性、缓存及能量前缀恢复。不要为正式 Steam 游戏设置该标志。证据见 [实施记录](../research/2026-10-29-potion-inspection-plan.md)。
