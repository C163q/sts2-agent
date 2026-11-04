# 遗物工具核验样例

对应[场景审阅](../2026-11-04-inspect-relics-review.md)。本目录保存 25 份完整公开 JSON；调用参数、证据类型、原文件及条目位置、SHA-256 和采样版本见 [manifest.json](manifest.json)。

- `recorded_mcp_response`：真实 stdio MCP 的完整公开返回；不可悬停样本由测试夹具关闭输入入口。
- `recorded_native_full_projection`：真实原生响应经当前 full 规则投影；原 MCP 使用 default，不把投影参数冒充原调用。
- `recorded_payload_projection`：真实完整公开返回经当前筛选规则回放，未重新请求游戏。
- `implementation_constructed`：按实现整理的空集合结构，不代表新增实测。
- `simulated_transport_or_local_validation`：实际调用公开参数／错误处理，但游戏传输为模拟；用于核对错误消息和许可恢复。

`combat.summary.json` 展示现有摘要，其余成功文件为 full。格式化以外不删改真实完整返回；不同采样版本分别记录，未合并为同次快照。样例不代表已接受新的状态字段或已经修复错误说明。
