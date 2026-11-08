# 宝箱房

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

当前支持实际单人宝箱，点击原生按钮完成开箱和领取，不自动前进或选路。

含 null 的字段说明与示例按 full 表达；默认输出的空值处理见[公共预设](mcp.md#输出预设)。可见宝箱房的 `relic:null` 在 default 和 get_observation summary 中均保留，表示当前没有展示可领取遗物；covered 时仍省略，不推断未开箱或被覆盖的隐藏内容。

页面主体的展示进度见[共用展示状态](observation.md#页面主体的展示状态)，按钮启用状态按当前操作条件判断。

## 观察与详情

`get_observation()` 返回 `scene: "treasure"` 及 `treasure`，例如未开宝箱时：

```json
{
  "scene": "treasure",
  "treasure": {
    "status": "visible",
    "chest": "closed",
    "relic": null,
    "proceed": null
  }
}
```

这是字段节选，完整观察还包含顶栏等公共字段。`chest` 为 `closed`、`opening` 或 `open`，不表示未来会掉落什么。只有原生遗物图标已经显示时，`relic` 才提供 `{name, enabled}`；未开箱不读取同步器提前生成的隐藏内容。基础观察不附送遗物效果。

`inspect_treasure()` 只读当前暴露的宝箱房，支持 `preset:default/full/summary`，默认 default。full/default 为可悬停遗物提供 `description` 与 `hover_tips`；summary 沿用基础观察的静态宝箱格式，保留箱子状态、遗物 name/enabled 及前进按钮。地图、选牌、额外奖励或其他页面覆盖时，`treasure.status` 为 `covered`，`chest`、`relic`、`proceed` 全为 `null`，详情不可用。成功详情可用于后续动作，令牌规则见[MCP 调用语义](mcp.md#调用和错误语义)。多人共享遗物投票尚未适配，不能由该动作自动代选。

明确读取拒绝保留已有操作许可，首次失败仍须取得有效观察。错误会说明无宝箱房、地图／牌组／选牌／奖励页覆盖或过渡等原因，与可用工具列表共用条件。详情成功必须为 scene:treasure、screen:{status:visible}；矛盾内容返回 transport_error 并清除许可，完整校验后才应用预设。

已显示遗物不可悬停时仍返回 name/enabled；full 为 description:null、hover_tips:[]，并通过 notes.hover_tips_unavailable.sources 中的 treasure.relic 说明。default 省略空正文，保留 note；summary 省略悬停内容和该 note。遗物显示读取保留隐藏、透明和容器裁剪判断，独立于屏幕边缘；点击继续检查屏幕位置与原生可操作状态。静态读取不要求房间已可点击。

## 开箱与领取

`loot_treasure()` 默认点击关闭的宝箱，等待原生金币和额外奖励流程，然后点击唯一单人遗物。金币由游戏在开箱时自动发放；工具不补发奖励。它不点击前进。

如果要先辨认遗物，再决定是否拿取：

1. `loot_treasure({"open_only":true})` 只开箱。
2. 根据观察，按需调用 `inspect_treasure()` 查看遗物说明。
3. 调用 `loot_treasure()` 领取当前可见遗物，或调用 `proceed()` 跳过。

`open_only` 可省略或为布尔值，默认 `false`；已开箱时再次传 `true` 属于不可用动作。已领取或空箱不能再次搜刮。动作沿用[MCP 许可规则](mcp.md#调用和错误语义)：成功读取及完整动作结果可以续接下一动作。首次点击前的明确拒绝保留已有许可；已点击、状态过期、超时或未知结果仍须重新观察。

开箱／领取与 available_actions 共用目标和原因判断；无宝箱、覆盖页、已开箱、无可领取遗物、禁用、离屏或尚未就绪会给出固定说明，明确拒绝可按 recovery 纠正或选择合法动作。例如已开箱再次要求 open_only:true 被拒后，可直接用普通 loot_treasure 领取；已领取再次操作被拒后，可直接 proceed。首次调用仍需已有有效观察。

开箱可能先出现额外奖励；领取遗物可能引发选牌或嵌套奖励。工具停在当前交互边界，返回[精简动作回执](mcp.md#动作返回格式)，后续使用奖励或选牌工具，不等待依赖后续输入的父任务。处理完后若宝箱仍有遗物，须再次显式调用 `loot_treasure()`，先前请求不会在后台继续自动领取。教程与未支持界面返回 `manual_input_required`。

普通完成会等待原生开箱、遗物领取与遗物自身异步效果、相关牌预览及界面刷新。`complete` 确认返回的停止边界；需要选择时不代表遗物的所有后续效果均已完成。宝箱动作接入[共享事件记录](end-turn.md#事件语义)，可返回已经公开的金币、遗物及永久牌组变化；空 events 不表示未发生效果。动作回执不附顶栏，最新数值和持有物按需观察或查看详情。

## 跳过、前进与空箱

`proceed()` 只点击当前暴露且启用的原生 Skip/Proceed。单人开箱后即使未领取遗物，游戏也会在延迟后提供 Skip；领取完成后变为 Proceed。不能在未开箱时强行前进。地图查看沿用 `inspect_map()` / `close_map()`，不旅行；跳过的最终处理沿用原生流程。

白银熔炉使进入后的第一个宝箱房不生成普通金币和遗物；仍须开箱，等待原生空箱流程后即可前进。接口不按遗物名称预判空箱，也不人为创建可领取项目；开箱后 `relic: null` 与当前原生按钮反映实际状态。

## 藏宝图

开箱沿用原生 `DoNormalRewards`，其中已包含 Spoils Map 的任务结算：当前地图节点带有该任务标记时，游戏依次结算牌组中的藏宝图，发放其金币（本版本默认 600）、完成任务并移除对应卡牌，然后继续宝箱流程；不是持有藏宝图就能在任意宝箱兑现。实际金币仍遵守游戏修正，不由工具直接增加。

目标版本先检查 `ShouldGenerateTreasure`；白银熔炉导致普通宝藏不生成时，会直接返回，藏宝图任务也不会在这次开箱结算。工具保留这一原生行为，不额外补发。此组合及藏宝图专项目前只完成源码核对，未进行图形行为验证。

## 验证入口

按[隔离运行指南](roundtrip.md)准备独立实例，再分别运行：

```sh
python3 scripts/run_roundtrip.py --windowed --treasure-scenario basic
```

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_treasure --scenario basic --report .tmp/treasure-check/basic.json
```

报告和截图目录必须全新。测试真实开箱、领取并前进，只能对新建隔离实例运行。其他夹具、证据与未测范围见[调研记录](../research/2026-10-31-treasure.md)。

详情专项可使用 [treasure_inspection_review 套件](../../tests/game/data/gui_suite_treasure_inspection_review.json)，按[图形测试指南](gui-testing.md)传入 --suite 和全新 --output 目录。它验证未开／已开／已领取／空箱、覆盖拒绝与纯读取续接；包含 summary 与基础观察对照，并以双重门控扰动检查不可悬停、禁用、离屏、隐藏、透明和容器裁剪，finally 和局间重置恢复。范围见[实施验证](../research/2026-11-06-treasure-inspection-presets-implementation.md)。

动作现状核验使用 [loot_treasure_review 套件](../../tests/game/data/gui_suite_loot_treasure_review.json)，按图形测试指南指定新输出目录。它覆盖默认／分步／空箱、奖励与选择中断、延迟效果、覆盖及拒绝恢复；验证拒绝后直接领取／继续／选择／旅行及原生未提交证明；真实超时或未知结果仍走保守恢复。范围见[开箱动作修复](../research/2026-11-06-treasure-loot-recovery-implementation.md)。
