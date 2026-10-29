# 当前手牌详情 JSON

适用于 Linux 游戏 `v0.107.1` 和 Mod `0.4.0`。文件接口 `inspect_hand` 一次读取全部当前可见手牌详情，输出英语，不切换游戏语言。它不移动鼠标、不出牌、不结束回合，也不读取牌堆内容；信息范围遵循 [观察约定](../observation.md)。MCP 暂未公开此调用。

## 读取

重新构建、安装 Mod 并重启游戏，进入无遮挡的战斗后，在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_hand > .tmp/live/hand-inspection.json
```

安装和启动前提见 [正常游戏加载](live-game.md)。旧进程不会热加载新 DLL；旧 Mod 不支持 `inspect_hand`，须先重启。此调用不要求 `expected_state`，不改变已有动作令牌，也不出现在 `available_actions` 中。诊断时可加 `--raw`，取得原始响应及采样前基础观察的 `snapshot_id`；默认玩法输出省略它。

## 格式

结果包含顶层 `hand` 数组，顺序与基础观察的手牌一致，ID 也保持一致。每张牌复用 [基础手牌字段](observation.md#手牌与身份)，新增：

| 字段 | 含义 |
| --- | --- |
| `description` | 当前完整牌面正文，保留换行和动态预览数值，移除颜色、字体等格式标记 |
| `hover_tips[]` | 游戏为这张牌生成的悬停解释框，按 UI 去重后的顺序返回 |
| `hover_tips[].title` | 解释标题；原提示无标题时为 `null` |
| `hover_tips[].description` | 解释正文；卡牌预览提示使用该预览卡的名称及正文 |

资源图标转为 `<Energy>`、`<Star>`；尚无明确语义映射的资源保留为 `<Icon:资源文件名>`，不静默丢弃。未知或锁定牌的 `description`、`hover_tips` 为 `null`，不补真实内容。正常可读的空手牌返回 `hand: []`。

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
python3 scripts/verify_hand.py --ipc-dir .tmp/live/ipc --output .tmp/live/hand-inspection.json --report .tmp/live/hand-inspection-check.json
```

它核对详情和基础观察的 ID、完整正文及提示结构、说明适用范围，以及读取前后观察令牌一致。需要测试英语作用域、缓存、关键词和动态数值时，在独立实例使用 `scripts/run_roundtrip.py --windowed --capture --check-hand`；该标志仅供仓库创建的铁甲战士测试战斗使用，不用于正式游戏。实施与验证记录见 [手牌详情实施记录](../research/2026-10-29-hand-inspection-plan.md)。
