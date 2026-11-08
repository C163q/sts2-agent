# 当前手牌详情 JSON

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件接口 `inspect_hand` 读取全部当前可见手牌详情；同名 [MCP 工具](mcp.md) 支持返回预设和按 ID 筛选，输出英语，不切换游戏语言。手牌正文与解释的信息范围遵循 [观察约定](../observation.md)。

成功结果的 `scene/screen` 来自本次快照，表示当前房间与覆盖状态，统一规则见[MCP 上下文](mcp.md#成功结果的场景上下文)。

## 读取

重新构建、安装 Mod 并重启游戏，进入无遮挡的战斗后，在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_hand > .tmp/live/hand-inspection.json
```

安装和启动前提见 [正常游戏加载](live-game.md)。文件调用不要求 `expected_state`，可用时出现在 `available_actions` 中；MCP 的动作令牌处理见 [调用语义](mcp.md#调用和错误语义)。诊断时可加 `--raw`，取得原始响应及采样前基础观察的 `snapshot_id`；默认玩法输出省略它。

## 参数与返回范围

以下为 MCP 可选参数；底层文件 `inspect_hand` 仍无参数。参数筛选和输出精简由 Python 完成，可见附魔等数据仍依赖游戏端采样。更新与版本排错见[正常游戏指南](live-game.md#更新与排错)。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `default` | `default` 保留完整内容并省略普通空值；`full` 保留原有空值；`summary` 仅保留身份、显示费用与标记 |
| `card_ids` | 省略 | 非负整数卡牌 ID 数组；省略或 `null` 返回全部可见手牌，`[]` 返回空结果。重复 ID 去重，结果仍按当前手牌顺序排列 |

调用示例：

```json
{"preset":"summary","card_ids":[1,2,3]}
```

`summary` 的每张牌保留 `id/name/type/energy_cost`，按实际显示保留非空 `unplayable_markers` 和有颜色的 `outline`，以及实际显示的 `star_cost`、已有特殊费用颜色、可见 `enchantment` 和 `affliction`。附魔名称、显示计数及置灰字段与[基础观察](observation.md#手牌与身份)完全相同，summary 不附送其效果正文；full 沿用原生共享悬停提示提供正文。费用仍是显示字符串，保留 `X`、`?`；未显示耗星时省略 `star_cost`；空禁用标记和 `outline:"none"` 也省略。名称保留可见升级后缀，普通空值按 default 规则省略。摘要省略正文、稀有度、卡池、共享提示和 `notes.card_values`；选牌查看战场等仍适用的导航说明保留。可打出性由 `inspect_targets` 或动作校验确认，标记和描边表达实际外观。

`unplayable_markers` 的 energy/star 表示禁用图标所在的费用位置，不是不可打出的原因；资源不足通常显示为红色费用，而标记数组仍可能为空。无可读附魔或 Affliction 时，full 显式保留 `enchantment:null`、`affliction:null`，default 和 summary 省略普通空值；比较中的空值仍遵循统一例外规则。附魔不显示计数时不生成 amount。`affliction` 仅含已识别覆盖外观的英语 `name`，不返回内部层数；两种效果可以共存，效果解释通过完整详情查看。

资源字段与卡牌筛选独立。full 提供顶层可空整数 `energy/max_energy/stars`，来自当前能量计和星星计；即使角色身体隐藏，也不影响独立可见的 HUD。default 省略普通空值；summary 将完整能量对合并为 `energy:"3/3"`，省略 max_energy，stars 可见时保留整数，包括 0。部分能量不可读时 summary 省略能量，不从模型补齐。

顶层另提供可空整数 `draw_count/discard_count/exhaust_count`，分别对应当前抽牌堆／弃牌堆／消耗牌堆入口的可见计数标签，与 get_observation.player 复用同一 HUD 读取。full 保留 null，default／summary 省略普通 null，0 始终保留；隐藏入口或标签不从模型补齐为零。三项计数独立于 card_ids，空筛选和部分无效 ID 均不影响返回。

筛选后的 `full` 仅保留命中卡牌及其共享提示关联；空结果为 `hand: []/hover_tips: []`，不附卡牌数值说明。摘要空结果保留 `hand: []` 及当前可读资源，可能另有下述错误或导航说明。full 的资源字段也不受空筛选或无效 ID 影响；省略 preset 则使用 default，过滤规则见[MCP 输出预设](mcp.md#输出预设)。

不在当前可见手牌中的 ID 按请求首次出现的顺序合并报告，其他有效卡牌正常返回：

```json
{
  "hand": [],
  "errors": [{"code":"cards_not_in_hand","card_ids":[2,3]}]
}
```

不存在、已离手、不可见均采用同一错误，不透露卡牌是否位于其他牌堆。即使全部 ID 无效，也采用此结构，MCP `isError` 为 `false`；客户端必须检查 `errors`，不能仅凭 `isError` 判断所有请求 ID 均已命中。未发现无效 ID 时省略 `errors`。

`card_ids` 元素须为 0 至 2147483647 的整数，布尔值、字符串和浮点数不接受；未知参数或非法 `preset` 整次返回 `invalid_request`，不请求游戏。与地图输出参数一致，这类本地参数错误保留旧动作许可。

所有预设与空筛选均在完整底层校验后投影；成功读取刷新下一动作许可，包括空结果或带合并错误的结果。动作再按当前状态、页面和原生合法性复核。底层请求失败仍返回普通顶层 `error`，不伪装成卡牌缺失。

明确拒绝保留已有许可，坏响应、超时、异常或取消仍清除许可；首次失败不生成许可。公开原因及恢复指示遵循[MCP 错误语义](mcp.md#调用和错误语义)。

## 格式

`full` 结果包含平级资源与牌堆计数，以及 `hand` 和 `hover_tips` 数组。手牌顺序与基础观察一致，ID 也保持一致；每张牌复用 [基础手牌字段](observation.md#手牌与身份)，新增 `description`，不再内嵌提示集合：

| 字段 | 含义 |
| --- | --- |
| `description` | 当前完整牌面正文，保留换行和动态预览数值，移除颜色、字体等格式标记 |
| 顶层 `hover_tips[]` | 全部手牌共享的悬停解释集合；按标题和正文同时相同去重，按首次出现的顺序排列 |
| `hover_tips[].title` | 解释标题；原提示无标题时为 `null` |
| `hover_tips[].description` | 解释正文；卡牌预览提示使用该预览卡的名称及正文 |
| `hover_tips[].card_ids` | 关联这条解释的手牌 ID，按手牌顺序排列，同一 ID 不重复 |

例如多张防御只保留一条 Block 解释；同名提示的正文或动态数值不同时仍为不同条目。客户端完成整合，不修改原始响应；`--raw` 仍保留逐牌 `hover_tips`，不修改游戏内原始采样。

资源图标转为 `<Energy>`、`<Star>`；尚无明确语义映射的资源保留为 `<Icon:资源文件名>`，不静默丢弃。未知或锁定牌的 `description` 为 `null`，不生成该牌的提示条目，不补真实内容；顶层空集合不代表未知牌没有提示。正常可读的空手牌返回 `hand: []`、`hover_tips: []` 及当前可读资源。

有手牌时只附带 `notes.card_values`：

```json
{
  "notes": {
    "card_values": "Card values are contextual previews; aiming may change target-specific values."
  }
}
```

该结果不包含敌人及意图，也不附带 `enemy_attack_intents`。空手牌不附带数值说明。基础观察仍只返回半隐藏手牌允许提供的字段，不自动附送正文和解释。

## 共用卡牌格式

卡牌字段由 `output/card_format.py` 统一投影。内部 face_full/face_default 固定不含 description 或 hover_tips；full/default 提供正文和可读悬停解释；summary 共用本页摘要规则。这些是内部内容模式，不增加公开 face 参数。

get_observation全部标准卡牌在full/default中采用face_full/face_default，不提供卡牌正文或逐牌悬停解释；summary采用共用摘要。范围包括手牌、商店、牌组／牌堆、选牌候选、卡包、所有比较侧及结算／解锁卡牌。专项详情继续提供各自完整牌面；原始身份及比较上下文保持。

普通 null 由统一 preset 入口过滤，比较的 before/after 仍保留必要空值；各工具保留自己的 ID、顺序、上下文和提示关联。原生实卡读取与网格隔离克隆分别保留，不重算持有卡牌。卡牌身份引用、transition 来源、悬浮君王之剑和一般悬停文本不扩展成完整卡牌。

## 数值与读取边界

正文复用当前卡牌实例的动态预览值。工具不会为每个敌人重新预览，也不保证未选目标时的数值已包含目标易伤等效果。英语文本复用游戏的描述组合、提示生成和 SmartFormat；具体来源见 [核查记录](../research/2026-10-29-hand-inspection-sources.md)。

非战斗、界面被覆盖、手牌容器不可读或正在出牌时返回 `illegal_action`。视口外、被裁剪或隐藏的卡牌使用与基础观察相同的过滤条件。读取在 Godot 主线程同步完成，文件等待仍在后台。

英语格式化仅在当前线程的同步读取范围内生效，异常退出也恢复。工具绕过关键词和药水提示的语言缓存，不改全局语言或缓存条目；不调用 `NCard.UpdateVisuals`，也不重算当前战斗预览。Linux 初始化会让已安装的 `libgcc_s.so.1` 符号对游戏随附补丁库可见，无须设置 `LD_PRELOAD`。其他 Mod 的自定义提示、其他游戏版本及非中文界面的数字格式尚未验证；缺少英语资源或无法识别提示时显式报错，不混入其他语言或静默漏项。

## 只读验证

游戏端读取见 [HandInspection](../../src/Sts2Agent/Observation/HandInspection.cs)，完整公开校验见 [hand_details](../../src/sts2_mcp/output/hand_details.py)，卡牌格式统一由 [card_format](../../src/sts2_mcp/output/card_format.py)维护。

以下脚本只读取当前场景，要求操作期间不要手动改变游戏状态：

```sh
python3 -m tests.game.verifiers.verify_hand --ipc-dir .tmp/live/ipc --output .tmp/live/hand-inspection.json --report .tmp/live/hand-inspection-check.json
```

它核对详情和基础观察的 ID、完整正文、共享提示去重及所有卡牌关联、说明适用范围，以及读取前后观察令牌一致。需要测试英语作用域、缓存、关键词和动态数值时，在独立实例使用 `scripts/run_roundtrip.py --windowed --capture --check-hand`；该标志仅供仓库创建的铁甲战士测试战斗使用，不用于正式游戏。游戏读取的实施与验证见 [手牌详情实施记录](../research/2026-10-29-hand-inspection-plan.md)，输出整合见 [共享提示记录](../research/2026-10-29-shared-hand-tips.md)。

预设与筛选的单元、stdio 和独立图形验证见[手牌参数验证记录](../research/2026-11-01-hand-presets.md)。

卡牌实节点与浏览克隆的职责及共享外观入口见[读取架构](architecture.md#展示与悬停读取)；克隆上下文不与半隐藏手牌读取合并。

手牌牌堆计数的原生标签／隐藏边界及三预设验证见[补充实施记录](../research/2026-11-04-hand-pile-counts.md)。
