# 占卜小游戏

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。支持单人原生 Crystal Sphere，先用[事件工具](events.md)进入小游戏。

## 工具与图像

| 工具 | 内容／操作 |
| --- | --- |
| get_observation(preset?) | 文字棋盘、已揭开碎片、次数、工具、当前对白及可用动作；full/default/summary 均省略固定教学，不返回 PNG |
| inspect_event(preset?, include_image?) | 共用文字棋盘；full/default 另提供当前展示的教学，summary 省略教学；include_image:true 按需附上当前棋盘 PNG，默认 false |
| set_divination_tool({"tool":"small"}) | 切换小范围工具；big为大范围，不消耗次数；可直接调用，返回actions_only格式 |
| divine({"x":5,"y":5}) | 点击一个仍被覆盖的格子，消耗一次次数 |
| proceed() | 点击结算后实际启用的前进按钮 |

占卜复用 inspect_event，没有独立 inspect_divination；两种观察从同一份可见棋盘读取。get_observation 不接受 include_image。图片可选，与工具 preset 分开控制。工具只读拒绝会说明无棋盘、地图／牌组／选择／奖励覆盖或开场过渡等原因；已有许可的明确读取拒绝可直接改用当前合法工具。

## 文字棋盘

坐标左上角为 (0,0)，x 向右、y 向下，范围均为 0–10。grid 包含 columns:11、rows:11、11 行 cell_rows，以及按行排列的 visible_fragments。每行 11 个字符：

| 字符 | 含义 |
| --- | --- |
| # | 仍覆盖；揭开动画尚未完成的格子也暂时保留此状态 |
| . | 已揭开且没有可见图案，或棋盘边缘空白 |
| s | 已显示图案局部，整体尚未全部揭开 |
| S | 图案整体已经揭开；并不表示已经领取奖励 |

例如以下为字段结构示例，省略其余行，并非完整实测返回：

```json
{
  "cell_rows": ["#####s#####"],
  "visible_fragments": [
    {"x": 5, "y": 0, "appearance": "potion.base"}
  ]
}
```

每个 s/S 格有一条坐标与 appearance 记录。可见部位名包括 potion.stopper/body/base（瓶塞／瓶身／瓶底）、round_potion 的圆瓶部位、card 的牌框部位、gold 的金币部位和 box 的箱体部位。有图案但无法可靠转译时保留 unrecognized；透明留白不因内部占用矩形而填满。完整揭开后，对应可见图案格改为 S。

固定图案不旋转。常见药水为1×3、圆瓶为2×2、卡牌为2×2、遗物箱为4×4、金币为1×1或2×1。静态词表由[共用图案定义](../../src/sts2_mcp/data/divination_patterns.json)维护。卡牌只有顶部横幅可提供对应稀有度；下方牌框使用共用名称，不附带隐藏横幅的类别。药水、遗物和卡牌奖励图标不会提前给出将来随机生成的具体奖励。

读取依据当前显示节点的贴图、几何和已清除的遮罩区域；不从 cell.Item、雾下物品位置或奖励列表输出真实分组。原生物品层比格子层高2像素；按原生格子放置坐标确定部位，并排除格线及球体外框遮挡的溢出像素。未知外观与不支持的布局不能标成已识别部位。

## 可选图片

inspect_event({"include_image":true}) 在文字结果后另附 ImageContent PNG。图片裁剪当前实际渲染的棋盘，保留遮罩、边框与局部图案；grid.image 记录该 PNG 的实际尺寸。JSON 与文字块不含 base64。只有这个调用需要支持图像的客户端；默认文字及 get_observation 不依赖 PNG 捕获。

自动附图与可选[截图存档工具](screenshots.md)独立；请求图片不会自动存盘。显式请求的图片无效或无法捕获时读取失败，不授予新许可。底层文件调用通过 response_options.include_divination_image 控制媒体，省略该选项仍兼容旧文件客户端的附图行为；见[文件协议](roundtrip.md#原型接口)。

## 动作、覆盖与结算

大范围以指定格为中心揭开按边界裁剪的3×3，小范围揭开一格。参数严格接受 big/small 或整数坐标，额外字段、布尔坐标、字符串、浮点数和越界值均拒绝。操作复用原生按钮；揭开和前进返回[精简动作回执](mcp.md#动作返回格式)，后续按需观察棋盘。

工具切换为视图操作，不要求已有观察许可；成功返回scene、screen及available_actions，刷新许可供后续揭开使用，不返回transition或图片。重复选择当前工具同样成功。切换前检查页面、忙碌和按钮状态，成功前确认仍属同一对局、棋盘及实际选中工具；完整棋盘和工具值由观察读取。该接口与Mod应配套更新，旧Mod仍要求切换前提供状态令牌。

无棋盘、地图／牌组／奖励／选牌覆盖、结算中或已经结束会给具体原因和对应工具提示。明确未交互的拒绝保留已有许可，可直接继续合法操作；首次拒绝不生成许可。交互后的错误、未知或坏响应仍须重新读取，完整规则见[MCP调用和错误语义](mcp.md#调用和错误语义)。

phase 为 playing、settling 或 finished。观察可读取已经展示的结算过程，动作继续要求原生输入与动画就绪。动作等待实际揭开、资源及奖励稳定；次数归零后仍可能需要奖励或选牌输入，按[共享动作边界](end-turn.md#动作完成与画面稳定)处理。

地图、牌组、奖励或其他界面覆盖时，divination.status:covered，其余底层字段为 null，不返回碎片与底层图像。关闭地图或浏览页后可以直接继续合法操作。finished 隐藏次数、工具与教学，只有原生前进启用时才允许 proceed。

完整当前对白只在文字渐显完成时返回。瞬态对白与动态图像不使许可过期；次数、工具、棋盘、忙碌状态和页面变化仍会复核。观察不切换游戏语言，不主动生成或领取奖励。

## 验证入口

按[测试指南](roundtrip.md)编译并准备隔离实例，使用[工具切换专项](../../tests/game/data/gui_suite_divination_tool_view.json)验证冷调用、重复选择、覆盖拒绝与合法后续操作；事件／占卜文字观察使用tests/game/data/gui_suite_event_inspection.json。UI显示夹具与隐藏真值仅用于私有测试入口，不进入公开工具目录；自然揭开和UI夹具验证的范围分别记录在[文字观察实施](../research/2026-11-07-event-inspection-text-implementation.md)及[工具切换实施](../research/2026-11-07-divination-tool-view-implementation.md)。
