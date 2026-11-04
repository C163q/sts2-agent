# 遗物详情 JSON

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作 `inspect_relics` 与同名 [MCP 工具](mcp.md)用于一次只读查看当前遗物栏中已显示的遗物，以英语返回原生正文和附带解释。支持无遮挡战斗及原生可查看的战斗背景（例如[建筑师](run-ending.md)），以及可读顶部栏的非战斗页面，包括事件、先古之民、火堆、宝箱、奖励、商店、选牌和地图；结算中仍须遗物栏实际可见，可用于查看已持有的添水等遗物说明。MCP full 与文件客户端返回相同的玩法 JSON；默认使用[default 预设](mcp.md#输出预设)省略普通空值。

地图覆盖战斗及牌组／三类牌堆浏览时也可查看仍然显示的遗物；顶栏和交互边界见[基础观察](observation.md#mcp-输出预设)。


成功结果的 `scene/screen` 来自本次快照，表示当前房间与覆盖状态，统一规则见[MCP 上下文](mcp.md#成功结果的场景上下文)。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启，在无遮挡战斗或暴露的商店中执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_relics > .tmp/live/relic-inspection.json
```

MCP 调用 `inspect_relics()` 默认返回省略普通空值的完整详情，也可传入以下预设与筛选参数，成功时刷新状态令牌；完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。原生文件协议支持内部参数 `level: full/summary`，省略为 full；现有 CLI 入口不提供遗物预设或筛选选项。读取不需要动作令牌，可用时列入 `available_actions`，不执行游戏动作。默认客户端移除控制信息；加 `--raw` 保留原始响应和状态令牌。

## MCP 参数

筛选只控制 Python 输出；summary 在原生端跳过悬停正文读取，不扩大游戏端的展示范围。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `default` | `default` 保留完整内容并省略普通空值和为 false 的图标置灰／发光字段；`full` 保留空值及 false；`summary` 仅保留 `name/counter/melted/grayed_out/pulsing` 静态字段并按 default 精简 |
| `relic_indices` | 省略 | 当前未筛选 `inspect_relics` 列表从 0 开始的下标数组；省略或 `null` 返回全部，`[]` 返回空列表，重复值去重，结果保持遗物栏顺序 |

```json
{"preset":"summary","relic_indices":[1,2,3]}
```

遗物当前没有稳定 ID，因此使用 `relic_indices`；同次稳定画面的未筛选列表与基础观察的 `top_bar.relics` 使用相同展示顺序；不能在遗物增减、重排或可见性改变后直接复用。summary 与 full/default 使用相同的展示范围。可见计数为 0 时保留 0，不可读为 `null`；旧响应缺少静态状态字段时不补值；原生 summary 读取需要与当前 MCP 匹配的 Mod。

传入非 null 筛选数组时，所有预设的顶层 `relic_indices` 与返回的 `relics` 一一对应，保留它们在未筛选列表中的原始位置。例如请求 `[3,1,3]`，结果映射为 `[1,3]`；`[]` 返回空映射。full/default 的 `hover_tips[].relic_indices` 同样指向**未筛选列表**，只保留命中的原位置并删除无关联解释；summary 不返回正文、`hover_tips` 或悬停缺失 note。省略或 null 筛选不增加顶层映射；default/summary 省略普通空值，以及 `grayed_out:false`、`pulsing:false`。`melted:false` 仍保留，表示蜡质遗物尚未熔化。

数组元素仅接受 0 至 2147483647 的整数，拒绝布尔值、浮点数、字符串、`null` 与未知参数。超出本次可读列表范围的下标按请求首次出现顺序合并，有效结果照常返回：

```json
{"errors":[{"code":"relic_indices_out_of_range","relic_indices":[80,70]}]}
```

带此 `errors` 时 MCP `isError:false`，没有无效下标时省略它。所有预设及空筛选都先验证完整底层详情，不用筛选掩盖坏数据；成功读取仍刷新动作许可。非法参数不发往游戏或清除旧许可，原生错误保持顶层 `error`，不转换为下标缺失。实现与实测范围见[遗物预设记录](../research/2026-11-02-relic-presets.md)。

## 格式

下表为空值保留时的字段语义，对应底层文件或 MCP full。

| 字段 | 内容 |
| --- | --- |
| `relics[]` | 当前已显示的遗物，沿用遗物栏顺序 |
| `relics[].name` | 图标身份对应的英语名称 |
| `relics[].counter` | 当前已显示计数标签；不可见或不可解析为整数时为 `null`，可见的 0 保留为 0 |
| `relics[].melted` | 蜡质遗物未熔化为 `false`、已熔化为 `true`；非蜡质不适用，或图标不可读时为 `null`。依据实际显示的蜡质效果和熔化着色，普通禁用不表示熔化 |
| `relics[].grayed_out` | 图标实际使用原生置灰着色时为 true，原生普通着色为 false，无法归类的着色为 null；不代表控件无法悬停 |
| `relics[].pulsing` | 实际 shader 的 pulse 参数为 1 时为 true、0 时为 false；缺少对应 shader／uniform 或值无法判断时为 null |
| `relics[].description` | 当前实例的原生英语正文，包括动态值及用尽、熔化等说明；当前不能悬停时为 `null` |
| `hover_tips[]` | 附带的关键词或卡牌解释，以 `title/description` 共同去重 |
| `hover_tips[].relic_indices[]` | 当前未筛选列表的位置，从 0 开始；筛选后通过顶层 `relic_indices` 查找对应条目 |

主正文保留在遗物条目内；重复附带解释集中保存，同名但正文不同的解释分别保留。没有可读条目时返回 `relics: []`；没有额外解释时为 `hover_tips: []`。本调用不包含手牌数值、敌人意图 notes。

例如 Lantern 的正文为 `Start each combat with an additional <Energy>.`，附带 `Energy` 解释；Pen Nib 初始可见计数为 `0`。图标沿用 `<Energy>`、`<Star>` 等文本表示，保留正文换行，去除格式标签。原始响应中的解释位于各遗物的 `hover_tips`，文件客户端将它们合并为上述共享结构。

## 读取边界

遗物来自实际 `NRelicInventory.RelicNodes`，不遍历玩家模型中未展示的遗物。必须有实际显示的 holder、遗物节点和带纹理的图标；隐藏、透明、零缩放、实际被父控件裁剪或待删除的条目排除。条目、计数和图标状态不按视口坐标截断；整个遗物栏隐藏或顶部栏不可读时返回带具体公开原因的 `illegal_action`，已有动作许可按共用恢复规则保留。计数与状态只读取实际显示的标签、着色和 shader，不从模型 Status、IsUsedUp 或触发准备旗标补齐，也不刷新画面。熔化、置灰、激活发光独立表达。任意像素遮挡仍无法精确判断。

展示与悬停分开判断。普通 `RelicStatus.Disabled` 只是图标变灰，仍可查看说明；控件须满足原生启用／`AllowFocusWhileDisabled` 条件，且鼠标或控制器焦点至少有一个入口。已显示但当前不能悬停时，full 保留静态字段、`description:null`，不生成悬停解释，并附 `notes.hover_tips_unavailable`。其中 `sources` 使用未筛选列表地址，例如 `relics.2`，筛选后只保留命中条目；default 按公共规则省略正文空值，summary 跳过说明并不生成这条 note。没有额外关键词与提示格式异常不等同于不能悬停。
基础观察的 `top_bar.relic_count` 独立计数持有条目；禁用或临时隐藏某个条目不会将其当作失去遗物，也不保证它可由本工具查看。字段及摘要预设见[观察说明](observation.md#mcp-输出预设)。

正文和附带说明取自已显示遗物实例的 `RelicModel.HoverTips`，与原生悬停入口相同。只输出原生悬停正文，不附送风味文本、内部计数、获取楼层、未来触发结果或概率推演。不会调用 `OnFocus`、触发动画、切换语言、设置目标或打开遗物检查页。格式化对 `EnergyVar.ColorPrefix` 的临时修改在 `finally` 恢复，未知提示类型整次报错，不静默丢弃。

## 验证

扩大的非战斗查看范围及动作列表一致性见[可用工具修复记录](../research/2026-11-02-available-actions-fix.md)。

文件和真实 stdio MCP 分别使用 `verify_relics.py` 与 `verify_mcp_relics.py`。运行脚本时避免手动改变游戏：

```sh
python3 -m tests.game.verifiers.verify_relics --ipc-dir .tmp/live/ipc --output .tmp/live/relic-inspection.json --report .tmp/live/relic-inspection-check.json
```

两份脚本共享静态字段、上下文、不可悬停说明和提示原下标关联断言，并检查重复读取一致、前后基础观察令牌不变及文件／MCP 输出一致。完整专项套件见[图形测试](gui-testing.md)，图标状态、筛选映射、错误续接和实际熔化的证据见[实施记录](../research/2026-11-04-relic-inspection-implementation.md)。令牌只覆盖已导出的基础观察，不是全部游戏内部状态的版本。

独立中文实例可使用 `scripts/run_roundtrip.py --windowed --capture --check-relics` 准备原生遗物获取及读取检查，不能为正式游戏设置测试标志。历史样本和检查数量见[遗物实施记录](../research/2026-10-29-relic-inspection-plan.md)及[MCP 实施记录](../research/2026-10-29-mcp-relic-inspection.md)，后续预设、熔化及非战斗范围见上文专项记录；全部遗物、第三方悬停和多人尚未穷举验证。
