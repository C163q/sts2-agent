# Mod 接入基线调研

核对日期：2026-10-28。范围为本机 Linux Steam 安装的静态文件和下列上游资料；未启动游戏、加载 Mod、反编译程序集或验证动作执行。

## 本地证据

游戏安装目录为 `~/.local/share/Steam/steamapps/common/Slay the Spire 2`。下表文件路径均相对于该目录。

| 文件 | 核对结果 |
| --- | --- |
| `release_info.json` | 版本 `v0.107.1`，分支 `v0.107.1`，提交 `59260271` |
| `data_sts2_linuxbsd_x86_64/sts2.dll` | 游戏程序集存在，具体接口仍需进一步检查 |
| `data_sts2_linuxbsd_x86_64/sts2.runtimeconfig.json` | 目标框架 `net9.0`，包含 `Microsoft.NETCore.App` 运行时 `9.0.7` |
| `data_sts2_linuxbsd_x86_64/GodotSharp.dll` | Godot C# 绑定程序集存在 |
| `data_sts2_linuxbsd_x86_64/0Harmony.dll` | Harmony 程序集存在，不据此推断具体补丁兼容性 |
| `data_sts2_linuxbsd_x86_64/sts2.xml` | 包含 `MegaCrit.Sts2.Core.Modding.ModInitializerAttribute`、`ModManager.Initialize` 等成员文档，以及 `MegaCrit.Sts2.Core.Commands.CardCmd` 的部分命令文档 |

这些证据支持优先调查 C# Mod 接入，并表明游戏自带 Mod 加载相关入口。XML 成员说明不能代替编译和运行验证，也不能据此认定存在完整、稳定的外部控制 API。上述运行时信息不等于已经选定开发工具链。

## 上游资料与作用

| 来源 | 可支持的结论 |
| --- | --- |
| [BaseLib 仓库](https://github.com/Alchyr/BaseLib-StS2) | 供其他 Mod 依赖的社区基础库，定位包含内容扩展；具体能力需核对所选版本 |
| [ModTemplate-StS2](https://github.com/Alchyr/ModTemplate-StS2) | 社区 Mod 模板；其 README 说明空 Mod 模板默认依赖 BaseLib，也允许移除该依赖 |
| [RitsuLib 仓库](https://github.com/BAKAOLC/STS2-RitsuLib) | 提供生命周期、Harmony 补丁、持久化、UI、诊断等共享能力；其 README 说明与游戏 API、BaseLib 等并用 |

此处核对的是调查时的仓库页面，尚未固定依赖版本或提交，也未证明它们与本机 `v0.107.1` 兼容。正式选型时须补充版本、许可证及具体 API 核验，不能直接照搬上游当前分支。

## 对项目方向的判断

建议优先用游戏内 C# Mod 读取状态和执行动作，在外部提供结构化工具接口，再连接 LLM。社区库按具体需要引入；暂不确定是否依赖 BaseLib、RitsuLib，也不确定是否采用 MCP。

首个验证应缩小到一次“读取状态 → 执行合法动作 → 读回结果”的完整往返。在接入 LLM 前，先使用确定性的客户端排查 Mod 加载、通信及游戏动作流程。

## 后续需要验证

- 当前版本 Mod 的初始化签名、清单格式、文件布局、打包和实际加载方式。
- 适用的 .NET SDK、Godot 版本及本地程序集引用方式。
- 状态读取位置、玩家可见信息的范围，以及可执行动作的枚举方式。
- 正常动作入口、Godot 主线程调度、异步动作完成及场景切换时机。
- 无效、重复或过期请求的处理，以及断线和超时后的恢复方式。
- 各社区库对目标游戏版本的兼容性及引入后能解决的具体问题。
