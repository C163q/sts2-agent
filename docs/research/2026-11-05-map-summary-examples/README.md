# 地图摘要真实返回样例

这些文件来自地图分类任务的真实 stdio MCP 结果，保留完整返回对象；不是根据字段手写。测试局使用固定夹具，数值和地图不代表正常开局。act-entry-before-fix.full.json 专门保留 MapRoom 识别修复前的 unrecognized，其他文件展示各自实测基线；逐文件 DLL 哈希见 manifest。代码、兼容基线、验证范围与失败记录见[实施记录](../2026-11-05-map-summary-implementation.md)。

- [inspect-map.full.json](inspect-map.full.json)：`inspect_map`，参数 `null`。
- [inspect-map.summary.json](inspect-map.summary.json)：`inspect_map`，参数 `{"preset": "summary", "max_steps": 0}`。
- [inspect-map-depth1.summary.json](inspect-map-depth1.summary.json)：`inspect_map`，参数 `{"preset": "summary", "max_steps": 1}`。
- [act-entry-depth1.summary.json](act-entry-depth1.summary.json)：`inspect_map`，参数 `{"preset": "summary", "max_steps": 1}`。
- [observation-map.full.json](observation-map.full.json)：`get_observation`，参数 `{"preset": "full"}`。
- [observation-map.default.json](observation-map.default.json)：`get_observation`，参数 `{"preset": "default"}`。
- [observation-map.summary.json](observation-map.summary.json)：`get_observation`，参数 `{"preset": "summary"}`。
- [observation-covered.full.json](observation-covered.full.json)：`get_observation`，参数 `{"preset": "full"}`。
- [map-rejected-no-permission.full.json](map-rejected-no-permission.full.json)：`inspect_map`，参数 `{"preset": "full"}`。
- [map-rejected-retained.full.json](map-rejected-retained.full.json)：`inspect_map`，参数 `{"preset": "full"}`。
- [act-entry-immediate.full.json](act-entry-immediate.full.json)：`get_observation`，参数 `{"preset": "full"}`。
- [act-entry-map.full.json](act-entry-map.full.json)：`inspect_map`，参数 `{"preset": "full"}`。
- [act-entry-before-fix.full.json](act-entry-before-fix.full.json)：`get_observation`，参数 `{"preset": "full"}`。

[manifest.json](manifest.json) 记录本地证据位置、从 0 开始的调用下标、参数和输出 SHA-256。截图位于原验证目录；代表性截图已目视检查，未对整图逐节点人工校核。
