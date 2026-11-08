# 在正常游戏中加载 Mod 并读取状态

本文说明 Linux Steam 游戏的安装、通信配置及更新排错。当前版本与依赖基线统一见[项目 README](../../README.md#当前版本与前提)，工具与字段见[开发文档索引](README.md)。独立测试实例另按[最小流程验证指南](roundtrip.md)准备；以下操作用于正常游戏的 Mod 存档环境。

## 安装文件

按[路径配置](roundtrip.md#路径配置)在当前终端加载 `.env`，再按[构建指南](roundtrip.md#前提与构建)生成产物。退出游戏后，在仓库根目录分别执行：

```sh
mkdir -p "${Sts2Dir:?请先配置并加载 .env}/mods/Sts2Agent"
```

```sh
cp src/Sts2Agent/bin/Debug/net9.0/Sts2Agent.dll src/Sts2Agent/bin/Debug/net9.0/Sts2Agent.json "${Sts2Dir:?请先配置并加载 .env}/mods/Sts2Agent/"
```

DLL 与清单必须来自同一次构建。已有 Steam 创意工坊管理的兼容 RitsuLib 时保留该安装，不再复制另一套。

手工安装依赖时，按[构建指南](roundtrip.md#前提与构建)获取完整发布包，将整个解压目录放入 `<游戏安装目录>/mods/STS2-RitsuLib/`，保留 `shared/`、`compat/`、`assets.zip` 等全部内容。

启动游戏，在 Mod 界面启用依赖和清单中名为 `STS2 Agent Roundtrip Spike` 的本项目 Mod，并按提示重启。运行中的游戏不会热加载新 DLL。

## Steam 启动配置

在游戏“属性 → 通用 → 启动选项”中设置通信目录，把示例路径替换为实际绝对路径：

```text
env STS2_AGENT_IPC_DIR="/absolute/path/to/sts2_agent/.tmp/live/ipc" %command%
```

保留 `%command%` 和已有启动设置；包装方式见[Steam 支持说明](https://help.steampowered.com/en/faqs/view/145A-FE54-F37B-278A)。修改后完整重启游戏。正常游戏不设置 `STS2_AGENT_TEST_MODE=1` 或其他测试夹具变量。

## 读取敌人

在仓库根目录执行一次当前状态读取：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state
```

无遮挡战斗使用 `scene:"combat"`，`enemies` 提供当前可见敌人；被覆盖时不补出隐藏战场。主菜单没有敌人，`enemies:null` 属于正常结果。该文件客户端默认保留空值，加 `--raw` 可查看原始响应及状态令牌；字段见[游戏基础观察 JSON](observation.md)。每次命令只读取一次，不提交游戏动作。

LLM 接入另按[MCP 指南](mcp.md#安装与游戏前提)安装 Python 依赖并配置 stdio 服务；`--ipc-dir` 必须与上述游戏侧目录一致。连接检查以成功读取当前游戏观察为准。

## 更新与排错

- 更新 Mod：退出游戏，构建并替换 DLL／清单，完整启动游戏。更新 Python 或 MCP 配置：重连客户端。两端有配套变更时同时更新；工具描述来自 Python，不能据此判断游戏内 DLL 版本。
- 请求超时：检查游戏是否运行、Mod 是否启用并重启、启动变量是否生效，以及双方通信目录和权限。动作超时后先读取实际状态，禁止自动重发，见[MCP 错误语义](mcp.md#调用和错误语义)。
- 游戏日志出现 `[Sts2Agent] Main-thread pump attached.` 表示主线程通信入口已连接；`STS2_AGENT_IPC_DIR is unset, bridge disabled.` 表示环境变量未传入游戏。
- 字段或场景与预期不符：先核对安装清单、游戏启动日志和 `get_state --raw` 中的 schema，再与[底层结构版本](observation.md)及[兼容基线](../../README.md#当前版本与前提)比较。排查时同时核对运行进程的启动时间与已安装 DLL。

例如，旧 DLL 可能已能输出附魔的悬停效果，却没有基础观察／summary 的结构化附魔字段；此时只更新 Python 无法补齐游戏端读取，实例见[r9 版本核查](../research/2026-11-02-r9-enchantments.md)。
