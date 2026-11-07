# 休息处

页面主体的visible／not_ready／covered及部分内容提示遵循[共用展示状态](observation.md#页面主体的展示状态)，按钮可操作性另行判断。

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

工具点击当前原生休息处按钮，选择与实际效果由游戏执行；不自动选路。

下文示例以公开 MCP full 为准；MCP 工具接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

## 观察与详情

`get_observation()` 返回 `scene: "rest_site"` 和 `rest_site`。基础观察的full/default/summary共用静态火堆格式，包含当前显示的标题、选项名称、启用状态和前进按钮，省略顶层及各选项description。例如：

```json
{
  "scene": "rest_site",
  "rest_site": {
    "status": "visible",
    "prompt": "What shall I do?",
    "options": [
      {"id": "HEAL", "text": "Rest", "enabled": true},
      {"id": "SMITH", "text": "Smith", "enabled": true}
    ],
    "proceed": null
  }
}
```

这是字段节选，完整返回还包含顶栏等公共观察。`id` 使用该次实际选项的原生标识，传给动作的字段名为 `option_id`；不要把选择卡牌页面的按钮 ID 或奖励 ID 传入。

`inspect_rest_site({preset?, option_ids?})` 返回同次快照的scene、screen和rest_site。default/full保留画面当前已展开的顶层description，并为可悬停的选项提供完整description，例如恢复生命的实时数值、追加奖励、锻炼剩余次数或不能锻造的原因。说明来自同一原生按钮的动态文本，使用已有选项，不重新生成或预读挖掘所得遗物。成功详情可用于后续动作，令牌规则见[MCP调用语义](mcp.md#调用和错误语义)。

| preset | 内容 |
| --- | --- |
| full | 完整说明和普通null，包括暂不可悬停选项的description:null |
| default | 默认；完整内容按共用规则省略普通null |
| summary | status、prompt、options的id/text/enabled及proceed，省略全部description与悬停note，并应用default空值规则 |

option_ids按当前显示列表的原生字符串ID精确筛选，例如`["HEAL","SMITH"]`。省略或null取全部，[]取空；去重并保持原生顺序，未找到的ID合并到errors中的option_ids_not_found。ID须为不全为空白、最多128字符的字符串。prompt和proceed仍描述当前页面，options:[]保留；完整响应先校验再摘要／筛选，空筛选也会检查坏响应。

普通灰置选项仍可悬停，保留说明和enabled:false。显示但无法悬停的选项保留静态字段，full提供description:null，default省略该null；notes.hover_tips_unavailable.sources通过`rest_site.options.<原生ID>`定位。筛选同步裁剪关联note，summary省略悬停note。

页面可读性与操作就绪分开：说明淡出、队列或按钮暂不可执行时，详情仍可读取实际显示的内容，enabled按动作条件计算。选项不按窗口视口裁剪，真正隐藏、透明或被父控件裁剪的内容仍排除。原生前进按钮用移出屏幕实现隐藏，仍按实际显示判断；单个动作继续核对目标是否可交互。详情与available_actions共用InspectionUnavailableReason，公开无火堆、地图／牌组／选牌／奖励覆盖、预览及过渡的具体原因。

地图、选牌、奖励、详情页面或过渡遮挡时，基础观察的rest_site.status为covered，其余静态字段为null；详情拒绝。proceed仅在实际显示时提供text、enabled。已识别但未适配的活动保留名称及可悬停说明，enabled为false。MCP会拒绝上下文与内容矛盾、缺少说明来源等坏响应并清除许可；纯读取的明确拒绝保留此前已有许可，首次失败不会生成许可。

## 选择与前进

`choose_rest_option({"option_id":"HEAL"})` 点击一个当前启用的原生选项。每次只执行一次，返回[精简动作回执](mcp.md#动作返回格式)；成功读取及动作结果可按[MCP 动作许可](mcp.md#调用和错误语义)续接下一步。按钮动画、说明文字淡出、选项执行与原生界面刷新完成后才返回可继续行动的结果；遇到需要选择、奖励或未支持页面时停在对应交互边界，不等待依赖后续输入的父任务。

明确点击前拒绝保留已有操作许可，可直接改用合法动作；原因区分无火堆、覆盖页面、等待、未知或已消耗ID、禁用及不支持的选项。过期状态或交互后结果不明仍须读取。按钮enabled、available_actions和执行共用动作／目标判断，读取使用独立可读性判断。

锻炼／填火的可见遗物计数变化通过relic_counter_changed反馈，格式与显示边界见[期间事件](end-turn.md#事件语义)。普通休息记录生命变化，挖掘记录公开取得的遗物及附带效果；仅打开锻造／烹饪选牌时events可为空，实际牌组变化在后续确认中记录。

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
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_rest_site --scenario smith --report .tmp/rest-check/smith.json
```

报告和截图目录须全新；仅用于新建隔离实例，会真实选择、取消和升级。其他夹具及实际验证范围见[调研与验证记录](../research/2026-10-31-rest-site.md)。
