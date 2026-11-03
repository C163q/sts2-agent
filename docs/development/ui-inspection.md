# 当前界面悬停说明 JSON

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作 `inspect_ui` 与同名 [MCP 工具](mcp.md)只读返回当前无遮挡战斗画面上可见入口、资源图标和空充能球槽的英语悬停说明。不触发鼠标悬停、不打开窗口、不切换游戏语言。工具分工见 [范围核查](../research/2026-10-29-ui-hover-tip-audit.md)。

## 读取与格式

按 [正常游戏加载](live-game.md) 构建、安装并重启游戏，进入无遮挡的战斗后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_ui > .tmp/live/ui-inspection.json
```

结果包含 `scene` 和共享提示数组 `hover_tips`。以下是独立中文游戏实例中实际读取的一条提示；它不是用户当前战斗的完整采样：

```json
{
  "scene": "combat",
  "hover_tips": [
    {
      "title": "Energy",
      "description": "Your current Energy ( <Energy>) count. Cards require <Energy> to play, indicated in the top left corner.",
      "sources": ["player.energy", "player.max_energy"]
    }
  ]
}
```

- `title` 和 `description` 来自游戏的悬停提示文本，移除颜色和字体标记，保留换行、实际快捷键和资源图标占位符，例如 `<Energy>`、`<Star>`。无标题时 `title` 为 `null`。
- `sources` 是关联的基础观察字段路径，不重复输出字段值。同标题同正文合并，来源去重并保留首次出现顺序；同标题不同正文不合并。
- 不附带手牌数值或敌人意图的 `notes`。没有可用提示时数组为 `[]`；不可读界面返回结构化错误，不以空集合表示读取失败。
- 加 `--raw` 时保留 `id/ok/state` 和 `state.snapshot_id`。无须提供动作令牌，读取工具可用时列入 `available_actions`。
- MCP full 返回相同玩法格式；默认 default 省略普通空值，如无标题的 title，规则见[公共预设](mcp.md#输出预设)。`structuredContent` 与 JSON 文本一致；成功查看会刷新状态令牌，完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。

## 覆盖与条件

当前包含头像及进阶、顶栏生命、金币、房间类型、楼层、首领、地图入口、主牌组入口、设置入口、能量、星星、抽牌/弃牌/消耗牌堆入口和结束回合。按当前节点可见性、视口和裁剪筛选，隐藏入口不补齐。禁用入口遵循游戏的 `AllowFocusWhileDisabled` 规则；禁用且不允许聚焦时不提供提示。头像须满足游戏 `ShowTip` 条件；牌堆须已绑定；结束回合的提示遵循玩家当前是否准备结束回合的条件。

空充能球槽使用原生通用帮助，同文合并，`sources` 如 `player.orb_slots.4`，下标对应[基础观察](observation.md#玩法字段)的槽位。只有完整栏位可读且对应空槽可悬停时提供；已生成球的效果通过 [inspect_combatants](combatant-inspection.md) 查看，不在这里重复。

药水、遗物、powers 和敌人当前意图解释均不包含；powers 与当前意图通过 [战斗对象详情](combatant-inspection.md) 一起查看，药水与遗物分别使用 [药水详情](potion-inspection.md) 和 [遗物详情](relic-inspection.md)。手牌效果使用 `inspect_hand`。地图、牌组、牌堆这里只返回入口说明，不返回具体内容或抽牌顺序；不添加游戏中不存在的格挡悬停说明。

地图、普通非战斗房间、菜单覆盖和过渡期间返回 `illegal_action`。原生可查看的战斗背景（例如[建筑师](run-ending.md)）也可提供当前可见提示，不要求战斗仍在进行；当前可用性以观察的 `available_actions` 为准。其他版本和其他 Mod 新增的图标或自定义提示没有自动兼容保证。

## 验证

下面的脚本只读取当前游戏，不执行动作；运行期间应避免手动改变场景：

```sh
python3 -m tests.game.verifiers.verify_ui --ipc-dir .tmp/live/ipc --output .tmp/live/ui-inspection.json --report .tmp/live/ui-inspection-check.json
```

脚本检查 `get_state → inspect_ui → get_state` 的令牌一致、提示结构和去重、来源字段存在及查看边界。独立测试实例可用 `scripts/run_roundtrip.py --windowed --capture --check-ui` 启用额外的游戏内可见性、英语文本和缓存检查；该标志不用于正式游戏。早期独立／正式战斗的样本及当时未覆盖场景见[实施记录](../research/2026-10-29-ui-inspection-plan.md)，后续充能球范围见[球槽核对](../research/2026-11-01-capacity-and-orbs.md)。历史记录中的未测项不能直接视为当前全部验证范围。
