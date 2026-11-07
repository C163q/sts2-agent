# capture_screenshot 典型实际返回

对应b104d84基线，[审阅建议](../2026-11-08-capture-screenshot-review.md)和[开发核验](../2026-11-08-capture-screenshot-development-notes.md)给出问题与限制。本工具没有preset，文件名不使用full/default后缀。

| 场景 | 实际返回 |
| --- | --- |
| 指定名称保存战斗截图 | [named](named.json) |
| 省略名称，自动命名 | [automatic](automatic.json) |
| 同名文件拒绝及随后动作要求观察 | [截图错误](duplicate.json)、[后续动作](duplicate-next-action.json) |
| 非法文件名 | [invalid-filename](invalid-filename.json) |
| 不支持preset参数 | [invalid-preset](invalid-preset.json) |
| 保存目录实际为文件 | [save-failed](save-failed.json) |
| 工具配置关闭 | [disabled](disabled.json) |
| headless不支持取图 | [headless](headless.json) |

9份均为实际MCP返回，未裁剪或生成内容；[manifest](manifest.json)记录参数和证据位置。首个图形脚本在各截图完成后误尝试关闭禁用的地图返回按钮，整体报告失败；这里仅使用其中已经完成的截图和错误核验，不将整体计为通过。剩余保存错误、配置关闭和headless另行验证通过。

实际PNG保留在`.tmp/2026-11-08-screenshot-tool-review/gui/captures/`，不随文档提交。MCP返回本地路径与尺寸，原生像素内容没有进入公开JSON。
