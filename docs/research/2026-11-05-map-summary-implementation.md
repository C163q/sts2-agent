# 地图分类与查看拒绝修复实施记录

> 当前状态：实现、验证与一次独立审查完成，已合入 main，临时分支已删除。698 项 Python、124 项 C#、编译及 9 种 GUI 组合的约定范围通过；保留两次清理失败记录，不声称首批套件整体通过。暂无阻塞。

实施依据为[地图定稿](2026-11-05-inspect-map-review.md)及[计划](../superpowers/plans/2026-11-05-map-summary.md)。基线 `bac16a6`，目标 Mod 0.68.0、MCP 0.70.0、原生 schema 41；游戏与上游证据见[源码核验](2026-11-05-inspect-map-development-notes.md)。未安装正式 Mod，未推送。

## 实现范围

- MAP-01、MAP-02：共用 MapUnavailableReason 服务工具列表与执行拒绝，固定公开原因；只对明确点击前拒绝声明 ui_unchanged，复用已有许可恢复策略。
- inspect_map 新增 summary；先复用有向连线子图裁剪，再 grouped_map；节点只按 type 分组为 ID，不附连接或详情。原生候选保持完整，full/default/selectable 保持原行为。
- MapInspection.Read 去除响应令牌依赖，由基础观察只读取得完整可见图；详情复用同次快照中的图。MapInspection.Summary 等待地图 Ready 才返回图，准备动画期间沿用不可读 map:null。
- schema 41 的地图必须通过完整 map_details 校验再生成分类。旧 schema 五字段地图继续兼容，不虚构类型。Python 的同一 grouped_map 服务基础观察与详情；基础观察固定整幕范围。
- notes.map 仅随已返回的分类地图加入；actions_only/top_bar 维持最小输出，覆盖／关闭时不附说明。full 的普通 null 与 default/summary 过滤规则保持。

## 验证与失败记录

证据根目录 `.tmp/2026-11-05-map-summary/`，原始失败保留：

- `python-red.log`：新回归先运行 7 项，5 个预期失败和 1 个错误（旧实现缺少新分组）；1 项无地图 note 的基线检查已通过。
- `python-focused.log`：地图、会话与新回归 56 项通过。
- `build-final.log`：0 警告／0 错误；`csharp.log`：124 项通过。
- `python-full.log`：697 项，2 个旧契约断言失败。将“其他不恢复的视图”样本从已经批准恢复的 inspect_map 换为 close_map；冻结预设基线另注明新增 summary 的专用回归覆盖。没有修改冻结 JSON 或退回产品行为。
- `gui.log`：新验证器未注册白名单，加载套件失败，尚未启动游戏；补白名单与参数后使用新的 `gui-registered` 目录。

- `python-full-corrected.log`：697 项通过，42.700 秒。C# 124 项通过；编译 0 警告／0 错误。
- `gui-registered`：飞鞋、战斗禁行、第二幕起点、双 Boss 四组完整通过；grouped_map 的调用断言通过，但清理奖励夹具超时，套件因此失败，未执行最后一组。
- `gui-remaining`：分类全部调用及 proceed 通过，清理仍超时。依据 TestRunRequest 等待 RewardFixture.Pending，以及已有旅行场景的完整收尾，定位到 proceed 只打开地图，Offer 仍等待离开奖励房间。仅在验证器末尾补原生 travel，未改生产代码、超时或清理逻辑。
- `gui-completed-flow`：分类、拒绝后直接选牌、选择战场地图覆盖、原生战斗上下文四组完整通过并清理。因此有 8 组不同组合完整通过，另保留 2 次分类局清理失败。不是一次套件无失败通过。
- [13 份真实完整返回](2026-11-05-map-summary-examples/README.md)保存三种基础观察、地图 full/summary/深度、幕起点及已有／无初始许可拒绝。每个文件记录原调用参数、证据下标和 SHA-256，逐对象核对原 structuredContent；原有手写结构示例不冒充实测。
- 上述八组地图组合使用 DLL `9e888a603c0a3d78ecdb6e8f38858b0641e7ba9535fcac77c9aa4feccbdc9844`；随后用户追加跨幕场景问题，复现并确认识别缺口，见[MapRoom 诊断与修复](2026-11-05-act-entry-scene.md)。
- `python-map-room-final.log`：最终 698 项通过，42.326 秒；`build-map-room.log`：0 警告／0 错误；`csharp-map-room.log`：124 项通过。
- `gui-act-entry-fixed`：在最终 DLL 上验证跨幕即时／延时观察、多个详情工具、牌组上下文及进入先古之民，再回归普通战斗上下文，两组通过并清理。与先前八组有一组重复，合计九种不同组合完整通过；先前八组未在最终 DLL 全部重跑，最终 C# 改动仅为共用场景入口增加 MapRoom 分支。
- 最终 DLL 与隔离运行时 SHA-256 相同：`1ffb82d5790e9bc51729c44e092223ce0faa511cb302f08627bbc8820fd8d774`。正式安装未替换。飞鞋截图已目视检查，未对整图所有节点逐个人工校核。
- 地图样本包含修复前 unrecognized 的明确对照，不把它当作当前返回；每份 manifest 单独记录其实际 DLL 哈希。私有交付校验核对原样本、文档链接、测试日志和构建产物一致性。

- `map-room-red.log`：10 项中仅新增的 MapRoom 场景失败；`python-map-room-full.log`：698 项中两项旧断言仍将 map 当非法场景。修正非法值样本后完整通过，以上失败均保留。

## 独立审查与交付

实现提交 `0430d27` 已快进合入 main，feat/map-summary 已删除。未推送或安装正式 Mod。

独立代理 /root/review_map_summary（gpt-6.1-sol/high）只读审查 bac16a6..0430d27，Critical 0、Important 0；Minor 1 是私有进度开头残留旧计数，已更新，无产品代码改动或复审。五项重点均通过核对，无其他需要根代理裁决的未决事项。

完整验证与 private review-result.md 位于任务证据目录；五个自有 GUI 进程均已退出。相同代码快进后仅重新运行交付校验，不重建 DLL 或重复整套测试。

## 未验证范围

- 没有穷举所有弹窗、多人、第三方地图和并发人工切页。无对局、禁用／隐藏地图入口、过渡中的具体拒绝按源码核对，未逐一制造 GUI 样本；中途变化不声明未交互，异常／矛盾证据在 Python 回归中验证。
- 地图的完整分类读取覆盖原生可滚动内容；沿用真正隐藏与透明内容的排除。问号揭晓及任务标记详情沿用既有读取，此次只验证它们在摘要省略，不新增自然任务事件复现。
- 未执行原有 verify_map.py 的全部独立破坏性探针、全流程通关或正式安装。close_map/travel_to_node 在所需真实流程中回归，不核销它们各自的完整内容审阅。

