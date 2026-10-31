# MCP 动作结果精简实施计划

当前状态：完成。共 2 项，已完成 2 项；280 项 Python 测试、24 项 C# 检查及最终 DLL 的 10 类图形回归通过，Mod 已备份安装，无剩余实施项。使用时完整重启游戏并重连 MCP；长期 LLM 行为评估留待后续。

> 使用 `superpowers:executing-plans` 在当前会话实施；设计已经用户授权，无需重复确认。沿用当前 checkout 的独立功能分支和隔离游戏运行目录，保留调研证据。

**目标：** 游戏动作返回精简回执，保留完整内部校验和连续动作许可。

**架构：** 新建 `scripts/action_output.py`，在 `GameTools._action` 完成校验与许可处理后投影公开结果。观察、详情、视图的输出不变；`CardSelection.cs` 与 `RestSiteInspection.cs` 补查已复现的有限 UI 淡出。

**技术栈：** Python、unittest、MCP stdio、已有隔离 Godot 游戏。

**设计：** [动作结果精简设计](../specs/2026-11-01-compact-actions-design.md)。

## 约束与审阅重点

- 保留完整 `transition`、必要交互提示及购买/领奖回执；零额外参数，MCP `0.28.0`、Mod `0.33.0`、schema `16`。
- 坏响应的已省略字段仍须验证；异常、取消、外部变更不得恢复许可。
- 连续选择、确认、升级预览改用专项详情；占卜无无效图像提示或媒体泄漏。
- `get_observation` 的预设、视图副作用及只读工具的许可规则不变。
- 测试脚本不能凭旧的完整动作结果假设读取新回执中已删除的字段。
- 锻造取消预览已连续两次复现过期，诊断前后唯一差异为 `selection.cards[0].outline: cyan → none`；修复为等待当前可见网格牌 `NCardHighlight._curTween`，不放宽令牌或重试失败动作。回到火堆后的第二处过期已定位为说明文字 1 秒淡出，另在 RestSiteInspection.Ready 补查 `_descriptionTween`。须使用最终 DLL 重新验证选择、动作链及相邻场景，并备份安装 Mod。

## 任务

- [x] **1. 输出投影与契约：** 先在 `test_action_observations.py` 补充精简字段、完整事件、交互提示和坏响应测试并确认失败；实现 `action_result(payload)`，在 `_action` 最后返回处调用。更新 stdio、购买/领奖、占卜测试及 `mcp_catalog.py` 提示、server 版本。运行完整 Python 测试，期望全部通过。同步持续维护的接口说明与示例。
- [x] **2. 验证与交付：** 更新受影响的 `verify_*.py`，使用真实 MCP 查看所需详情，不通过隐式恢复完整动作结果绕过契约。隔离图形实例验证动作链、选牌、药水、购买/领奖和占卜；记录当前回执示例及字符数。完成独立审阅、处理发现、文档链接与差异检查，提交并本地合入 main，备份安装 Mod `0.33.0`；完整重启游戏并重连 MCP 后生效。
