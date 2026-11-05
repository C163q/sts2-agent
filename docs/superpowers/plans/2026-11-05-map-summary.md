# 地图分类摘要实施计划

> 当前状态：实施中，共 1 项，已完成 0 项。核心实现与约定测试通过；剩余一次独立审查和合入 main。暂无阻塞。
>
> For agentic workers: REQUIRED SUB-SKILL: superpowers:executing-plans。采用本会话实施和一次独立终审；沿用当前检出的隔离临时分支及已有测试运行时。

**Goal:** 修复地图查看拒绝的恢复与诊断，加入按类型分类的 summary，并统一基础观察地图表达。

**Architecture:** 原生地图读取去除响应令牌依赖，完整图进入同次基础观察；inspect_map 复用这次快照。Python 先校验完整图，再共用分类投影，深度裁剪仅属于详情工具。旧 schema 的五字段地图仍可读取，新 schema 必须完整校验。

**Tech Stack:** C#/.NET 9、Godot、Python MCP、现有隔离 GUI 测试。

**Spec:** [已确认规则](../../research/2026-11-05-inspect-map-review.md)、[源码核验](../../research/2026-11-05-inspect-map-development-notes.md)。这两份记录的字段与边界草案随用户确认成为实施要求。

## Global Constraints

- inspect_map 默认 default；full/default/selectable 原有主体与 max_steps 契约保持，新增 summary；max_steps 默认 0。
- summary 仅类型与 ID，不含连线、名称、任务标记、revealed_type 或已走路线；先裁剪后分类，原生候选不裁剪。
- get_observation 的 full/default/summary 地图使用整幕分类，外层 notes.map 为 `Map connections omitted; use inspect_map for details.`；actions_only/top_bar 不加地图或 note。
- 追加已确认范围：原生 MapRoom 统一识别为 scene:map，普通房间上的地图仍保持原 scene；覆盖 Boss 后 proceed 紧接观察与延时对照。
- 普通空值仍使用公共规则，不主动打开地图，不读取被覆盖地图，不改变原生点击与单人限制。
- 明确点击前拒绝只保留已有许可，不制造许可；点击后失败和状态变化不承诺未交互。
- 英文代码注释、中文文档；不安装正式 Mod、不推送；验证后自行合入 main。

## Review Focus

1. 飞鞋候选在深度子图外仍保留合法性，不伪造连线或补入分组。
2. 幕起点 null 与多起点、双 Boss、裁剪边界按既有步数；不将图标已揭晓内容推断成未来信息。
3. 新原生图的损坏不能被 summary/actions_only 过滤绕过；旧五字段快照保持兼容且不伪造分类。
4. 地图关闭、被牌组覆盖、选择战场查看时，地图和 note 与真实页面一致；同次快照不重入 Observe。
5. 明确拒绝、点击后变化、无初始许可和矛盾执行证据分别验证；available_actions 与执行原因一致。

## Task 1: 地图查看与分类输出

**Files:** MapInspection.cs、GameAdapter.Views.cs／AvailableTools.cs、新 GameAdapter.Map.cs、GameObservation.cs；map_details.py、contracts/map.py、observation_details.py、public_output.py、tool_registry.py；相关地图与会话测试、GUI 验证器及当前指南。

**Interfaces:** 原生 `MapInspection.Read(screen, run)` 返回无令牌完整图；`Summary` 只读暴露地图。Python `grouped_map(payload)` 提供纯分类投影，`map_observation(value, context, require_graph)` 校验并用于基础观察；legacy 保留原五字段。`MapUnavailableReason()` 服务工具列表与执行校验。

- [x] 补测试并确认失败：summary 0/1/2 步、幕起点、元信息省略、飞鞋范围、所有观察预设、损坏图、点击前许可恢复。
- [x] 实现共用完整读取和校验、分类输出及 note，修复固定公开错误与未交互恢复；版本 Mod 0.68.0、MCP 0.70.0、schema 41。
- [x] 运行针对性及全套 Python、C# 检查，编译并准备隔离运行时；保留失败证据。
- [x] 以现有地图夹具实测飞鞋、战斗禁行、幕起点、双 Boss，以及覆盖／关闭、明确拒绝直接续接；提供典型新 JSON。
- [ ] 更新现行指南、规格与清单，提交实现，完成一次独立审查；有重要发现则修复并验证。
- [ ] 合入 main、清理临时分支和自有进程，归档工作记录后删除本计划工作区。

验证命令：`timeout 180s .tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'`；`dotnet build Sts2Agent.sln -m:1 --no-restore`（使用 .env 游戏依赖参数）；C# Checks；`scripts/gui_suite.py` 的本任务组合套件。预期均退出 0；GUI 明确记录实际覆盖及未验证范围，不要求每个场景都有 JSON。
