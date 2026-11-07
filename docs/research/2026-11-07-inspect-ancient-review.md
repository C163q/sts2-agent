# inspect_ancient 核验与建议

> 当前状态：审阅完成，等待确认修复范围与参数设计，尚未修改工具行为。七类典型场景已核验，31项相关Python检查通过；工具清单仍为38/44项完成，无阻塞。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。[16份完整实测JSON](2026-11-07-inspect-ancient-examples/README.md)包含14份full、一份default，以及一份不支持summary的错误；源码位置、验证过程及未验证范围见[开发核验](2026-11-07-inspect-ancient-development-notes.md)。

## 优先处理的问题

| 问题 | 实际影响与建议 | 核实程度 |
| --- | --- | --- |
| 查看失败的原因不具体 | 不在先古房间、被地图／牌组／选牌／奖励覆盖，均只返回“The requested action is unavailable.”。应分别说明当前情况及可用的返回／查看工具。 | 实际MCP复现 |
| 内容与页面状态缺少交叉校验 | 读取器会接受“先古内容可见，但页面被地图或牌组覆盖”等矛盾返回。应要求成功详情对应当前可见的先古页面，避免错误数据被当作新的有效观察。 | 修改实际原始响应的screen后，四种矛盾状态均被接受；正常游戏未复现这种矛盾响应 |
| 缺少原生致死红框信息 | 瓦库的Distinguished Cape选项带有“最大生命不超过9时致死”的原生警告判断，先古输出没有对应字段。建议基础观察和详情都提供lethal_warning，摘要仅保留true。 | 目标版本源码确认；未构造低最大生命的GUI场景 |
| 显示与悬停的读取边界仍不统一 | 文字、选项和继续按钮仍使用屏幕坐标过滤；详情也没有核对该选项当前能否显示悬停帮助。建议取消读取中的离屏过滤，保留真实隐藏／透明／裁剪判断；无法悬停时保留选项正文，省略帮助并附note。 | 源码确认；正常布局已验证，异常布局与禁用悬停尚未做GUI探针 |

这些问题应先于新增参数处理。重构建议限于先古页面的读取条件、错误原因与悬停判断，以及对应的Python输出校验；继续复用已有上下文、默认空值过滤及事件选项原生流程。

## 当前用途与典型返回

当前仅支持`preset:default/full`，默认default，没有其他参数。返回当前先古之民名称、已显示称号／说明／对话、馈赠选项及其悬停解释，以及继续／前进按钮。建筑师对话由get_observation读取，见[终章接口](../development/run-ending.md)。

| 场景 | 当前返回与示例 |
| --- | --- |
| 对话尚未结束 | 只返回已展示的对话；继续按钮存在时，通过advance_dialogue推进。[完整full](2026-11-07-inspect-ancient-examples/dialogue.full.json) |
| 馈赠已展开 | 通常三个选项，各有id、title、description、enabled、hover_tips。[完整full](2026-11-07-inspect-ancient-examples/choices.full.json) |
| 馈赠引用其他遗物／卡牌 | 悬停解释包含当前角色对应的具体物品，例：Burning Blood→Black Blood，Bash→Break。[完整full](2026-11-07-inspect-ancient-examples/relic-references.full.json) |
| 领取完毕 | options和dialogue为空，proceed显示原生前进按钮。[完整full](2026-11-07-inspect-ancient-examples/obtained.full.json) |
| 刚到达或从浏览页返回 | 可以读取已经显示的内容，但enabled可能暂为false。[到达full](2026-11-07-inspect-ancient-examples/arrival.full.json)、[返回default](2026-11-07-inspect-ancient-examples/returning.default.json) |
| 被其他页面覆盖 | 当前拒绝查看；变牌、卡牌包及嵌套奖励继续由各自工具读取。[选牌覆盖](2026-11-07-inspect-ancient-examples/selection-covered.full.json)、[奖励覆盖](2026-11-07-inspect-ancient-examples/rewards-covered.full.json) |

先古馈赠的效果正文已在选项上展开，所以基础观察也返回description；它与悬停解释的用途不同。[基础观察对照](2026-11-07-inspect-ancient-examples/choices-observation.full.json)保留选项正文、省略hover_tips。

**没有发现查看报错后必须重新观察的问题。**已有许可时，错误查看后可以直接end_turn、close_map或close_card_view；[实际结束回合返回](2026-11-07-inspect-ancient-examples/legal-after-rejection.full.json)。首次调用inspect_ancient也可以成功，不要求预先get_observation。当前enabled为true时，成功详情后可直接选择；页面过渡中应依据最新enabled及可用动作决定后续操作。

## 参数与摘要建议

推荐新增summary，沿用基础观察已有的先古主体：保留名称、称号、说明、已展示对话、选项id／title／description／enabled，以及continue／proceed；省略全部hover_tips。馈赠正文用于判断收益，应当保留。新增致死警告后，summary省略false，default/full保留布尔值。

get_observation的full/default/summary继续共用静态先古格式，与inspect_ancient.summary统一；其顶栏、卡牌选择等仍按各自规则处理。

筛选有两个可行选择：通常只有三项馈赠，可以维持无筛选；也可以像火堆一样加入option_ids，供LLM仅展开某项的悬停解释。推荐后者：

```json
{"preset":"full","option_ids":[0,2]}
```

- 省略或null返回全部；[]返回空options，其余对话、按钮和上下文保留。
- 使用当前options[].id，保留页面原顺序；无须额外位置映射。
- 找不到的ID合并到errors中的option_ids_not_found，匹配项照常返回。
- summary、default、full使用相同筛选规则；悬停不可用note只保留所选项，summary省略此类note。

不建议增加任意字段路径筛选：当前主体已较小，选项筛选和悬停说明开关足以表达主要查看需求。工具现有描述较简洁，新增规则宜放在参数说明中。

以上为待确认建议；当前调用summary仍会得到invalid_request，[实际返回](2026-11-07-inspect-ancient-examples/summary-unsupported.json)。
