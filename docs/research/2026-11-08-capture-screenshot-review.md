# capture_screenshot 核验与建议

> 当前状态：三项整改、验收及独立审阅单轮修复完成并合入main；下文现状和9份样例保留b104d84审阅基线。总进度见[工具清单](2026-11-02-mcp-tool-review.md)。

修复后的规则、实际返回与验收见[实施记录](2026-11-08-screenshot-recovery-implementation.md)。

本工具用于把当前游戏视口保存为PNG，便于记录和对照游玩过程。输出是本地文件位置及尺寸；客户端读取该文件后才能将其作为视觉输入。源码和验证边界见[开发核验](2026-11-08-capture-screenshot-development-notes.md)，返回见[9份实际JSON](2026-11-08-capture-screenshot-examples/README.md)。

## 优先处理的问题

| 问题 | 优先级与影响 | 建议 |
| --- | --- | --- |
| 1. 本地保存错误撤销已有操作许可 | 中：同名文件或保存目录错误均未改变游戏，随后end_turn仍要求重新观察。成功截图却可在同一状态下保留许可。 | 原生取图成功、响应有效且采样令牌与旧许可一致时，本地保存错误也保留旧许可；首次调用、状态改变、取消、坏响应、取图失败或未知结果继续沿用保守规则。 |
| 2. 错误原因不能指导纠正 | 中：保存目录是文件、文件名超过文件系统长度限制，都只提示检查目录／权限／空间；工具被配置关闭时，MCP仅提示参数无效。 | 保持现有错误码，补充可识别的具体原因及恢复建议；关闭工具时提示配置启用和重启连接。未知保存原因继续使用通用提示。 |
| 3. 专用游戏验证脚本过时 | 中，影响验收：脚本仍断言启用后只有43个工具，实际为44；还固定连接旧共享IPC目录，不能直接用于当前独立工作目录。 | 迁移到当前隔离测试接口及工具目录发现，覆盖图形、无窗口和错误恢复，避免继续手工维护工具数量。 |

前两项属于[已有TODO](../development/TODO.md)中的错误恢复和原因准确性范围，此次没有新增TODO。普通截图、独占保存及已有文件／符号链接保护未发现需要改变的行为。

## 当前参数和返回

工具按配置启用，不接受preset。操作参数只有可选filename：

```json
{"filename":"combat.png"}
```

也可以传空对象，生成UTC时间加随机后缀的文件名。显式filename必须是5至128字符、以小写`.png`结尾的文件名，不含目录分隔符或ASCII控制字符；null不接受。目标目录由MCP启动配置指定。

本次实际战斗截图返回：

```json
{
  "path": "/home/c163q/Program/workspace/project/sts2_agent/.tmp/2026-11-08-screenshot-tool-review/gui/captures/combat.png",
  "width": 1760,
  "height": 990
}
```

路径和尺寸随环境变化。返回没有scene、screen、available_actions、transition或图片内容；这是文件工具的现有格式。工具通过MCP目录发现，get_observation.available_actions不列出截图。

| 场景 | 当前行为及典型返回 |
| --- | --- |
| 主菜单、战斗、选牌、查看战场、地图、牌组 | 同一三字段结构，实际取得8张PNG；[指定文件名](2026-11-08-capture-screenshot-examples/named.json)和[自动命名](2026-11-08-capture-screenshot-examples/automatic.json)各给一例 |
| 同名文件 | [file_exists](2026-11-08-capture-screenshot-examples/duplicate.json)，原文件不变，但随后动作被[要求观察](2026-11-08-capture-screenshot-examples/duplicate-next-action.json) |
| 目录是文件 | [screenshot_save_failed](2026-11-08-capture-screenshot-examples/save-failed.json)，游戏状态不变，已有许可丢失 |
| 文件名／额外参数错误 | [非法路径](2026-11-08-capture-screenshot-examples/invalid-filename.json)、[传preset](2026-11-08-capture-screenshot-examples/invalid-preset.json)本地拒绝，保留旧许可 |
| 配置关闭 | 工具不在目录，[调用返回invalid_request](2026-11-08-capture-screenshot-examples/disabled.json) |
| 无窗口模式 | [screenshot_unavailable](2026-11-08-capture-screenshot-examples/headless.json)，不创建文件或许可 |

## 参数及提示词建议

建议保持filename及三字段结果，无须增加summary、筛选或其他预设。现有结构已经足够精简。截图保留实际画面语言和视口分辨率，保存由游戏外进程完成；截图不切换页面，也不授予新的玩法许可。

提示词可简化为：

> Save the current game viewport as a PNG in the configured directory; return its local file path and pixel dimensions.

小范围重构集中于Python侧：保存错误携带可识别原因，保留已验证的采样信息，供会话判断能否沿用旧许可。Godot取图、PNG边界校验、文件保存与MCP输出继续保持现有职责分离。

保存目录实际为文件和中文长文件名已在本地复现；不建议把所有OSError都解释为权限／空间问题。具体文件系统限制应据实际错误说明，当前文件名字符上限保持即可。

## 输出定稿

filename、三字段成功结果、PNG格式及尺寸边界保持，无preset或内联图片。仅在有效原生取图成功、原生执行证据明确未交互且已采样、采样令牌等于已有许可时，已识别的本地保存拒绝保留旧许可；不生成新许可。保存错误的执行证据缺失／矛盾、不同令牌、坏PNG／响应、原生失败、取消及未知文件结果仍清除许可。成功截图保持现有同令牌规则；矛盾的原生成功证据仍视为坏响应。

错误码保持，目录是文件、文件名／路径过长、权限不足、只读目录和空间不足给出稳定具体原因及恢复建议，未知原因仍用通用提示，并标记outcome:unknown。临时文件清理失败可能已发布目标，明确提示检查目录并标记未知结果，不作为可恢复的未保存拒绝。截图配置关闭时提示启用配置及重启连接；其他未知工具仍按原规则拒绝。

截图验证迁入现有隔离IPC／对局约定和GUI套件，保留独立主菜单及headless检查；工具目录按注册表比较，目录／文件名错误后直接游戏动作、未观察首调用、状态改变及取消的负例均覆盖。仅更新MCP版本，Godot取图、Mod版本和schema不变；不更新正式安装、不增加用户TODO。执行见[计划](../superpowers/plans/2026-11-08-screenshot-recovery.md)。
