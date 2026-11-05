# 地图关闭结果与拒绝恢复实施记录

> 当前状态：实现、约定验证和一次独立审查完成，已合入 main，临时分支已删除。703 项 Python、124 项 C#、编译和六类 GUI／七步骤已通过；保留旧验证器迁移失败记录，不声称首批套件整体通过。暂无阻塞。

依据[审阅定稿](2026-11-05-close-map-review.md)与[实施计划](../superpowers/plans/2026-11-05-close-map-results.md)。基线 5474951，目标 Mod0.69.0、MCP0.71.0、schema41；目标游戏与上游证据沿用[开发核验](2026-11-05-close-map-development-notes.md)。不安装正式 Mod，不推送。

## 最终实现

- MapView.CloseUnavailableReason 统一当前原生可关闭条件与具体原因，CanClose 为其布尔投影；工具列表和执行前均使用该入口。
- 原生关闭流程迁入 GameAdapter.Map.CloseMap；保留按钮点击、动画、同一 run/map/act/overlay 检查、重开监听和 finally 解绑。只有前置拒绝带 ui_unchanged:true；点击后任何失败不恢复已有许可。
- closed_map 先 observation_details 完整校验，仍拒绝返回未关闭浏览页。公开成功共用 actions_only_result，保留适用 selection.type/status；默认和 full 内容一致，无 transition、主体、note 或图像。底层文件响应仍完整。
- MCP media=false，关闭后回到占卜不再依赖 PNG 捕获。需要棋盘内容和图像时显式观察；旧文件接口的默认媒体选项保持。
- 旧 verify_mcp_map 使用当前目录核对发现的工具，关闭只比较 actions_only，其余完整观察与原生图一致性目标不变；与新测试在同一战斗中串行运行，避免两个 MCP 控制连接重叠。

## 验证记录

证据目录 `.tmp/2026-11-05-close-map-results/`；原审阅 `.tmp/2026-11-05-close-map-review/` 与六份旧样本保持原样。

- `python-red.log`：新增 5 项回归先运行，3 项预期失败（旧成功主体、选择／房间校验缺口、拒绝许可）；2 项既有安全规则已通过。
- `python-focused.log`：38 项中 10 个旧契约断言失败，均为媒体需求、冻结关闭主体或通用预设返回。按定稿更新测试期望，冻结 JSON 保持原样；未退回产品行为迎合测试。
- `python-focused-corrected.log`：62 项通过，5.379 秒。旧“未注册工具不保留许可”的样本由已接入的 close_map 换为未审阅 open_shop，保留其原验证目的。
- `build.log`：0 警告／0 错误，6.26 秒。

- `python-full.log`：703 项通过，44.173 秒；`csharp.log`：124 项通过。
- `gui`：no_map 完整通过，combat 的新关闭步骤通过；旧独立检查在工具目录处失败，实际还启用了可选 capture_screenshot。改为按发现的可选开关生成当前目录。
- `gui-remaining`：旧脚本到地图比较处失败，兼容 player_result 比生产地图投影多保留 status。`gui-current-decoder` 保留了仅补 operation 名仍不足的失败尝试；源码确认 player_result 始终是兼容片段投影。保存响应与生产 decode_success 的独立比较为完全相同，随后旧脚本统一改用生产解码入口。一次检查失败后误在同一 shell 继续推进的记录已纠正，后续依赖检查分开执行；没有改产品迎合旧脚本。
- `gui-production-decoder`：五类剩余场景完整通过，141.537 秒。与首批 no_map 合计六类、七个不同步骤；旧独立脚本 completed:true、10 次 MCP 调用通过。同一战斗先后运行两个独立 MCP 连接，没有重叠控制连接。
- 全部尝试合计 97 次 MCP 调用，包含预期业务拒绝和保留的失败脚本步骤。不是一次无失败套件通过；没有无故重复已完整通过的 no_map。
- [9 份真实完整 JSON](2026-11-05-close-map-fixed-examples/README.md)逐对象匹配原始 structuredContent，manifest 保存参数、来源下标、图像计数和 SHA-256。占卜关闭的 image_count 为 0，原生状态也未附 divination_image；其后的显式观察仍正常提供棋盘。原[6 份审阅样本](2026-11-05-close-map-examples/README.md)按原哈希保持。
- 构建与隔离运行时 DLL 均为 `d188e26338c54fa7687bbf02ed43fd96d037b72027410a43f7b007a5ea6bcb4f`。四个自有游戏进程（101276、102554、104155、104557）均退出，正式安装未改。

## 未验证范围

无对局、多人、任意模态覆盖／入口隐藏、过渡中的关闭，以及人工并发重开／切幕未逐一新增 GUI 复现；这些分支核对目标版本源码，关闭后的身份和重开检查保持原流程。Python 回归覆盖缺失／损坏房间、损坏选择、无初始许可、缺少未交互保证和矛盾执行事实；合成坏数据不冒充游戏自然产生的响应。

建筑师关闭地图的页面分支没有单独新增 GUI，沿用已校验基础观察和明确允许的 epilogue view；普通事件和占卜已实际验证。未安装正式 Mod、未全流程通关，未重跑与本次行为无关的其他工具 GUI。

## 独立审查与合入

实现提交 1972e43 已快进合入 main，fix/map-close-results 已删除；未推送或安装正式 Mod。

独立审查代理 /root/review_close_map_results（gpt-6.1-sol/high）只读核对 5474951..1972e43，结论可合入，Critical0、Important0、Minor0，无修复或复审。建筑师、人工并发重开／切幕及多人仍按已披露边界处理；主代理判定保持原生防护和单人限制，不据源码核对声称新 GUI 覆盖，不扩大本次任务。

本任务沿用清洁 checkout 的临时分支、已有依赖与隔离运行时，只有主代理写代码；按用户既有授权直接执行和自行本地合入。相同代码快进后只做交付校验，不重建 DLL 或重复整套测试。验证器失误及纠正、审批命令和全部判定保留在任务证据目录；工作区归档后仅删除本计划临时记录，不触及其他任务。
