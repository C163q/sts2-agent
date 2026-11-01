# 当前手牌详情 JSON

适用于 Linux 游戏 `v0.107.1` 和当前 Mod `0.35.0`。文件接口 `inspect_hand` 读取全部当前可见手牌详情；同名 [MCP 工具](mcp.md) 支持返回预设和按 ID 筛选，输出英语，不切换游戏语言。它不移动鼠标、不出牌、不结束回合，也不读取牌堆内容；信息范围遵循 [观察约定](../observation.md)。

## 读取

重新构建、安装 Mod 并重启游戏，进入无遮挡的战斗后，在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_hand > .tmp/live/hand-inspection.json
```

安装和启动前提见 [正常游戏加载](live-game.md)。旧进程不会热加载新 DLL；首次接通 Mod 读取须按安装指南重启。文件调用不要求 `expected_state`，可用时出现在 `available_actions` 中；MCP 的动作令牌处理见 [调用语义](mcp.md#调用和错误语义)。诊断时可加 `--raw`，取得原始响应及采样前基础观察的 `snapshot_id`；默认玩法输出省略它。

## 参数与返回范围

MCP `0.31.0` 起支持以下可选参数；底层文件 `inspect_hand` 仍无参数。参数功能只更新 Python 输出；MCP `0.32.0` 与 Mod `0.35.0` 新增的卡面附魔字段需要同时更新 DLL 并完整重启游戏，再重连 MCP。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `full` | `full` 保留正文、共享解释和原有字段；`summary` 仅保留身份、显示费用与标记 |
| `card_ids` | 省略 | 非负整数卡牌 ID 数组；省略返回全部可见手牌，`[]` 返回空结果。重复 ID 去重，结果仍按当前手牌顺序排列 |

调用示例：

```json
{"preset":"summary","card_ids":[1,2,3]}
```

`summary` 的每张牌保留 `id/name/type/energy_cost/unplayable_markers/outline`，以及实际显示的 `star_cost`、已有特殊费用颜色和可见 `enchantment`。附魔名称、显示计数及置灰字段与[基础观察](observation.md#手牌与身份)完全相同，summary 不附送其效果正文；full 沿用原生共享悬停提示提供正文。费用仍是显示字符串，保留 `X`、`?`；未显示耗星时省略 `star_cost`。名称保留可见升级后缀，未知身份和不可读费用继续保留原有空值，不补真实内容或假定为零。摘要省略正文、稀有度、卡池、共享提示和 `notes.card_values`；选牌查看战场等仍适用的导航说明保留。标记和描边不等于可打出判断，合法性仍由 `inspect_targets` 或动作校验确认。

筛选后的 `full` 仅保留命中卡牌及其共享提示关联；空结果为 `hand: []/hover_tips: []`，不附卡牌数值说明。摘要空结果仅包含 `hand: []`，可能另有下述错误或导航说明。省略参数或显式 `preset: full` 的结果与原输出兼容。

不在当前可见手牌中的 ID 按请求首次出现的顺序合并报告，其他有效卡牌正常返回：

```json
{
  "hand": [],
  "errors": [{"code":"cards_not_in_hand","card_ids":[2,3]}]
}
```

不存在、已离手、不可见均采用同一错误，不透露卡牌是否位于其他牌堆。即使全部 ID 无效，也采用此结构，MCP `isError` 为 `false`；客户端必须检查 `errors`，不能仅凭 `isError` 判断所有请求 ID 均已命中。未发现无效 ID 时省略 `errors`。

`card_ids` 元素须为 0 至 2147483647 的整数，布尔值、字符串和浮点数不接受；未知参数或非法 `preset` 整次返回 `invalid_request`，不请求游戏。与地图输出参数一致，这类本地参数错误保留旧动作许可。

两种预设与空筛选都会读取并校验完整底层手牌后再投影，不能用筛选遮蔽格式损坏的数据；它们不改变 UI、游戏状态或原生状态指纹。成功读取刷新下一动作的许可，包括带合并错误或空结果的读取。此许可只代表当前状态已读取，不保证任何被筛出的卡牌可操作；过期状态、覆盖界面和真实动作合法性检查照常生效。底层请求失败仍返回普通顶层 `error`，不伪装成卡牌缺失。

## 格式

`full` 结果包含平级的 `hand` 和 `hover_tips` 数组。手牌顺序与基础观察一致，ID 也保持一致；每张牌复用 [基础手牌字段](observation.md#手牌与身份)，新增 `description`，不再内嵌提示集合：

| 字段 | 含义 |
| --- | --- |
| `description` | 当前完整牌面正文，保留换行和动态预览数值，移除颜色、字体等格式标记 |
| 顶层 `hover_tips[]` | 全部手牌共享的悬停解释集合；按标题和正文同时相同去重，按首次出现的顺序排列 |
| `hover_tips[].title` | 解释标题；原提示无标题时为 `null` |
| `hover_tips[].description` | 解释正文；卡牌预览提示使用该预览卡的名称及正文 |
| `hover_tips[].card_ids` | 关联这条解释的手牌 ID，按手牌顺序排列，同一 ID 不重复 |

例如多张防御只保留一条 Block 解释；同名提示的正文或动态数值不同时仍为不同条目。客户端完成整合，不修改原始响应；`--raw` 仍保留逐牌 `hover_tips`，无须更新 Mod 或重启游戏。

资源图标转为 `<Energy>`、`<Star>`；尚无明确语义映射的资源保留为 `<Icon:资源文件名>`，不静默丢弃。未知或锁定牌的 `description` 为 `null`，不生成该牌的提示条目，不补真实内容；顶层空集合不代表未知牌没有提示。正常可读的空手牌返回 `hand: []` 和 `hover_tips: []`。

有手牌时只附带 `notes.card_values`：

```json
{
  "notes": {
    "card_values": "Card values are contextual previews. Target-specific modifiers may apply only when aiming. Do not apply included modifiers again."
  }
}
```

该结果不包含敌人及意图，也不附带 `enemy_attack_intents`。空手牌不附带数值说明。基础观察仍只返回半隐藏手牌允许提供的字段，不自动附送正文和解释。

## 数值与读取边界

正文复用当前卡牌实例的动态预览值。工具不会为每个敌人重新预览，也不保证未选目标时的数值已包含目标易伤等效果。英语文本复用游戏的描述组合、提示生成和 SmartFormat；具体来源见 [核查记录](../research/2026-10-29-hand-inspection-sources.md)。

非战斗、界面被覆盖、手牌容器不可读或正在出牌时返回 `illegal_action`。视口外、被裁剪或隐藏的卡牌使用与基础观察相同的过滤条件。读取在 Godot 主线程同步完成，文件等待仍在后台。

英语格式化仅在当前线程的同步读取范围内生效，异常退出也恢复。工具绕过关键词和药水提示的语言缓存，不改全局语言或缓存条目；不调用 `NCard.UpdateVisuals`，也不重算当前战斗预览。Linux 初始化会让已安装的 `libgcc_s.so.1` 符号对游戏随附补丁库可见，无须设置 `LD_PRELOAD`。其他 Mod 的自定义提示、其他游戏版本及非中文界面的数字格式尚未验证；缺少英语资源或无法识别提示时显式报错，不混入其他语言或静默漏项。

## 只读验证

以下脚本只读取当前场景，要求操作期间不要手动改变游戏状态：

```sh
python3 -m tests.game.verifiers.verify_hand --ipc-dir .tmp/live/ipc --output .tmp/live/hand-inspection.json --report .tmp/live/hand-inspection-check.json
```

它核对详情和基础观察的 ID、完整正文、共享提示去重及所有卡牌关联、说明适用范围，以及读取前后观察令牌一致。需要测试英语作用域、缓存、关键词和动态数值时，在独立实例使用 `scripts/run_roundtrip.py --windowed --capture --check-hand`；该标志仅供仓库创建的铁甲战士测试战斗使用，不用于正式游戏。游戏读取的实施与验证见 [手牌详情实施记录](../research/2026-10-29-hand-inspection-plan.md)，输出整合见 [共享提示记录](../research/2026-10-29-shared-hand-tips.md)。

预设与筛选的单元、stdio 和独立图形验证见[手牌参数验证记录](../research/2026-11-01-hand-presets.md)。
