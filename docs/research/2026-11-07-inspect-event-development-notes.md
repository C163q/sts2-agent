# inspect_event 开发核验依据

本记录对应[审阅与占卜文字方案](2026-11-07-inspect-event-review.md)，用于定位源码与后续验证。本记录保留b1afbaa实现前的源码、资源与受控输入核验；修复、后续GUI及最终范围见[实施记录](2026-11-07-event-inspection-text-implementation.md)。

## 基线与证据

- 代码基线 b1afbaa；Mod 0.75.0、MCP 0.77.0、schema 44。未构建、安装或改动产品代码。
- 核对日期 2026-11-07；Linux 游戏 v0.107.1、发布 59260271、RitsuLib 0.6.10。
- 游戏安装目录内 data_sts2_linuxbsd_x86_64/sts2.dll 的 SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03，与[原占卜核验](2026-10-31-divination-validation.md)相同。
- 原生源码证据为 .tmp/2026-10-31-divination/source/ 下 CrystalSphereMinigame、CrystalSphereItem 及五种派生类、NCrystalSphereScreen/Item/Mask、场景与 shader；事件按钮依据 .tmp/2026-10-31-events/source/NEventOptionButton.cs 与 NEventLayout.cs。
- 新资源证据位于 .tmp/2026-11-07-inspect-event-review/assets/；assets-manifest.json 记录从目标 SlayTheSpire2.pck 只读提取的 40 项相关资源及各项 SHA-256，逐项校验 PCK 内 MD5。13 张小尺寸贴图解码供本地目视核对，不纳入 Git。

资源读取依据 Godot 4.5 的 [PCK 读取实现](https://github.com/godotengine/godot/blob/4.5-stable/core/io/file_access_pack.cpp)和 [CompressedTexture2D 读取实现](https://github.com/godotengine/godot/blob/4.5-stable/scene/resources/compressed_texture.cpp)。目标 PCK 为格式 3，头部引擎版本 4.5.1；只读取未加密条目及 PNG/WebP 贴图数据，没有修改游戏资源。

## 已确认问题

| 编号 | 优先级 | 依据与修复范围 |
| --- | --- | --- |
| EVENT-INSPECT-01 | 中 | [普通事件请求](../../src/Sts2Agent/Adapter/GameAdapter.Event.cs)和[占卜请求](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)使用 FileMailbox.Error，未公开具体拒绝原因。[error_output](../../src/sts2_mcp/output/error_output.py)仅接受显式 public_message，因此细节被替换为通用 illegal_action。应提供读取专属原因，并供 available_actions 复用 |
| EVENT-INSPECT-02 | 中 | [inspect_event_details](../../src/sts2_mcp/output/event_details.py)检查 scene==event，但不核对页面与对应主体。context-probe.json 中 event-map 与 board-deck 均被 inspection_details 接受。应校验可见事件要求当前事件页、可见占卜要求 divination 页；覆盖状态不能携带可见主体 |
| EVENT-INSPECT-03 | 中 | [DivinationInspection.Read](../../src/Sts2Agent/Observation/DivinationInspection.cs)只生成 covered_rows 与图片尺寸；可见碎片在 PNG 中，纯文字无法获得。此项是既有用户 TODO，待设计确认后实现 |

02 的探针使用现有 Python 测试中的受控事件／棋盘对象，只改变 screen，调用实际 inspection_details，未经过游戏或真实 IPC。它证明读取器接受矛盾数据，不证明适配器生成了这种数据，也不将探针记为 GUI 通过。

读取拒绝的许可恢复已由 [GameSession](../../src/sts2_mcp/game_session.py) 的 effect==read 路径处理，适用于 inspect_event；未发现需要重新添加该机制的证据。未知通信结果及媒体校验失败仍清除许可。

## 外观与读取职责

CrystalSphereMinigame.PopulateItems 实际生成九类图案：两种金币、两种药水、三种卡牌奖励、诅咒、遗物。CrystalSphereItem.PlaceItem 只选择 Position；NCrystalSphereScreen 按 Size×57 设置控件并平移，未设置旋转。

NCrystalSphereItem._Ready 对卡牌奖励隐藏 _icon，使用 CardFrame、CardBanner 及阴影组合；实际牌框材料来自玩家角色，横幅材料来自稀有度。资源中三张预合成 card_reward PNG 不能直接当作当前绘制真值。仅凭下方相同的牌框不能输出稀有度。

NCrystalSphereItem.OnRevealed 在完整揭开后播放闪光与缩放，NCrystalSphereScreen.OnItemRevealed 播放正向／负向对白。cell_rows 的 S 应表示已完整揭开的可见图案，而非已领取、随机奖励身份或内部矩形；该字符是文字转译，原生并没有永久显示字母或同名标记。需验证动画结束、重新读取与页面往返后仍能依据完整外观保持正确表示。

common_potion 与 uncommon_potion 解码后 RGBA 像素 SHA-256 同为 b3259870855365aad0936917e7c870cb9b7b5921a55acee32359237243f03795。字典应按外观归类，不以类枚举制造不存在的视觉差别。

后续识别入口建议只接收可见区域图像／遮罩与静态图案定义，避免依赖 CrystalSphereItem.Position 或 cell.Item 选择唯一答案。识别结果必须容许多个可见外观等价、透明留白与未知。字典可包含固定方向的静态图案知识，但不得把推断的雾下范围列作本次直接观察。

## 待核验项

- EventInspection.Shown 使用 OnScreen(%Text)，用于 ID、静态读取及动作查找。应核对静态列表是否改为 Displayed，同时单独保留点击范围判断；当前尚未用事件布局实测离屏漏项。
- EventInspection.Read(full:true) 用 Clickable 决定 hover_tips。原生 NEventOptionButton.OnFocus 主要排除 IsLocked；仍需连同 NClickableControl 的有效鼠标／焦点规则验证，分开“可点击”与“可悬停”。锁定选项原生没有悬停，不应因重构而提供说明。
- 普通事件读取只要求 Exposed 与单人，占卜读取还要求 Ready。若允许结算中观察占卜，须保持点击的 Ready 条件，并核对截图采样时序、工具状态及许可过期规则。
- EVENT-INSPECT-02 涉及的成功数据需在完整解码后再执行预设投影；空筛选或 summary 均不能绕过校验。
- 文字识别的准确性、耗时、窗口缩放、卡框材质、边框遮挡及透明区域均未测试。现有图片流程没有变化。

## 样例与验证界限

[样例目录](2026-11-07-inspect-event-examples/README.md)包含两份当前结构的完整 full JSON。主体取自历史真实游戏结果，使用当前 decode_success 重放，补入相邻历史观察的 screen 与当前 schema 标记；manifest 写明来源、行号、补充规则与哈希。没有验证当前 GameSession 的图像传输，也没有将这些结果描述为新游戏实测。

仅运行上述两个受控上下文探针、资源提取／解码和文档／样例一致性检查；未启动游戏、运行全套测试或构建。实现前须完成碎片词表和图片策略定稿，再安排对应新鲜 GUI 样本及拒绝恢复验证。
