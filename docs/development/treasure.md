# 宝箱房

适用于 Mod `0.33.0`、MCP `0.28.0`、Linux 游戏 `v0.107.1` 与 RitsuLib `0.6.10`。当前支持实际单人宝箱，点击原生按钮完成开箱和领取，不自动前进或选路。

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
  },
  "available_actions": ["loot_treasure", "inspect_potions", "inspect_map", "inspect_treasure"]
}
```

这是字段节选，完整观察还包含顶栏等公共字段。`chest` 为 `closed`、`opening` 或 `open`，不表示未来会掉落什么。只有原生遗物图标已经显示时，`relic` 才提供 `{name, enabled}`；未开箱不读取同步器提前生成的隐藏内容。基础观察不附送遗物效果。

`inspect_treasure()` 只读当前暴露的宝箱房，为可见遗物增加 `description` 与 `hover_tips`。地图、选牌、额外奖励或其他页面覆盖时，`treasure.status` 为 `covered`，`chest`、`relic`、`proceed` 全为 `null`，详情不可用。详情不授予动作许可，状态未变时保留已有许可。多人共享遗物投票尚未适配，不能由该动作自动代选。

## 开箱与领取

`loot_treasure()` 默认点击关闭的宝箱，等待原生金币和额外奖励流程，然后点击唯一单人遗物。金币由游戏在开箱时自动发放；工具不补发奖励。它不点击前进。

如果要先辨认遗物，再决定是否拿取：

1. `loot_treasure({"open_only":true})` 只开箱。
2. 根据观察，按需调用 `inspect_treasure()` 查看遗物说明。
3. 调用 `loot_treasure()` 领取当前可见遗物，或调用 `proceed()` 跳过。

`open_only` 可省略或为布尔值，默认 `false`；已开箱时再次传 `true` 属于不可用动作。已领取或空箱不能再次搜刮。动作沿用[MCP 许可规则](mcp.md#调用和错误语义)：初次先观察，成功完整结果可以续接下一动作，失败或切换查看页后重新观察。

开箱可能先出现额外奖励；领取遗物可能引发选牌或嵌套奖励。工具停在当前交互边界，返回[精简动作回执](mcp.md#动作返回格式)，后续使用奖励或选牌工具，不等待依赖后续输入的父任务。处理完后若宝箱仍有遗物，须再次显式调用 `loot_treasure()`，先前请求不会在后台继续自动领取。教程与未支持界面返回 `manual_input_required`。

普通完成会等待原生开箱、遗物领取与遗物自身异步效果、相关牌预览及界面刷新。`complete` 确认返回的停止边界；需要选择时不代表遗物的所有后续效果均已完成。当前宝箱动作不额外记录事件，`transition.events` 为空，金币与已获得遗物从最终顶栏读取。

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
.tmp/mcp-venv/bin/python scripts/verify_treasure.py --scenario basic --report .tmp/treasure-check/basic.json
```

报告和截图目录必须全新。测试真实开箱、领取并前进，只能对新建隔离实例运行。其他夹具、证据与未测范围见[调研记录](../research/2026-10-31-treasure.md)。
