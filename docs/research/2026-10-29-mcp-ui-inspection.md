# 界面说明 MCP 接入记录

当前状态：已完成，共 3 项。MCP 接入、38 项回归、正式战斗只读采样及独立审阅均已完成，随本记录提交交付。无需更新已加载的 Mod 0.5.0，客户端禁用配置未修改。

## 范围与接口

基线为项目 `3abb4fc`，游戏 `v0.107.1`、Mod `0.5.0`、Python SDK `mcp==1.26.0`。已确认的 JSON 格式见 [界面说明](../development/ui-inspection.md)。本次增加无参数、只读 MCP `inspect_ui()`，直接复用文件接口 `inspect_ui`；不扩展游戏侧读取或支持场景，server 升为 `0.3.0`。

返回仅含 `scene` 和 `hover_tips`；提示只保留 `title/description/sources`，不传输额外游戏状态、控制元数据或数值解读 notes。校验当前 `scene == combat`、提示数组与各字段类型，畸形响应转为结构化 `transport_error`。空提示数组合法。

控制锁、串行执行及动作令牌规则与 `inspect_hand` 共用：直接查看不授权动作；已有观察与读取返回令牌相同才保留原权限；状态变化、失败或取消均清除权限。初始化、发现工具不抢锁，忙碌时不发送游戏请求；参数严格拒绝，MCP 文本与结构化内容一致。

## 实施步骤

1. 已完成回归先行：补 FakeGame 的界面响应与读取测试，覆盖直接读取、空结果、保留/清除令牌、取消、畸形字段及多余字段过滤；更新真实 stdio 的四工具发现、只读标注、严格参数和控制锁检查。先确认新增能力缺失导致失败。
2. 已完成接入：共享只读详情的令牌处理，增加输出投影和校验、工具声明与路由；保持原有工具行为。同步两个现有 MCP 验证脚本的工具集合，新增只读 `verify_mcp_ui.py`。
3. 已完成验证交付：全量 Python 回归，通过 SDK stdio 调用正式战斗的 `inspect_ui → get_observation → inspect_ui`，确认格式、协议响应、与文件接口相同及前后状态令牌一致。使用说明已更新，独立审阅无阻断问题，单独执行 Git 暂存及提交。

## 验证边界

正式战斗只执行读取，结束回合的令牌兼容性使用 FakeGame 验证；不进行正式游戏动作，不改 Codex 配置，不重新构建或重启游戏。客户端需要重载连接才能发现新增工具；手动禁用的连接仍保持禁用。地图等场景、药水、遗物、powers 和敌人意图解释保持原范围。

## 验证证据

- 新测试先确认 `inspect_ui` 方法及工具声明缺失导致失败；实现后 `.tmp/mcp-venv/bin/python -m unittest discover -v -s scripts -p 'test_*.py'` 的 `38/38` 项通过。
- 真实 SDK stdio 初始化返回 server `0.3.0`、协议 `2025-11-25`，发现四个无参数工具，`inspect_ui` 标记只读。
- `.tmp/mcp-venv/bin/python scripts/verify_mcp_ui.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-ui-inspection.json --report .tmp/live/mcp-ui-evidence.json` 读取正式战斗的 `13` 条英语提示，与文件读取结果完全相同。文本和 `structuredContent` 一致，正式战斗前、参考读取及最终观察的令牌一致。
- SDK 验证只调用 `inspect_ui/get_observation/inspect_ui`，没有执行结束回合或其他游戏动作。测试子进程正常退出，控制锁随连接结束释放。
- 本次实际采样为进阶 `6`、楼层 `3`、第 `1` 回合、生命 `65/80` 的战斗，敌人为 Leaf Slime (S)、Twig Slime (M) 和 Twig Slime (S)。
- 本次没有重新运行独立游戏的回合往返脚本或真实模型自动游玩；两个旧验证脚本仅同步四工具发现集合。原有手牌与动作行为通过临时 IPC 及真实 stdio 回归覆盖。
