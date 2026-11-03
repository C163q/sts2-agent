# 当前界面悬停说明 JSON

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作 `inspect_ui` 与同名 [MCP 工具](mcp.md)只读返回当前可见顶栏、战斗通用入口、资源图标和空充能球槽的英语悬停说明。不移动鼠标、不打开窗口、不切换游戏语言。手牌、药水、遗物、能力、意图与已有球的效果使用各自的专门查看工具。

## 调用与参数

按[正常游戏加载](live-game.md)构建、安装并重启游戏后，文件客户端无额外参数：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_ui > .tmp/live/ui-inspection.json
```

MCP 支持以下调用：

```text
inspect_ui(preset="summary")
inspect_ui(sources=["top_bar.hp", "top_bar.gold"])
inspect_ui(preset="full", sources=["player.energy"])
```

| 参数 | 行为 |
| --- | --- |
| `preset` | 默认 `default`，按[公共预设](mcp.md#输出预设)省略普通空值；`full` 保留空值；`summary` 在 default 基础上省略每条提示的 `description`，保留标题、来源和上下文 |
| `sources` | 按提示来源路径精确匹配。省略表示全部，`[]` 表示不返回提示；重复值去重，提示与来源保持原生顺序。共享提示只保留匹配的来源；不会将 `top_bar` 当作路径前缀 |

未匹配来源集中返回 `errors:[{"code":"ui_sources_unavailable","sources":[...]}]`，其余匹配提示仍正常返回；可能是来源拼写错误，也可能是当前页面没有该入口或不允许悬停。未知参数、非法预设、非字符串或空字符串来源等返回 `invalid_request`。

summary 可先列出可查询来源，再用 default 加 sources 读取所需正文。完整原生响应先校验，再筛选和摘要；筛选不会掩盖未选中数据的格式错误，也不会改变原生状态令牌。

## 返回格式

成功结果包含 `scene`、`screen`、`hover_tips`，场景与页面遵循[统一上下文](observation.md#场景上下文)，与同一画面的基础观察一致。选牌切回战场时另有 `notes.selection`，提示返回选择界面完成选牌。以下仅为单条帮助的结构片段，完整实测示例见[本轮核验与修复记录](../research/2026-11-03-inspect-ui-review.md#修复后示例与验证入口)：

```json
{
  "scene": "event",
  "screen": {"status": "visible"},
  "hover_tips": [
    {
      "title": "Hit Points (HP)",
      "description": "If you run out of HP, you die.",
      "sources": ["top_bar.hp", "top_bar.max_hp"]
    }
  ]
}
```

- 标题与正文来自原生悬停帮助，移除颜色、字体标记，保留换行、实际快捷键及 `<Energy>/<Star>` 图标占位符。full 保留 `title:null`，default/summary 省略无标题字段。
- sources 关联完整基础观察中的字段，不重复字段值；不随观察摘要合并生命／能量字段而改名。顶栏 HP 使用 `top_bar.hp/top_bar.max_hp`，头像与进阶帮助使用 `top_bar.ascension`；战斗资源如 `player.energy` 沿用对应来源。
- 同标题同正文合并，来源去重；同标题不同正文分别保留。空球槽来源如 `player.orb_slots.4`，下标从 0 起，对应完整可读栏位；多个空槽的共同帮助只输出一次。
- 无可用提示或 sources 筛选为空时保留 `hover_tips:[]`；不可读页面返回结构化错误，不用空数组表示失败。不包含资源当前值、动作 transition 或 available_actions；可用操作由 get_observation 提供。
- MCP 的 JSON 文本与 structuredContent 一致。成功查看刷新内部许可；参数错误与明确读取拒绝保留已有许可，坏响应、超时、异常或取消仍清除许可。首次失败不生成许可。完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。文件客户端 `--raw` 另保留通信包装与 snapshot_id。

## 可见范围

顶栏与战斗区域独立判断。事件、火堆、商店、奖励、先古之民、宝箱、地图／牌组／牌堆覆盖、选牌页、建筑师及结算中，只要顶栏按原生 UI 仍可见可读，就提供对应帮助；不会因此穿透读取被遮住的战斗资源。主菜单、模态遮挡和过渡等没有可读区域的情况返回 illegal_action，可用性以 get_observation.available_actions 为准。

顶栏包括可悬停的头像／进阶、生命、金币、当前房间、楼层、可见首领、地图、牌组与设置入口。头像遵循原生 ShowTip，不补出隐藏首领。战斗区域包括能量、星星、抽牌／弃牌／消耗堆入口、结束回合与空充能球槽；牌堆须已绑定，结束回合遵循玩家准备状态，完整球栏及空槽须可读可悬停。

固定入口仍按可见性、视口与裁剪筛选；禁用控件按原生 AllowFocusWhileDisabled 决定是否能提供帮助。这些入口不属于可滚动候选列表，不补齐隐藏图标。地图、牌组与牌堆只提供入口帮助，不读取其中内容或顺序；不添加原生没有的格挡帮助。

## 验证

当前完整跨场景回归为 [gui_suite_ui_context.json](../../tests/game/data/gui_suite_ui_context.json)，通过[图形测试套件](gui-testing.md)执行；通关终章通过独立实例的 verify_ui_context.py --scenario ending 验证，不放入复用套件。

只读脚本可核对当前游戏；运行期间避免手动改变场景：

```sh
python3 -m tests.game.verifiers.verify_ui --ipc-dir .tmp/live/ipc --output .tmp/live/ui-inspection.json --report .tmp/live/ui-inspection-check.json
```

独立实例的 `run_roundtrip.py --windowed --capture --check-ui` 另检查原生可见性、英语文本和缓存不变；不用于正式游戏。早期实现见[实施记录](../research/2026-10-29-ui-inspection-plan.md)，充能球边界见[球槽核对](../research/2026-11-01-capacity-and-orbs.md)。历史未测项不直接代表当前验证范围。
