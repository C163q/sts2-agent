# MCP 工具列表与场景可用性

核对日期 2026-10-29。本次仅回答协议及设计问题，没有实现动态工具列表，也没有修改客户端配置。

## 协议事实

- 当前项目真实协商的是 `2025-11-25`，依赖 `mcp==1.26.0`。该版 [工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) 定义了 `tools/list`、`tools.listChanged` 能力和 `notifications/tools/list_changed` 通知；服务可通知客户端重新发现工具。
- 较新的 [2026-07-28 工具规范](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) 同样允许列表随时间变化，但明确禁止按连接改变集合，或把改变集合作为同一连接其他请求的副作用；授权范围差异单独允许。因此不能将协议的动态发现能力笼统解释为任意按请求步骤增删工具。
- 协议的工具发现通知，不等于已经验证某个 agent 会立即把更新后的工具集合交给下一次模型调用。第三方客户端的实际刷新和过滤方式仍需分别验证。

## 当前实现与本地证据

`scripts/mcp_server.py` 的 `list_tools` 固定返回七个工具，调用时检查状态合法性；尚未接入牌组的 MCP 工具。服务使用默认初始化选项，不声明动态列表变更能力，也不发送变更通知。

已安装 SDK 的 `mcp/server/lowlevel/server.py` 中，`NotificationOptions.tools_changed` 默认为 `False`，`get_capabilities` 将它映射至 `tools.listChanged`；`mcp/server/session.py` 提供 `send_tool_list_changed`。这些是服务器实现能力，不是现有项目已经启用的行为。

## 设计建议，尚未实施

优先保留稳定的 MCP 工具集合，在观察结果中列出当前场景允许的操作，并在调用时重新校验。牌组页可以提示关闭牌组，战斗页可以提示结束回合；错误页面、旧状态、等待期间变化均由游戏端拒绝。工具列表本身不能替代合法性检查。

若目标是减少送给 LLM 的工具数量，自行实现的 agent 可以在每次模型调用前按场景过滤提供给模型的工具；服务器仍维护完整接口。接入第三方 agent 时，应先验证其支持程度。此建议区别于服务器随 `inspect_deck` 等调用反复增删 MCP 工具，尚未确定为项目最终实现。
