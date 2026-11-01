# 项目目录整理

当前状态：已完成。共 3 项，已完成 3 项；源码、测试、常用入口及文档已整理，自动检查与真实游戏验证通过，无剩余实施项。未更新正式游戏安装。

## 范围与决定

基线 `ae7f092`。保留 `scripts/mcp_server.py`、`roundtrip_client.py`、`prepare_roundtrip.py`、`run_roundtrip.py`、`gui_suite.py` 的常用 CLI 路径；参数和游戏工具协议保持不变。内部导入迁移到正式 Python 包，不为所有旧内部模块保留转发文件。

生产代码归入 `src/`，测试归入 `tests/`；`scripts/` 只保留常用入口和统一路径引导。Python 包为 `src/sts2_mcp/`，输出校验和各类详情／预设放入 `output/`，服务、会话、通信、配置和截图模块放在包根。包导入不加载 MCP SDK，标准库文件客户端仍可独立使用。入口统一引导仓库与 `src` 路径，不新增安装步骤；测试通过包方式运行。

C# Mod 项目迁至 `src/Sts2Agent/`，按 Infrastructure、Adapter、Observation、Actions、Events、Localization、Testing 归档。`Testing/Fixtures` 和 `Testing/Checks` 仍随游戏内程序集编译，测试模式门控保持原样。命名空间、程序集名和 Mod 标识不变；不在目录调整时拆分游戏适配器或引入新测试框架。纯 C# 检查项目迁至 `tests/csharp/Sts2Agent.Checks/`，继续链接实际无游戏依赖的源文件。

Python 自动检查位于 `tests/python/`；真实游戏验证器位于 `tests/game/verifiers/`，支持代码位于 `tests/game/support/`，套件管理器为 `tests/game/suite.py`，JSON 场景与清单位于 `tests/game/data/`。场景白名单继续同时供 Python 与 C# 嵌入资源使用，logical name 不变。验证器名称不变，套件内部按模块启动，`scripts/gui_suite.py` 保持兼容入口。

同步持续维护文档的命令和链接。历史研究保留原始命令及证据路径；指向迁移源码的 Markdown 链接更新目标，保留其历史语境。本次仅重排目录和导入，不变更功能版本或正式安装。

## 实施与验证

- [x] C# 项目迁移：按职责移动源码，更新纯检查链接、运行时准备脚本及其临时安装测试，增加根 solution；构建、60 项纯 C# 检查、371 项 Python 检查和真实动作链加载通过。
- [x] Python 迁移：按上述位置搬迁并改为包导入；修正配置默认根目录、子进程入口、验证器资源和 C# 嵌入资源；完整 Python 测试、全部模块导入及仓库外工作目录 CLI 验证通过。
- [x] 整体验证：重新构建并运行纯 C# 检查、隔离 GUI 套件；核对 SDK 图像、场景白名单、检查入口、动作许可和配置默认路径；同步文档并完成只读审阅。

重点检查：绝对脚本路径在仓库外工作目录仍可启动；标准库客户端不依赖 MCP；所有可复用验证器由新模块路径启动；临时安装测试使用新构建输出；C# 链接源与嵌入资源无遗漏；现有客户端无需更改配置。新的自动检查入口为 `python -m unittest discover -s tests -t . -p 'test_*.py'`，实际结果在完成后记录。

现代 SDK 默认递归包含项目目录下的 C# 文件，目录整理不要求改变类型名或命名空间；参见 [.NET SDK 默认项](https://learn.microsoft.com/en-us/dotnet/core/project-sdk/overview)。

## 阶段验证记录

C# 阶段证据位于 `.tmp/2026-11-02-project-layout/`：`csharp-build-single.log` 构建成功且无警告／错误，`csharp-checks.log` 为 60 项纯检查，`csharp-python.log` 为 371 项 Python 检查（34.083 秒），`csharp-gui/report.json` 为真实动作链通过且自有游戏进程已退出。沙箱内 solution 默认并行构建曾无错误明细地返回失败；改用 `-m:1` 后成功，未改变项目代码以绕过该失败。

C# 阶段提交为 `5f32b39`。Python 迁移后全量 371 项通过（32.715 秒），日志为 `python-migration.log`。35 个包／实现模块和 60 个游戏验证器全部可导入；五个常用 CLI 在仓库外工作目录下均可显示帮助，其中标准库文件客户端使用 `python3 -S`，不加载第三方依赖。运行时源码除导入和默认配置根目录定位外，AST 与迁移前一致；完整构建和 60 项纯 C# 检查再次通过，证明搬迁后的嵌入场景资源可用。

最终 `final-gui/report.json` 中 6 项全部通过：完整动作链、反伤与死亡来源、战斗交接原生检查、地图预设、永久卡牌变化、充能球事件。所有验证器按新模块路径运行，测试自有进程已退出。DLL SHA-256 为 `0e9d0573ac164924b721e3b252472097f917a5fb39bea7db29a83a105d7f5072`，与构建产物、隔离运行时及报告一致；汇总见 `verified-summary.json`。

只读审阅未发现已确认的严重或重要功能问题，指出一处文档仍用文件路径直接启动已迁移测试；已改为 `python3 -m tests.python.test_prepare_roundtrip`，实际运行通过，日志为 `documented-prepare-check.log`。维护文档的源码链接及当前命令已更新，历史记录保留旧命令的适用基线。测试源码计数仍为 128 个 C# Mod 文件、37 个 Python 测试模块、60 个游戏验证器；`scripts/` 从 138 个文件降为 6 个 Python 文件（5 个常用入口及 1 个引导模块）。
