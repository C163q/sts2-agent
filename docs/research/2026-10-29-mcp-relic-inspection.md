# 遗物详情 MCP 接入记录

当前状态：实施完成。共 3 项，已完成 3 项；七工具实现、回归、正式游戏真实 stdio 采样、独立审阅及文档同步均完成，无遗留或阻塞。

## 方案与边界

基于已验证的 Mod 0.8.0 文件操作 `inspect_relics`，新增第七个无参数只读 MCP 工具 `inspect_relics()`，服务升级至 0.6.0。输出沿用 [遗物详情格式](../development/relic-inspection.md)，不修改 Mod、不重启游戏、不改客户端全局配置、不执行正式游戏动作。

复用 `GameTools._inspect` 的串行请求、控制权和令牌规则：直接查看不授权动作；相同令牌保留已有显式观察，变化、失败、超时、取消时清除。读取只发一条文件请求，不自动重试。协议文本与 `structuredContent` 内容一致。

成功响应仅投影 `relics`；各项仅保留 `name/counter/description/hover_tips`，附带提示仅保留 `title/description`。校验数组及必需字段、可空名称、字符串正文、可空有符号 32 位整数计数，拒绝布尔计数。异常按现有规则输出脱敏错误。客户端再将附带提示共同去重到平级，以 `relic_indices` 关联，不产生数值 notes。

## 步骤

- [x] 1. 先补充测试并确认失败：七工具发现、只读注解、无参数、精确投影和共享解释、空列表和计数边界、错误/超时/取消、控制权竞争及动作令牌保留或失效。
- [x] 2. 新增 `scripts/relic_details.py` 并接入 `mcp_server.py`；更新既有验证脚本的工具发现列表，运行 Python 全套回归。新增 `verify_mcp_relics.py`，通过真实 SDK stdio 执行 `inspect_relics → get_observation → inspect_relics`，核对文件 JSON 一致、关联完整及前后状态不变。
- [x] 3. 独立审阅并同步 README、MCP 指南、信息边界及遗物指南；记录验证结果，提交本次变更。

## 核对基线

游戏 Linux `v0.107.1` main commit `59260271`，已加载 Mod 0.8.0；本次复用文件接口，不新增游戏 API。依赖固定 `mcp==1.26.0`，本机 Python 3.14.8。服务基线 0.5.0，已有六工具及 62 项 Python 测试。原始文件契约见遗物指南及 `spikes/roundtrip/RelicInspection.cs`；MCP 生命周期依据当前 `mcp_server.py` 和已安装 SDK。

## 验证关注点

隐藏或缺失字段不得从其他响应补齐；空数组必须有效；计数 0 不变成未知；同名异文解释分别保留；额外内部字段不能穿透嵌套投影；失败及取消不能恢复旧动作授权；新工具首次读取遵循相同控制锁。真实采样只读，无法穷举全部遗物及其他 agent 客户端。

## 验证结果

- 新增工具发现测试先因缺少 `inspect_relics` 失败，日志为 `.tmp/mcp-relic-red.log`。实现后 Python 全套 71 项通过，11.877 秒，日志为 `.tmp/mcp-relic-tests.log`；错误输入及超时用例产生的诊断符合预期。MCP/AnyIO 测试在允许 socketpair 的沙箱外执行。
- 新增 9 项工具测试覆盖精确输出、共享解释、空数组、可空文本、有符号 32 位计数、必需字段错误、嵌套额外信息过滤、源数据不变、同名异文、令牌保留与失效、错误脱敏、无重试及取消。真实 stdio 自动测试覆盖七工具发现、无参数限制、文本与结构化输出一致、控制权竞争，以及遗物首次读取取得控制权和断开后的恢复。
- 正式游戏通过真实 SDK 完成 `inspect_relics → get_observation → inspect_relics`，握手协议 `2025-11-25`，server `0.6.0`，工具数 7。取得 Burning Blood 和计数 2 的 Silver Crucible，无原生附带解释；与文件接口结果一致，重复读取及前后基础观察令牌一致。
- 面向 LLM 的 JSON 保存于 `.tmp/live/mcp-relic-inspection.json`，完整协议与文件对照证据保存于 `.tmp/live/mcp-relic-evidence.json`。没有执行正式游戏动作，没有修改用户禁用的全局 Codex MCP 配置或 Mod。
- 持续文档本地链接及 `git diff --check` 通过。既有五个验证脚本只更新工具发现集合，本次没有重复执行其中的独立游戏动作流程。

独立审阅未发现 Critical 或 Important 问题；发现 MCP 错误表格中工具数仍写六个的 Minor 文档问题，已改为“所有工具”，与七工具实现一致。

范围限制：正式采样没有附带解释，共享解释与计数边界由自动检查覆盖；没有重新进行真实模型自动游玩或其他 agent 客户端验证。现有 Mod 的场景和可见性限制不变。
