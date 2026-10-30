# 可配置截图工具验证

## 基线与结论

2026-10-30 核对 Linux 游戏 `v0.107.1`，分支 `v0.107.1`、提交 `59260271`，RitsuLib `0.6.10`；本次 Mod `0.17.0`、MCP `0.14.0`。已完成默认关闭/启动启用、PNG 保存、权限边界、独立图形游戏和 headless 拒绝验证。实际接口见[截图指南](../development/screenshots.md)，配置与结果不依赖开发者的机器路径。

采用 JSON 配置，复用 Python 标准库并保持 Python 3.10 下限；不引入 TOML 解析依赖。配置只在启动时读取，默认 20 工具、启用后 21 工具。截图为显式调用，游戏视口保留原语言与分辨率；模型仅收到保存路径和尺寸。

## API 证据

- 目标程序集为游戏目录 `data_sts2_linuxbsd_x86_64/GodotSharp.dll`，核对 `Godot.Image.IsEmpty/GetWidth/GetHeight/SavePngToBuffer`、`Godot.Viewport.GetTexture` 与 `Godot.Texture2D.GetImage`。
- 本项目 `BridgeMod.Attach/Pump` 的图形采样已在 `RenderingServer.FramePostDraw` 上运行；`ViewportCapture.Read` 复用该时机，不请求额外帧或执行 UI 动作。
- 现有 `TestCapture.Save` 已使用同一视口读取路径；RitsuLib 源码提交 `772f280964f2efc7c7e2f29fc59844e68616dd57` 的 `src/Diagnostics/SelfCheckBundleWriter.Artifacts.cs:CaptureScreenshot` 使用 `GetImage` 和 `SavePngToBuffer`。本次不调用社区库的自检导出流程。
- PNG 经内部文件 IPC 返回，外部进程校验尺寸、大小、块校验和及完整结束，再使用临时文件与独占硬链接发布。模型结果不含 PNG 数据、状态令牌或原始包装。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| Python 全套 | 158 项通过，其中本次 11 项；覆盖真实 stdio 启动、配置固定、文件名、禁止覆盖/符号链接、载荷与权限/取消 |
| C# 边界与缓冲 | 原有 8 项通过 |
| Mod 构建 | 0 警告、0 错误；编译产物与游戏验证运行时一致 |
| 图形游戏/真实 stdio | 21 工具；保存主菜单、战斗、选牌、查看战场、返回选择、返回战斗、下一回合、地图、牌组和返回地图，共 11 张 PNG，含自动文件名 |
| 动作衔接 | 喝技能药水进入选牌；原生跳过恢复战斗；结束回合由 1 到 2，HP 80 到 73；截图既不授予权限，也不在状态不变时消耗旧权限 |
| 保存边界 | 同名返回 `file_exists`，旧内容不变；目录穿越参数拒绝；返回文本与 `structuredContent` 一致 |
| 独立代码审阅 | 未发现 Critical、Important 或 Minor 问题；只读核对代码及既有证据 |
| headless | 明确 `screenshot_unavailable`，不创建截图目录或动作许可 |
| 画面人工核对 | 查看选牌、战场、地图及牌组 PNG，1280×720、显示范围与对应界面一致，保留游戏内提示，不扩大可见范围 |

未给 RitsuLib 的待审遥测申请授权。游戏内提示属于当前视口画面，截图不会将它隐藏。

## 验证时序与限制

选牌入场动画结束时，`select_card` 会从禁用变为可用，因此原始观察令牌可以在纯截图前后变化。验证脚本先等待静态观察稳定再比对；产品工具不等待动画结束，保留调用时实际画面。

本次测试战斗尚无正式地图当前节点，原生地图没有返回入口；因此在打开地图前先完成回合验证，牌组关闭后验证地图仍保留。没有为测试直接修改地图或绕过原生关闭规则。

证据位于忽略目录 `.tmp/2026-10-30-screenshots/`：`python.log`、`csharp.log`、`build.log`、`graphical.json`、`headless.json`、两组游戏日志及 `captures/`。初次动画和地图顺序检查的失败记录保留在该目录的 `initial-*` 子目录，未当作产品通过证据。

本次图形实例为英语界面、1280×720；未重新验证中文界面、其他渲染后端/游戏版本、超大分辨率、最小化/后台节流、非硬链接文件系统或真正多人联机。截图工具不处理客户端的视觉输入，也未让实际 LLM 完成整场战斗；这是后续易用性评估，不能用本次固定脚本的通过替代。
