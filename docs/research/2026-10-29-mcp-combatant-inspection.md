# 双方 powers 与意图 MCP 接入

当前状态：已完成。共 3 项，已完成 3 项；桥接、文档、完整回归、正式游戏只读验证及独立审阅均通过，无遗留阻塞。

## 范围

新增第六个无参数只读工具 `inspect_combatants()`，MCP server 升至 0.5.0，复用已加载 Mod 0.7.0 的文件操作，不修改或重装 Mod。输出契约以 [战斗对象详情](../development/combatant-inspection.md) 为唯一来源：玩家 powers、敌人 id/name/powers/intents、共享 hover_tips 及 sources；包含敌人意图时附带既有数值 note，不附带卡牌 note。

沿用 `_inspect` 的串行、延迟控制锁及令牌规则。直接查看不能授权动作；已有观察与详情令牌相同则保留权限，状态改变、失败、超时或取消时清除权限。不修改用户 MCP 配置，不执行正式对局动作。

MCP 边界严格校验并投影当前约定字段，保留空数组和不可读的 null；原始额外字段及 notes 不转发，数值 note 由客户端重建。power 计数为整数或 null，意图 value 为字符串或 null，敌人 ID 为 uint32 或 null；名称、标题和 category 可空。sources 只允许引用本次结果中实际存在的具体 power/intent；非法索引、重复来源、重复提示或缺失字段报 transport_error，清除动作权限。校验与投影放入独立模块，避免继续扩大 MCP 传输模块。

## 步骤

1. [x] 先补充真实 stdio 工具发现、无参数与控制锁检查，确认旧实现缺少工具的失败；增加文件 IPC 语义检查，覆盖投影、来源解析、空值、令牌、错误、超时与取消，再实现桥接。
2. [x] 新增 `verify_mcp_combatants.py`，更新其他 MCP 验证脚本的六工具发现断言，同步接口与使用文档；运行完整 Python 回归。
3. [x] 用真实 stdio SDK 在当前正式游戏只读验证 `inspect_combatants → get_observation → inspect_combatants`，核对文件输出、sources、正文、数值 note 与前后状态一致；独立审阅后交付。

## 验证边界

自动检查使用 `.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p 'test_*.py'`，按 Codex socketpair 限制单独申请沙箱外运行。正式验证只发送读取请求，不验证或调用出牌、结束回合等动作。游戏 API 与英语正文沿用 Mod 0.7.0，本轮不重新调研或修改游戏侧。

审阅重点：嵌套内部字段不得泄漏；sources 不能指向手牌、隐藏状态或不存在的数组项；数组不能被压缩；空容器不产生意图 note；失败与取消不能恢复动作权限；首次详情调用必须参与控制锁竞争。

## 验证结果

- 真实 stdio 工具发现先因缺少 inspect_combatants 按预期失败，实现后全套 Python 回归 60/60 通过；无非预期错误。格式错误和超时用例的日志为预期结果。
- Python 3.14.8、官方 SDK mcp==1.26.0 与 MCP server 0.5.0 完成握手，协议 2025-11-25，发现六个无参数工具，新工具标记只读。
- 当前正式战斗完成三次 SDK 调用：inspect_combatants、get_observation、inspect_combatants。两个敌人、三条共享说明，与文件接口相同；文本 JSON 与 structuredContent 相同，详情重复一致，前、中、后观察令牌相同。
- 证据（不纳入 Git）：`.tmp/live/mcp-combatant-inspection.json`、`.tmp/live/mcp-combatant-evidence.json`。
- 独立只读审阅未发现 Critical、Important 或 Minor 缺陷；没有额外调用游戏、IPC 或重复测试。
- 仅修改外部桥接和文档，没有修改或重装 Mod，没有修改 Codex 配置，也没有执行正式对局动作。本轮未重跑其他四份验证脚本的游戏流程，仅更新其六工具发现断言；未重新进行模型自动游玩或其他 agent 客户端验证。
