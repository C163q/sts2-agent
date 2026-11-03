# 遗物详情 JSON

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作 `inspect_relics` 与同名 [MCP 工具](mcp.md)用于一次只读查看当前遗物栏中可见、可悬停的遗物，以英语返回原生正文和附带解释。支持无遮挡战斗及原生可查看的战斗背景（例如[建筑师](run-ending.md)），以及可读顶部栏的非战斗页面，包括事件、先古之民、火堆、宝箱、奖励、商店、选牌和地图；结算中仍须遗物栏实际可见且可悬停，可用于查看已持有的添水等遗物说明。MCP full 与文件客户端返回相同的玩法 JSON；默认使用[default 预设](mcp.md#输出预设)省略普通空值。

地图覆盖战斗及牌组／三类牌堆浏览时也可查看仍然可悬停的遗物；顶栏和交互边界见[基础观察](observation.md#mcp-输出预设)。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启，在无遮挡战斗或暴露的商店中执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_relics > .tmp/live/relic-inspection.json
```

MCP 调用 `inspect_relics()` 默认返回完整详情，也可传入以下预设与筛选参数，成功时刷新状态令牌；完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。底层文件调用仍无参数，不需要动作令牌，可用时列入 `available_actions`，不执行游戏动作。默认客户端移除控制信息；加 `--raw` 保留原始响应和状态令牌。

## MCP 参数

以下参数只控制 Python 输出，不扩大游戏端的读取范围。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `preset` | `default` | `default` 保留完整内容并省略普通空值；`full` 保留原有空值；`summary` 的遗物条目仅保留 `name/counter/melted`，与基础观察的字段一致 |
| `relic_indices` | 省略 | 当前未筛选 `inspect_relics` 列表从 0 开始的下标数组；省略返回全部，`[]` 返回空列表，重复值去重，结果保持遗物栏顺序 |

```json
{"preset":"summary","relic_indices":[1,2,3]}
```

遗物当前没有稳定 ID，因此使用 `relic_indices`；这些下标不保证与基础观察的 `top_bar.relics` 相同，也不能在遗物增减、重排或可见性改变后直接复用。summary 沿用本调用可见、可悬停的遗物范围，不扩大为其他图标。可见计数为 0 时保留 0，不可读为 `null`；兼容旧 Mod 时不补原本缺失的 `melted`。

传入筛选时，顶层 `relic_indices` 与返回的 `relics` 一一对应，保留它们在未筛选列表中的原始位置。例如请求 `[3,1,3]`，结果映射为 `[1,3]`。full 的 `hover_tips[].relic_indices` 仍指向**本次返回数组**，同步重新编号并删除无关联解释；summary 不返回正文或 `hover_tips`。省略筛选时不增加顶层映射，显式 full 与原格式兼容；default 下普通遗物的 `melted:null` 和不可读计数可省略，summary 同样省略这些普通空值。

下标仅接受 0 至 2147483647 的整数，拒绝布尔值、浮点数、字符串、`null` 与未知参数。超出本次可读列表范围的下标按请求首次出现顺序合并，有效结果照常返回：

```json
{"errors":[{"code":"relic_indices_out_of_range","relic_indices":[80,70]}]}
```

带此 `errors` 时 MCP `isError:false`，没有无效下标时省略它。所有预设及空筛选都先验证完整底层详情，不用筛选掩盖坏数据；成功读取仍刷新动作许可。非法参数不发往游戏或清除旧许可，原生错误保持顶层 `error`，不转换为下标缺失。实现与实测范围见[遗物预设记录](../research/2026-11-02-relic-presets.md)。

## 格式

下表为空值保留时的字段语义，对应底层文件或 MCP full。

| 字段 | 内容 |
| --- | --- |
| `relics[]` | 当前可见且可悬停的遗物，沿用遗物栏顺序 |
| `relics[].name` | 原生悬停提示的英语名称 |
| `relics[].counter` | 当前屏幕计数标签；不可见或不可解析为整数时为 `null`，可见的 0 保留为 0 |
| `relics[].melted` | 蜡质遗物未熔化为 `false`、已熔化为 `true`；非蜡质不适用，或图标不可读时为 `null`。依据实际显示的蜡质效果和熔化着色，普通禁用不表示熔化 |
| `relics[].description` | 当前实例的原生英语正文，包括原生提供的动态值及用尽、熔化等说明 |
| `hover_tips[]` | 附带的关键词或卡牌解释，以 `title/description` 共同去重 |
| `hover_tips[].relic_indices[]` | 对应本次 `relics` 数组的位置，从 0 开始，仅对本次结果有效 |

主正文保留在遗物条目内；重复附带解释集中保存，同名但正文不同的解释分别保留。没有可读条目时返回 `relics: []`；没有额外解释时为 `hover_tips: []`。本调用不包含手牌数值、敌人意图 notes。

例如 Lantern 的正文为 `Start each combat with an additional <Energy>.`，附带 `Energy` 解释；Pen Nib 初始可见计数为 `0`。图标沿用 `<Energy>`、`<Star>` 等文本表示，保留正文换行，去除格式标签。原始响应中的解释位于各遗物的 `hover_tips`，文件客户端将它们合并为上述共享结构。

## 读取边界

遗物来自实际 `NRelicInventory.RelicNodes`，不遍历玩家模型中未展示的遗物。必须有实际显示的 holder、遗物节点和带纹理的图标，holder 须启用且接受鼠标事件。隐藏、透明或不可悬停的条目排除；遗物清单不再按视口或裁剪矩形位置删条目，避免数量与原生遗物栏脱节。整个遗物栏隐藏或顶部栏不可读时返回 `illegal_action`。数字计数与 melted 仍只读取实际屏幕标签和图标；不可读时保留 null，不用内部数值补齐。任意像素遮挡仍无法精确判断。

基础观察的 `top_bar.relic_count` 独立计数持有条目；禁用或临时隐藏某个条目不会将其当作失去遗物，也不保证它可由本工具查看。字段及摘要预设见[观察说明](observation.md#mcp-输出预设)。

正文和附带说明取自已显示遗物实例的 `RelicModel.HoverTips`，与原生悬停入口相同。只输出原生悬停正文，不附送风味文本、内部计数、获取楼层、未来触发结果或概率推演。不会调用 `OnFocus`、触发动画、切换语言、设置目标或打开遗物检查页。格式化对 `EnergyVar.ColorPrefix` 的临时修改在 `finally` 恢复，未知提示类型整次报错，不静默丢弃。

## 验证

扩大的非战斗查看范围及动作列表一致性见[可用工具修复记录](../research/2026-11-02-available-actions-fix.md)。

运行脚本时避免手动改变游戏：

```sh
python3 -m tests.game.verifiers.verify_relics --ipc-dir .tmp/live/ipc --output .tmp/live/relic-inspection.json --report .tmp/live/relic-inspection-check.json
```

脚本检查重复读取一致、前后基础观察令牌不变、名称和计数与基础观察按顺序对应、共享解释去重及下标有效。令牌只覆盖已导出的基础观察，不是全部游戏内部状态的版本。

独立中文实例可使用 `scripts/run_roundtrip.py --windowed --capture --check-relics` 准备原生遗物获取及读取检查，不能为正式游戏设置测试标志。历史样本和检查数量见[遗物实施记录](../research/2026-10-29-relic-inspection-plan.md)及[MCP 实施记录](../research/2026-10-29-mcp-relic-inspection.md)，后续预设、熔化及非战斗范围见上文专项记录；全部遗物、第三方悬停和多人尚未穷举验证。
