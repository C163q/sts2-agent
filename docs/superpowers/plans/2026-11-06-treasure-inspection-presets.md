# 宝箱详情边界与 summary 实施计划

> **For agentic workers:** 使用 superpowers:executing-plans 自行执行，一次独立审查收尾。
>
> 当前状态：已完成，共 1 项，已完成 1 项。全部约定验证、独立审查及本地集成完成，2862318 已合入 main，临时分支已清理，无阻塞。

**Goal:** 修复宝箱详情诊断、上下文及悬停边界，新增沿用静态宝箱格式的 summary。

**Architecture:** TreasureInspection 共用显示读取，详情按可悬停性扩展；读取、悬停和原生点击各有判断。Python 在完整校验后投影 summary，保留纯读取许可处理。

**Tech Stack:** .NET 9／Godot／目标游戏，Python stdio MCP、unittest 与隔离图形套件。

**Spec:** [已确认方案](../../research/2026-11-06-inspect-treasure-review.md)及其开发依据。基线 fac27bf。

## Global Constraints

- 保留 default/full，新增 summary；省略 description、整个 hover_tips 及悬停不可用 note。treasure.relic:null 在 default/summary 保留。无筛选参数。
- 成功详情必须 scene:treasure、screen:{status:visible}，完整校验在投影和刷新许可前。正常基础观察的 covered 宝箱保持。
- 不可悬停的已显示遗物保留 name/enabled，full 的 description:null、hover_tips:[]，以公共来源 treasure.relic 生成 note；default 过滤普通 null。
- 显示读取保留隐藏、透明、容器裁剪与纹理检查，取消视口截断；点击仍核对屏幕位置与原生状态。静态读取不要求房间 Ready。
- 不改变 loot_treasure/proceed 流程，不新增观察前置要求。正式 Mod 不自动安装；验证后本地合入 main。

## Review Focus

1. 静态读取未就绪房间、刚开箱或刚取得遗物时，不能读出尚未揭示／已隐藏身份。
2. summary 不绕过正文、悬停来源或上下文校验；坏响应清除许可，纯读取明确拒绝保留已有许可。
3. 显示、悬停与点击分离后，离屏图标仍可读取但动作不会穿透屏幕；隐藏、透明及裁剪仍生效。
4. 遗物不可悬停时 full/default 正文与 note 一致，summary 只保留静态信息；空遗物的 null 例外保持。
5. 测试扰动门控及恢复可靠；开箱、选择、奖励覆盖、查看工具列表和旧开箱脚本保持正常。

### Task 1: 三项修复、summary 与验证

**Files:**
- Modify: src/Sts2Agent/Observation/TreasureInspection.cs、Adapter/GameAdapter.Treasure.cs、GameAdapter.AvailableTools.cs。
- Modify: src/sts2_mcp/output/treasure_details.py、tool_registry.py；Create: output/treasure_presets.py。
- Create: tests/python/test_treasure_presets.py；Testing/Fixtures/TreasureDisplayFixture.cs，修改测试路由、重置与门控清单。
- Modify: tests/game/verifiers/verify_treasure_inspection_review.py 及其套件、预设目录相关断言；版本及现行文档。
- Create: docs/research/2026-11-06-treasure-inspection-presets-implementation.md 与修复后 JSON。

**Interfaces:** 复用 scene_context、treasure_details(full=False)、HoverAccess.CanFocus、公共 unavailable_hover_sources 与现有纯读取许可。原生 inspect_treasure 仍零参数，summary 为 Python 投影。

- [x] **Step 1: RED。** 新测试覆盖四种矛盾 screen、summary 静态格式与 IPC 零参数、空遗物、不可悬停正文／来源校验、summary 前损坏正文拒绝、参数错误许可保持。运行新测试，预期缺少 summary、上下文和 nullable 正文支持导致失败。
- [x] **Step 2: 实现。** 新增共享读取与详情扩展、明确诊断，接入 available_actions；详情上下文／悬停来源完整校验，接入 summary 投影。更新七场景为新诊断／预设；预期针对性 Python 通过。
- [x] **Step 3: 原生边界设施。** 添加双重门控宝箱显示扰动 no_hover/disabled/offscreen/hidden/transparent/clipped，finally 与局间 reset 恢复。增加 raw 原生读取以在旧 DLL 上证明缺少悬停检查和视口截断，不将注入当作自然复现；更新后验证静态读取及点击拒绝。预期旧产物 RED，最终产物 GREEN。
- [x] **Step 4: 验证。** 完整 Python、124 项 C#、构建／准备后主 GUI，旧 basic/open 宝箱流程及测试入口双模式回归。每次新目录；失败保留证据，先定位后继续依赖步骤。预期全部通过。
- [x] **Step 5: 交付与提交。** Mod 0.71.0、MCP 0.73.0、schema 41；同步文档与已授权 TODO 覆盖，导出完整新样本并核对来源／哈希／链接／退出。提交后一次独立审查，再本地合入 main、删除临时分支，归档并清理本计划工作区。最终命令为证据根 verify_delivery.py。
