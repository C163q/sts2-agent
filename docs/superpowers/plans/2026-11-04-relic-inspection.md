# 遗物详情正确性与可见状态实施计划

> 当前状态：完成，共 3 项，已完成 3 项；共享读取、专项验证、GUI、文档及提交范围核对均完成，独立变更已交付。暂无阻塞。
> 执行方式：使用 executing-plans 在当前功能分支实施，完成后进行一次独立只读审阅。

**目标**：交付 RELIC-01–03，保留现有参数及原下标映射。
**架构**：RelicInspection.Static 提供图标状态，详情合并正文；Python 先完整校验，再筛选并走公共精简入口；测试断言共享但不复用生产投影计算期望值。
**技术**：C#／Godot、Python／MCP、独立 GUI 套件。
**规格**：[遗物输出定稿](../../research/2026-11-04-inspect-relics-review.md#输出定稿)。

## 约束与审阅重点

- 不增参数，不安装正式 Mod，不动正式存档；保留原生动作及事件边界。
- 核对游戏 v0.107.1 / build 59260271 的 RelicModel.UpdateTexture 与 NRelicInventoryHolder.RefreshStatus，实际呈现优先于模型旗标。
- grayed_out／pulsing 互相独立，也独立于 melted；普通着色 false，无法判断 null；full 保留，default／summary 省略 false／null。
- 精简仅限根 relics 与 top_bar.relics 的这两个字段，其他 false、比较及期间事件保留。
- 所有预设先校验全量数据；筛选不能掩盖坏数据，原下标同时用于映射、提示及 note。
- 可见但无悬停保留静态数据；隐藏／裁剪仍排除；离屏不截断。
- 具体读取拒绝保留旧许可；未知结果不冒充未执行。异常信息保持私有。

## 1. 共享状态、响应与预设

文件：RelicInspection.cs、RequestDispatcher.cs、output/relic_details.py、contracts/ui.py、relic_presets.py、null_fields.py、inspection_details.py；tests/python/test_relic_display.py、原生 RelicInspectionChecks.cs。

- [x] 增加失败测试：full 保留两字段、default／summary 移除 false 并保留 true；基础观察同样处理，其他 false／事件不受影响；坏字段即使空筛选也拒绝。
- [x] 运行 Python 定向测试确认 RED；原生检查用 JSON 字段避免因未实现类型导致编译失败，构建并运行 GUI 确认缺口。
- [x] 原生共享静态读取增加两字段，详情合并；公开安全具体拒绝。在统一精简入口增加局部 false 规则，原生 schema 与 Mod／MCP 版本递增。
- [x] 运行定向测试 GREEN，确认不依赖模型状态推断实际渲染；记录证据。

## 2. 修复专项验证并扩展 GUI 契约检查

文件：tests/game/support/relic_assertions.py、verify_relics.py、verify_mcp_relics.py、verify_relic_presets.py、verify_display_readers.py；新增遗物状态／展示测试夹具与 verify_relic_inspection.py、gui_suite_relic_inspection.json；登记 suite.py 和测试路由白名单。

- [x] 用真实已有完整响应证明旧断言失败，再共享新字段／上下文／提示关联断言，移除固定旧工具清单。
- [x] 双重门控夹具只改渲染／展示，用于实际图标状态与模型状态不一致、无 shader、不可悬停、隐藏栏的边界；finally 和局间重置恢复。
- [x] 覆盖全部预设的映射、null／[]／重复／越界、提示和 note 裁剪、具体错误后直接行动、顶栏一致性及浏览覆盖。
- [x] 验证真实图标激活呈现、自然熔化、非战斗读取；明确夹具注入和原生游玩证据的区别。

## 3. 验收、文档与提交

- [x] 编译、Python 全套、C# checks；准备隔离运行时并用有限超时 GUI 套件验收，等待自有进程完成。
- [x] 独立只读审阅；重要问题经 RED→GREEN 修复，记录裁定及未验证范围。
- [x] 同步持续文档、README 兼容表、用户 TODO 既有两项的覆盖范围、逐项核销；导出真实 full/default/summary 及原下标映射示例，核对来源哈希和链接。
- [x] 使用英文 Conventional Commit 提交独立交付；正式 Mod 不安装。
