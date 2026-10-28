# MCP 启动控制锁修复记录

## 适用基线与问题

仓库基线 `4881810`、MCP server 0.1.0、Python SDK `mcp==1.26.0`、Codex CLI 0.165.0。正常游戏配置指向 `.tmp/live/ipc`。

Codex 在启动新会话时报告 `handshaking with MCP server failed: connection closed: initialize response`。本机 Codex 日志数据库 `~/.codex/logs_2.sqlite` 的 `codex_rmcp_client::stdio_server_launcher` 记录了实际退出原因：`Another MCP controller already owns this IPC directory`。

`lsof` 核实旧 MCP 进程由 Codex 后台进程启动，已经持有该目录的控制锁。0.1.0 在处理初始化前取得进程锁，导致仅预热工具的后台连接也独占游戏，后续会话无法完成握手。该表现可通过持锁时启动第二个 stdio 客户端复现，与游戏是否启动、Python 依赖和网络无关。

## 修复行为

- MCP server 版本为 0.1.1；初始化和列出工具不申请控制锁。
- 首次 `get_observation` 非阻塞申请锁，成功后持有到服务退出；同一控制者可重复读取。
- 已有控制者时返回英语结构化 `controller_busy`，恢复指引为 `disconnect_other_client`，不发送游戏请求或断开 MCP 连接。原控制者退出后，等待者可在原连接重新观察。
- 仍保留一个实际控制者、动作前显式观察和令牌消耗要求。没有增加多个 agent 同时控制游戏的能力。
- 只关闭本机已确认的旧版 MCP 预热进程以释放旧锁，没有关闭 Codex、启动游戏或执行战斗动作。

## 验证

- 修复前新增测试复现了持锁时初始化连接关闭，以及空闲握手连接抢占锁；修复后回归通过。
- Python 全量检查 18 项通过：原有动作、取消和过滤检查继续通过；新增空闲连接不占锁、持锁仍可握手且释放后恢复、两个真实客户端只允许一个控制者且断开后可接管。
- 使用本机 `~/.codex/config.toml` 的实际 `sts2` 命令与参数，完成真实 stdio 初始化和工具发现；返回 `sts2-agent` 0.1.1，工具为 `get_observation` 和 `end_turn`。验证时旧控制锁仍在，未调用游戏工具。证据 `.tmp/mcp-startup-evidence.json`。
- 使用真实配置启动新的临时 Codex 会话，要求 `sts2` 初始化成功，并通过工具发现确认 `mcp__sts2__get_observation` 和 `mcp__sts2__end_turn` 可用；未调用游戏工具。证据 `.tmp/codex-mcp-discovery-events.jsonl`、`.tmp/codex-mcp-discovery-result.txt`。
- 独立代码复审未发现其他必须修复的问题，并再次运行全部 18 项检查通过；59 个 Markdown 本地链接、代码块围栏、Python 语法与 Git 空白检查通过。
- 不修改 Mod；首次接入时的真实游戏与模型验证见 [MCP 实施记录](2026-10-29-mcp-plan.md)。此次仅针对启动、控制锁和原有协议行为复测，不重复操作正式游戏。
