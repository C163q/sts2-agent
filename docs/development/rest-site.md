# 休息处

适用于 Mod `0.34.1`、MCP server `0.29.1`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。工具点击当前原生休息处按钮，选择与实际效果由游戏执行；不自动选路。

## 观察与详情

`get_observation()` 返回 `scene: "rest_site"` 和 `rest_site`。基础观察包含当前可见标题、选项名称与灰置状态；只有当前画面已展开的说明才放在 `description`，否则为 `null`。例如：

```json
{
  "scene": "rest_site",
  "rest_site": {
    "status": "visible",
    "prompt": "What shall I do?",
    "description": null,
    "options": [
      {"id": "HEAL", "text": "Rest", "enabled": true},
      {"id": "SMITH", "text": "Smith", "enabled": true}
    ],
    "proceed": null
  },
  "available_actions": ["choose_rest_option", "inspect_potions", "inspect_map", "inspect_rest_site"]
}
```

这是字段节选，完整返回还包含顶栏等公共观察。`id` 使用该次实际选项的原生标识，传给动作的字段名为 `option_id`；不要把选择卡牌页面的按钮 ID 或奖励 ID 传入。

`inspect_rest_site()` 返回当前休息处状态，并为每个可见选项增加 `description`，例如恢复生命的实时数值、附加奖励说明、锻炼剩余次数或不能锻造的原因。灰置选项依然可以查看；说明来自同一按钮实际悬停使用的动态文本，不重新生成选项或预测挖掘所得遗物。成功详情可用于后续动作，令牌规则见[MCP 调用语义](mcp.md#调用和错误语义)。

地图、选牌、奖励、详情页面或过渡遮挡休息处时，`rest_site.status` 为 `covered`，其余字段为 `null`；隐藏内容不能查看或点击。`proceed` 仅在实际显示时提供 `{text, enabled}`。灰置、隐藏和已经消失的选项不能执行。已识别但尚未适配的选项保留名称与说明，`enabled` 为 `false`。

## 选择与前进

`choose_rest_option({"option_id":"HEAL"})` 点击一个当前启用的原生选项。每次只执行一次，返回[精简动作回执](mcp.md#动作返回格式)；成功读取及动作结果可按[MCP 动作许可](mcp.md#调用和错误语义)续接下一步。按钮动画、说明文字淡出、选项执行与原生界面刷新完成后才返回可继续行动的结果；遇到需要选择、奖励或未支持页面时停在对应交互边界，不等待依赖后续输入的父任务。

| 原生 ID | 行为 |
| --- | --- |
| `HEAL` | 休息立即按原生规则恢复生命，可能被遗物追加后续奖励；不能撤销已发生的恢复 |
| `SMITH` | 打开牌组升级选择，支持取消、升级预览和确认 |
| `DIG` | 挖掘并获得原生抽取的遗物，其后续选择或奖励单独处理 |
| `LIFT` | 锻炼，增加壶铃的累计次数 |
| `KINDLE` | 给南瓜蜡烛填火 |
| `COOK` | 选两张牌并确认移除，随后增加最大生命；选牌可以取消 |
| `CLONE`、`HATCH` | 执行当前原生复制或孵化选项 |

只报告实际存在的选项，不按遗物清单推测按钮。多人 `MEND` 目标流程未接通；动作目前限本地单人或游戏的假多人模式。未穷举第三方选项。

没有帐篷时，一次成功选择后原生清空剩余选项并熄火；有 Miniature Tent 时，移除刚选过的选项并重建剩余按钮，同一个选项不能凭旧观察重复执行。剩余选项按需观察或通过 `inspect_rest_site` 查看，是否能够前进以当前 `available_actions` 为准。`proceed()` 点击休息处已显示且启用的原生前进按钮，打开地图，不替模型选择剩余选项。查看地图仍使用 `inspect_map()` / `close_map()`；查看或关闭的成功结果可以继续操作当前界面。

## 锻造与烹饪选牌

复用[选牌工具](card-selection.md)。锻造返回 `selection.type: "deck_upgrade"`；`inspect_selection()` 查看完整可浏览候选，`select_card(card_id)` 选择一张。达到原生选择数量后进入升级预览；`upgrade_previews` 数组中的 `before` / `after` 使用同一个原牌 ID，预览克隆不是新的候选。只提供已显示的预览；多牌预览未显示的升级前牌面字段保持未知。预览期间 `cards` 为空，不能点击底层网格。

- `selection_option({"option_id":"cancel_preview"})`：退出当前预览，回候选列表并清空已选项。
- `selection_option({"option_id":"cancel"})`：退出整个可取消的选择，返回休息处，不消耗此次机会。
- `selection_option({"option_id":"confirm"})`：确认已显示的选择，才进行实际升级。

所有按钮须以本次 `selection.options` 的启用状态为准。烹饪沿用 `deck` 多选和移除预览，确认前不删除实际牌。若原生规则直接跳过选择，工具等待真实后续流程，不人为创建候选。

## 验证入口

先按[隔离运行指南](roundtrip.md)准备独立实例；运行：

```sh
python3 scripts/run_roundtrip.py --windowed --rest-scenario smith
```

另一终端执行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_rest_site.py --scenario smith --report .tmp/rest-check/smith.json
```

报告和截图目录须全新；仅用于新建隔离实例，会真实选择、取消和升级。其他夹具及实际验证范围见[调研与验证记录](../research/2026-10-31-rest-site.md)。
