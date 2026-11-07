# 截图恢复修复后的实际返回

共12份实际MCP JSON，对应MCP0.83.0及未改变的Mod0.80.0／schema47。没有preset，不使用full/default文件后缀。要求和验证范围见[实施记录](../2026-11-08-screenshot-recovery-implementation.md)。

| 场景 | 实际返回 |
| --- | --- |
| 指定名称保存及自动命名 | [named](named.json)、[automatic](automatic.json) |
| 同名拒绝及随后直接结束回合 | [duplicate](duplicate.json)、[direct-after-duplicate](direct-after-duplicate.json) |
| 目录实际为文件 | [directory-is-file](directory-is-file.json) |
| 中文文件名超过文件系统字节上限 | [long-filename](long-filename.json) |
| 选牌同名拒绝后直接跳过 | [direct-selection-skip](direct-selection-skip.json) |
| 非法文件名 | [bad-filename](bad-filename.json) |
| 配置关闭，提示启用和重启连接 | [disabled](disabled.json) |
| 独立主菜单截图 | [menu](menu.json) |
| headless原生拒绝及随后需观察 | [headless](headless.json)、[headless-next-action](headless-next-action.json) |

[manifest](manifest.json)记录工具、参数、报告行号、原生响应文件及样例SHA。全部来自三类通过的隔离验收；8张实际PNG保留在`.tmp/2026-11-08-screenshot-recovery/`各报告目录，不提交图片或base64。

目录和长名字拒绝后直接end_turn也已在GUI证据中验证，为避免重复只导出一份纠正动作回执。未知I/O、清理失败和取消采用Python故障注入，没有在这里生成对应的“实测GUI”样例。旧[9份审阅返回](../2026-11-08-capture-screenshot-examples/README.md)保留旧行为。
