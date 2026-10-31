# 占卜小游戏规格

实现通用事件调研的第二阶段，目标为 Linux 游戏 v0.107.1、RitsuLib 0.6.10。以原生 `CrystalSphere` 开启的 `NCrystalSphereScreen` 为范围；不实现 Trial 确认框、地图选路、多人或第三方小游戏。沿用用户已授权的自主设计、实现、验证和安装流程。

## 信息与图像

当前界面保持 `scene: event`，`screen.view: divination`；小游戏展开时 screen 为 visible，底层 event 为 covered。新增 `divination` 对象：`status`、`phase`（playing/settling/finished）、`remaining`、`tool`（big/small）、`tools`、`instructions`、`dialogue`、`grid`、`proceed`。被地图、奖励或其他界面覆盖时只保留 covered，其余字段为 null。未显示的计数、工具和说明为 null，不从隐藏模型补出。

`grid` 包含 columns/rows 与按行排列的 `covered_rows`，`#` 表示原生仍覆盖的格子，`.` 表示已揭开；左上角坐标为 (0,0)，向右 x、向下 y。棋盘图像是游戏已绘制 viewport 中全部格子的矩形裁剪，保持原始像素，11×11 等分与坐标对应；不重绘、不添加网格、不移除雾、不读取物品类型或完整范围。`grid.image` 提供像素 width/height。

可见棋盘的基础观察、动作最终观察和 `inspect_event` 附带同一次主线程帧后采样的 PNG。IPC 的私有 `divination_image` 携带 base64；MCP 将其校验后转换为 `ImageContent`，JSON 和 TextContent 不含 base64。只为当前 visible divination 提供图像，不转发隐藏底层、未知字段或截图路径。捕获不可用或 PNG 无效时不授予动作许可，明确报错，不以残缺文字静默继续。

图像为自动观察信息，与可选 `capture_screenshot` 存盘工具独立；默认截图配置关闭仍须可玩。纯文字客户端不受支持，MCP 通用协议没有可据以确认模型实际视觉能力的协商项；文档声明这一前提，并以真实 stdio 客户端验证 ImageContent 传输、解码与 PNG 裁剪内容。

## 操作与结算

新增 `set_divination_tool({tool: big|small})` 和 `divine({x: int 0..10,y: int 0..10})`。参数严格拒绝布尔值、额外字段、越界、字符串和浮点坐标。工具切换点击真实 `NDivinationButton`，揭开点击真实 `NCrystalSphereCell` 的 Released 流程；不直接调用 CellClicked 或修改次数/格子/奖励。已揭开格、被覆盖页、结算中与结束后不能揭开。大工具以中心揭开裁剪后的3×3，小工具揭一格；不主动代选。

使用已有观察许可、原生合法性复核和成功动作观察续接。切换工具不消耗次数。等待原生点击任务、遮罩淡入淡出、物品揭开动画、卡牌预览与资源动画稳定；最后次数为0并非完成，必须等 `.75s` 后的原生奖励及 Finished 通知。可输入的子奖励/选牌优先返回，继续使用已有工具；父小游戏等待子界面时不误判卡死。Finished 后只在原生前进按钮启用时开放 `proceed`，不自动打开地图。读取不改变游戏语言、RNG、模型和界面。

## 验证

先写失败测试覆盖严格参数、可见/覆盖投影、私有图像清除、坏图像撤销许可、动作连续调用和真实 stdio 混合内容。隔离图形验证两种进入方式（3/6次）、工具切换、边缘裁剪、重复格拒绝、局部与完整揭示、最后结算、奖励/选牌及前进；保存实际截图与 MCP 棋盘图像核对。对一般事件、确认框人工边界、商店、战斗和奖励进行必要回归。完整 Python、C# 检查及 Mod 编译通过后记录实际覆盖与剩余范围，创建独立提交并沿用备份安装流程。
