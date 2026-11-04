# 药水读取边界与预设实施计划

> 执行方式：使用 executing-plans 在当前工作区逐项实施，TDD 验证，最后独立审查。
>
> 当前状态：完成，共 3 项，已完成 3 项；代码、审查修复、全部验证及文档核销完成，无遗留实施步骤或阻塞。

**目标：** 修复 POTION-01–05，增加 summary 与 slot_indices，保持玩家 UI 信息边界和原槽位引用。

**规格：** [药水审阅](../../research/2026-11-04-inspect-potions-review.md)的已确认范围及本计划的具体裁定。用户已授权实施。

**架构：** PotionInspection 共用槽位静态读取、独立悬停读取；动作定位另查入口合法性。Python 使用现有过滤、共享解释和空值规则，仅增加药水领域预设，不增加第二套会话恢复。

## 全局约束与裁定

- 原槽位不按视口截断；隐藏、透明、无纹理、零面积及实际裁剪仍不可读。无法确认一个槽位时保留原有整栏未知／详情拒绝，不引入局部未知格式或将未知记为空槽。
- 可见但不可悬停时保留静态数据；full/default 正文为空并给 note，summary 不读悬停正文或槽位帮助。
- summary 的槽位内容与基础观察共用，包括存在时的 bouncing、usable_here；full/default 同样携带这些静态字段。
- 省略／null 筛选为全部，[] 为空；合并越界 errors；筛选映射及提示、note 来源均是原槽位，关联随筛选裁剪。
- full/default 保留通用 slot_tip；summary 仅上下文、静态槽位及筛选映射／错误。
- 动作与事件调用者独立保留原有可点击及历史可见性边界；不因查看条件放宽而自动放宽用药。
- 独立分支使用现有工作区与隔离游戏 runtime，不修改正式游戏安装；游戏 API 按审阅中目标程序集证据核对。

## 审查重点

1. 隐藏或图标缺失不能被读成药水名字或 null 空槽；包含基础观察与全部预设。
2. 灰色、禁用、鼠标／手柄入口关闭与真正隐藏分别处理；离屏读取不能放宽动作定位。
3. 空槽筛选不能留下 Block 提示；压缩结果、提示与 note 的原槽位关联一致。
4. summary、空筛选不能掩盖坏响应；未知执行结果不得恢复旧许可。
5. 覆盖页面、战斗外特殊显示、丢弃后的空槽与事件记录保持兼容。

## Task 1：原生读取与正确性

**文件：** PotionInspection.cs、CombatObservation.cs、PotionActions.cs、RequestDispatcher.cs、PotionInspectionChecks.cs、测试派发入口。

**接口：** 静态读取返回位置不变的槽位；Read(holders, full) 返回可空 description、共享静态字段与 unavailable_hover_sources；VisibleHolders 提供读取集合，动作另用入口检查。

- [x] 先补游戏内边界检查：离屏可读、禁用保留静态、隐藏图标使基础观察未知、关闭两个悬停入口不读正文；运行旧实现，确认失败。
- [x] 实现共用静态读取、HoverAccess、具体安全错误；保留动作和事件边界，重跑上述检查。

命令：构建后 prepare_roundtrip；以独立 GUI suite 调用 check_test_potion_readers。预期由边界断言失败变为全部通过。

## Task 2：预设、槽位筛选与公开契约

**文件：** potion_presets.py、potion_details.py、tool_registry.py、inspection_details.py、roundtrip_client.py、test_potion_presets.py。

**接口：** potion_arguments / potion_preset；私有 level=summary 省去原生悬停；公开 preset default/full/summary、slot_indices。

- [x] 新增测试覆盖省略／null／[]、空槽、重复、越界、原位置提示裁剪、note 裁剪、摘要静态字段、错误许可和坏响应；先运行确认旧实现失败。
- [x] 接入登记、完整解码、摘要与筛选；CLI 增加药水 preset 和 slot-indices，raw 保留协议；跑领域及完整 Python 回归。

命令：有界 unittest；预期领域与全套通过，无自动观察或重试。

## Task 3：GUI 验证、文档与交付

**文件：** verify_potions.py、verify_mcp_potions.py、药水预设 GUI 验证／清单、接口与审阅记录、版本表。

- [x] 修复旧验证断言，保留只读、英语、原槽位及提示去重检查。
- [x] GUI 验证满栏、空槽筛选、共享提示、不可悬停 note、隐藏／离屏边界、覆盖页与使用／丢弃；保存真实 JSON。
- [x] 完整 Python、C# 检查和构建通过；同步文档、版本及核销清单；独立审查并处理发现，提交实现。

命令：Python unittest discover；dotnet build / checks；gui_suite --suite 药水及相关组合清单。预期报告通过，正式 Mod 未安装，TODO 未擅自核销其他工具。
