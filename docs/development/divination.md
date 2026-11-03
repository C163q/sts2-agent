# 占卜小游戏

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

支持单人原生 Crystal Sphere 界面，先用[事件工具](events.md)选择进入方式。

下文输出字段的空值与 JSON 示例以底层文件或 MCP full 为准；MCP 工具另接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

## 工具与图像

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | 当前棋盘、次数、工具和可用动作，刷新动作许可 |
| `inspect_event()` | 只读当前占卜界面，与基础观察的小游戏信息相同；成功时刷新状态令牌 |
| `set_divination_tool({"tool":"small"})` | 点击小范围工具；`big` 为大范围，不消耗次数 |
| `divine({"x":5,"y":5})` | 点击一个仍被覆盖的格子，消耗一次次数 |
| `proceed()` | 点击结算后实际启用的前进按钮 |

占卜复用 `inspect_event` 作为专门查看入口，没有独立的 `inspect_divination`。`get_observation({"preset":"summary"})` 省略固定教学 `divination.instructions`，其余主体沿用 default，保留棋盘、图像、可见次数、工具按钮、当前完整对白及坐标说明；default/full 和 `inspect_event` 仍提供实际可见的教学说明。摘要不改变原生页面或动作许可，验证范围见 [13–15 组核验记录](../research/2026-11-03-get-observation-divination-confirmation-epilogue.md)。

占卜需要**支持图像内容的 MCP 客户端及有视觉能力的模型**。可见棋盘随完整基础观察和 `inspect_event` 详情返回独立的 `ImageContent` PNG；动作使用[精简回执](mcp.md#动作返回格式)，不附送棋盘或图像，后续按需查看；JSON 与文字内容不含 base64。图像直接裁剪游戏当前渲染画面，保留遮罩、边框和物品碎片，不从内部物品模型重绘。纯文字客户端无法获得全部可见信息。

自动棋盘图像与可选[截图存盘工具](screenshots.md)独立：默认关闭截图工具仍可玩占卜，不自动存盘。文件客户端在 `state.divination_image` 收到 PNG base64，MCP 将其校验后转为图像。不能捕获有效图像时调用失败，不提供动作许可。

## JSON 示例

以下省略通用顶栏和底层已覆盖的事件字段；说明正文只摘取首句，实际返回完整英文说明。该 JSON 后还有一个 PNG 内容块。

```json
{
  "scene": "event",
  "screen": {"status": "visible", "view": "divination"},
  "divination": {
    "status": "visible",
    "phase": "playing",
    "remaining": 3,
    "tool": "big",
    "tools": [
      {"id": "big", "text": "Big Divination", "enabled": true},
      {"id": "small", "text": "Small Divination", "enabled": true}
    ],
    "instructions": {
      "title": "How to Divine",
      "description": "Reveal your future by revealing the tiles!"
    },
    "dialogue": null,
    "grid": {
      "columns": 11,
      "rows": 11,
      "covered_rows": [
        "...#####...",
        "..#######..",
        ".#########.",
        "###########",
        "###########",
        "###########",
        "###########",
        "###########",
        ".#########.",
        "..#######..",
        "...#####..."
      ],
      "image": {"width": 599, "height": 598}
    },
    "proceed": null
  }
}
```

结果另带精简 `notes.divination`，说明坐标与符号。图像覆盖11×11格子的完整矩形，按11等分对应坐标；尺寸随实际渲染分辨率变化，不能固定为示例数值。`#` 为仍覆盖的格子，`.` 为已揭开，边缘初始就有不可点空白。左上角为 `(0,0)`，向右为 x、向下为 y。只在 `playing` 且动作列表有 `divine` 时点击 `#` 格，已揭开格不能重复点。

大范围揭开以指定格为中心、按边界裁剪的3×3，小范围揭一格。参数必须为 `big/small` 或0至10的整数；拒绝额外字段、布尔值、字符串、浮点数和越界值。切换工具、揭开和前进均点击原生按钮，在 UI 上可见。

## 结算与边界

`phase` 为 `playing`、`settling` 或 `finished`。动作等待原生点击、遮罩及物品揭开动画、卡牌预览与资源结算稳定。次数归零后仍有延迟及奖励流程，不能提前报告结束。奖励或选牌需要输入时按[共享动作边界](end-turn.md#动作完成与画面稳定)返回，用现有奖励、选牌、药水工具继续。

地图、奖励或其他界面覆盖棋盘时，`status: covered`，其余字段为 null，不返回底层图像。地图使用 `inspect_map/close_map`；关闭后可直接继续当前界面的合法动作，需要棋盘图像时按需调用 `inspect_event`。最终 `finished` 时原生隐藏次数、工具和说明，对应字段为 null；只有原生前进启用时才能 `proceed`。不自动领取奖励、选择卡牌或打开地图。

成功完整动作的观察可续接下一动作。动态噪声图像和自动消失的对白不使动作许可过期；次数、工具、格子、忙碌状态和页面变化仍会触发复核。对白只在当前完整显示时返回英文，不改变游戏语言。

不输出雾下物品、完整占用范围、未完整揭开的身份或未来奖励。碎片由图像保留，已揭开图标也不提前生成随机药水、遗物或卡牌奖励。源码、实测与未覆盖范围见[占卜验证记录](../research/2026-10-31-divination-validation.md)。

## 隔离验证

按[测试指南](roundtrip.md)编译和准备隔离实例，启动：

```sh
python3 scripts/run_roundtrip.py --windowed --event-scenario crystal
```

另一终端验证6次及奖励衔接：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_divination --option 1 --scenario rewards --report .tmp/divination-check/rewards.json
```

使用全新报告路径，只连接隔离 IPC，不用于正式对局。验证脚本使用私有测试真值安排覆盖用例；真实 LLM 不会获得这些数据。
