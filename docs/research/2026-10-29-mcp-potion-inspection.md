# 药水详情 MCP 接入

当前状态：已完成。共 3 项，已完成 3 项；桥接、文档、自动检查、正式游戏只读验证和独立审阅均完成，无遗留阻塞。

## 范围与接口

在已有文件操作和 Mod 0.6.0 的基础上新增无参数只读工具 `inspect_potions()`，MCP server 升至 0.4.0。JSON 契约以 [药水详情](../development/potion-inspection.md) 为唯一来源：通用栏位说明一份、空槽保留 `null`、共享解释按标题和正文去重，并以从 0 开始的 `slot_indices` 关联。

复用 `GameTools._inspect` 的串行处理、延迟控制锁和动作令牌语义。直接查看不能授权动作；已有观察与详情的令牌一致时保留原权限，状态变化、失败或取消时清除权限。不增加使用或丢弃药水的动作，不修改用户 MCP 配置，不修改或重装 Mod。

MCP 边界先校验必需字段和类型，再只投影 `slot_tip.title/description`、`potion_slots[].name/description/hover_tips[].title/description`。名称和标题允许原生可空值，正文必须为字符串；逐药水提示必须为数组。缺失、格式错误或不可读的响应返回结构化错误，不把未知槽位当成空槽。不转发多余状态、内部字段、数值 notes 或动作列表。

## 实施顺序

1. [x] 为药水查看、去重与位置、令牌保留及失效、错误和取消、严格字段投影补充文件 IPC 检查；扩展真实 stdio 工具发现、无参数约束和控制权竞争检查。先确认新增工具尚未发现的失败，再实现桥接。
2. [x] 新增只读 SDK 验证脚本，更新现有验证脚本的五工具断言，同步当前接口文档。运行完整 Python 自动检查。
3. [x] 通过真实 stdio MCP 读取正式游戏，核对文本与结构化内容一致、输出与文件接口一致、槽位与基础观察一致、读取前后观察不变；独立审阅后交付本次变更。

## 验证与边界

自动检查命令：`.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p 'test_*.py'`。Codex 沙箱的 socketpair 限制要求此命令独立申请沙箱外执行。

真实游戏验证只调用读取工具，不执行动作。药水游戏 API 继续沿用 Mod 0.6.0 已核实实现，本轮不新增游戏 API 调用。测试替身覆盖重复 Block 解释和空槽，真实采样内容以实际场景为准。

审阅重点：多余嵌套字段不泄漏；空槽不能压缩；缺失字段不能静默省略；错误和取消不恢复动作权限；首次药水查看参与控制锁竞争。

## 验证结果

- 新工具接入前，真实 stdio 工具发现断言因缺少 `inspect_potions` 按预期失败；实现后完整 Python 检查 51/51 通过。格式错误与超时用例产生预期日志，无非预期失败。
- 官方 Python SDK `mcp==1.26.0` 与 MCP server 0.4.0 完成初始化，协议为 `2025-11-25`，发现五个无参数工具，药水工具标记只读。
- 正式游戏 Mod 0.6.0 已加载；只读执行 `inspect_potions → get_observation → inspect_potions`，取得 Skill Potion 和空槽，与文件读取一致。文本与结构化内容一致，重复读取一致，前后观察令牌一致。未调用游戏动作，未重装或修改 Mod，也未修改 Codex 配置。
- 证据：`.tmp/live/mcp-potion-inspection.json`、`.tmp/live/mcp-potion-evidence.json`；均不纳入 Git。
- 独立审阅未发现 Critical、Important 或 Minor 缺陷；审阅只读核对代码、文档及落盘证据，没有额外调用游戏或 IPC。
- 本轮未重跑模型自主结束回合、其他 agent 客户端或全部药水类型。原有三份 MCP 验证脚本仅更新五工具发现断言，未重新执行其游戏流程。
