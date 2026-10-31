# 占卜接入与验证

核对日期：2026-10-31。目标为 Linux 游戏 `v0.107.1`、分支 `v0.107.1`、提交 `59260271`（发布于2026-06-18），RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。交付接口见[占卜说明](../development/divination.md)，本记录仅对该次实现和验证负责。

## 版本与证据

- 游戏程序集：游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 源码证据：`.tmp/2026-10-31-divination/source/`。复核 `CrystalSphere`、`CrystalSphereMinigame`、Cell/Item 派生类、`NCrystalSphereScreen/Cell/Mask/Item/Dialogue`、`NDivinationButton` 与 `NClickableControl.ForceClick`。一般事件基线见[事件调研](2026-10-31-events.md)。
- 资源证据：目标 `SlayTheSpire2.pck` 中 `scenes/events/custom/crystal_sphere/` 场景及 `shaders/scry_reveal.gdshader`。依据 Godot [4.5 PCK 读取实现](https://github.com/godotengine/godot/blob/4.5-stable/core/io/file_access_pack.cpp)只读提取至忽略目录，没有加入 Git。
- 图像 API：核对 Godot 4.5 的 [Viewport](https://docs.godotengine.org/en/4.5/classes/class_viewport.html) 与 [Image](https://docs.godotengine.org/en/4.5/classes/class_image.html)。棋盘裁剪须包含 viewport stretch transform；在 `frame_post_draw` 后取实际渲染图像。
- MCP：[2025-06-18 工具规范](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)允许一份结果含多个内容块，图像使用 `ImageContent`，结构化内容可另附相同 JSON 文本。使用实际 Python `3.14.8`、`mcp==1.26.0` 的 stdio 客户端验证传输；没有将 base64 放入 LLM 文字 JSON。

## 原生边界

`NDivinationButton` 和格子均通过原生 `Released` 进入游戏。`ForceClick` 会绕过 hover/focus/pause，适配器因此先核对完整可见性、当前许可、单人、格子未揭开、原生可用状态及结算就绪。没有直接调用模型 `CellClicked` 或改写棋盘、次数和奖励。

遮罩 shader 根据每格 `gridFadeParams` 在0.5秒内插值，不能只看 `IsHidden` 变化。`NCrystalSphereItem.OnRevealed` 还存在自身动画；原生 `CompleteMinigame` 在最后揭开后等待0.75秒，再等待自定义奖励输入，最后才通知 `Finished` 并启用前进。动作等待这些真实边界，子奖励与选牌不受父事件仍在等待的影响。

自动棋盘图像只裁剪实际绘制的11×11格子矩形，部分揭开的图标由像素保留。公开路径未读取 `Items`、`cell.Item` 或完整物品矩形来序列化身份、边界和价值。测试 fixture 为确定性覆盖诅咒、卡牌、药水和4×4遗物读取隐藏真值来安排测试点击；这些真值只在测试模式的私有检查入口返回，不进入 MCP 工具和公开观察。

## 验证结果

本次证据位于 `.tmp/2026-10-31-divination/`，使用全新报告路径和独立用户目录；所有游戏操作都作用于测试实例。

| 验证 | 结果 |
| --- | --- |
| Python 全套 | 236项通过，包含11项新增占卜测试及真实 stdio/临时文件 IPC |
| C# 纯检查 | 24项通过 |
| Mod 编译 | .NET9 构建，0错误、0警告 |
| 3次占卜、大小工具与重复格 | 进入、切换、单格、按边界裁剪3×3、重复格拒绝、最终前进通过 |
| 6次及诅咒 | 债务进入、完整揭开诅咒后加入 Doubt，结算后前进通过 |
| 遗物图标 | 通过4次大范围完整揭开4×4图标，最终奖励页与返回前进通过；没有提前查询随机遗物结果 |
| 普通奖励 | 药水领取、卡牌奖励打开、选牌跳过、奖励前进与返回棋盘通过 |
| 满药水栏 | 领取未成功保留奖励；丢弃一瓶后正常领取，继续选牌并返回棋盘通过 |
| 地图 | 打开、棋盘覆盖字段为 null 且无底层图像、关闭返回棋盘、重新观察与继续通过 |
| 延迟行动 | 等待4秒模拟模型思考，临时对白消失后仍可前进；真实状态继续复核 |
| 相邻图形回归 | 通用事件翻页、Trial 人工确认边界、假商人药水进入战斗、普通奖励、10步战斗动作链通过 |

当前最终 DLL SHA256 为 `c56862822e9386f47ba0124bf1f54b8b33f7c8c357570db850359ffed8e47e03`，清单为 `fb620d61d2a9a316e194f4e7a795c91e613aa718347cb9deeb1aaca5739b9f12`。构建文件与隔离加载文件相同；安装完成情况另以交付记录为准。

## 复现与修复

1. **裁剪未应用窗口缩放。** 最初点击中心格后，PNG 中揭开位置偏离中心。独立像素检查先返回 `center_border: false`；应用 `GetStretchTransform()` 后为 true。对应 `geometry-red/green` 报告和完整视口截图；最终裁剪样本为599×598像素，不将该尺寸作为固定协议值。
2. **临时对白误使许可过期。** 等4秒后 `proceed` 返回 `stale_state`，原因是对白自动消失改变观察哈希。将瞬态对白与动态图像排除出许可内容，保留次数、工具、格子和忙碌状态；相同延迟场景通过。
3. **地图关闭校验拒绝占卜页。** 游戏已正确返回棋盘，Python 仍将所有 `screen.view` 当成残留浏览页而报传输错误。新增失败测试后允许已验证的占卜观察，地图往返通过。
4. **CRC 正确但像素不可解码。** 独立审阅构造损坏 IDAT，初版只检查块结构仍授予许可。加入原生8-bit RGB(A)、非交错格式检查及有界 zlib 解码、扫描行长度、过滤器与尾随数据检查。坏流、过量/不足像素和非法过滤器的失败测试转为通过；审阅复核无剩余 Critical/Important。

测试脚本曾反复打开同一未领取卡牌奖励并跳过，已改为每行只尝试一次再前进；这是验证脚本的循环错误，没有改动原生跳过规则。隔离进程均由启动脚本回收；引擎退出时既有静态字符串清理日志未被描述为无警告启动/退出。

## 未验证范围

没有使用视觉模型自主决定并玩完整次占卜，已验证的是实际 UI、脚本决策和 stdio 图像传输；不能据此保证任意客户端会将图像交给模型。没有穷尽 RNG 排列、所有遗物/药水获取修饰、不同窗口缩放、多显示器及渲染后端。原生玩法允许跳过奖励，本次没有推断其最优选择策略。

多人、第三方小游戏、Trial 确认框操作、地图选路和 The Architect 不在本次范围。正式对局未被工具操作；更换磁盘 Mod 文件后须完整重启游戏，重连 MCP 才能加载新版本和工具目录。
