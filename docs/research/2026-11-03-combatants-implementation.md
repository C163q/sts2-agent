# 战斗对象读取、错误恢复与预设实施

> 当前状态：已完成，共 3 阶段，已完成 3 阶段。541 项 Python 回归、40 项原生检查、60 项纯 C# 检查及最终六局隔离 GUI 全部通过；独立复审的两项问题已修复。文档及公开样本已同步，尚未安装正式 Mod。暂无阻塞。依据为[工具核验与已确认设计](2026-11-03-inspect-combatants-review.md)。

## 最终实施约束

- get_observation 的公开 full/summary 格式保持，各自从公共战斗对象读取的 Summary 级取得原始静态字段，再组合生命、资源、手牌等数据。内部静态数据不提前删 null 或压缩数字。
- 公共函数使用具名 level 参数 Summary/Full；Full 在同一静态对象及顺序上追加悬停解释。静态列表不因不可悬停而删除条目。
- 状态、意图、球槽与悬浮剑等图标取消屏幕坐标截断及对应数值的视口限制；保留显隐、透明、纹理、缩放和实际裁剪边界，不全局改写 VisibleUi.OnScreen。
- inspect_combatants 默认 default，支持 full/summary；summary 完全省略 hover_tips，default 经统一空值过滤。
- sources 支持分组与具体条目路径，筛选对象和关联说明；省略或 null 表示全部，[] 仅保留 scene/screen 和必要 notes。仅本工具接受显式 null，不扩大其他工具参数。
- 筛选用未筛选本次列表的规范路径；结果列表紧凑排列，必要时 source_indices 按原始数组路径给出原下标映射。hover_tips.sources 与 notes 中的路径保持规范地址，便于直接再用作筛选参数。映射也支持真正的空球槽，不用 null 伪造未选中项。
- 无效路径合并 errors，有效数据继续返回；共享解释仅保留匹配来源；未选中对象的解释及 note 不泄露。静态摘要不生成不可悬停 note；Full 仅对交互禁用的已展示条目给 notes.hover_tips_unavailable，不猜原因。
- 明确读取拒绝保留已有许可；未观察、未知结果、过期状态、取消、连接或控制器问题不生成／恢复许可。只公开适配器显式许可的说明。
- 不安装正式 Mod；版本与最终验证同步至 README。证据放在 .tmp/2026-11-03-combatants-implementation/，失败现场保留。

## 阶段与验证

### 1. 错误与过时验证入口

- [x] 扩展 tests/python/test_inspection_errors.py 与现有 MCP 断言，观察明确拒绝／未知字段的旧失败。
- [x] 将 inspect_combatants 接入 PURE_READS 和明确本地诊断；原生拒绝使用 public_message。取消、坏响应、无初始许可及 stale_state 保持保守。
- [x] 更新 verify_combatants.py / verify_mcp_combatants.py，通过共用断言核对当前结构、来源及完整工具发现，不删只读一致性检查。
- [x] 运行对应 Python 回归，记录并提交独立变更。

### 2. 公共两级读取与图标边界

- [x] 原生检查先覆盖不可悬停静态保留、隐藏图标排除、离屏图标及计数保留；原有断言调整为新契约。
- [x] CombatantInspection.Read 增加 Summary/Full，拆分静态值与悬停生成；CombatObservation 组装共用静态对象，原有专属字段独立保留。
- [x] 图标专用显示读取复用显隐／裁剪，独立于视口；同步 OrbInspection、SovereignBladeInspection 和相关检查。不改无关工具。
- [x] 构建、纯 C# 检查与隔离游戏检查，核对静态／基础观察一致和真实悬停边界，记录后提交。

### 3. 工具参数、筛选与交付

- [x] 新增 tests/python/test_combatant_presets.py：嵌套并集、位置映射、空球槽、共享提示裁剪、[]/null、无效路径、未知字段、静态／完整边界、坏数据不可由筛选绕过；先观察失败。
- [x] 新增 combatant_presets.py 负责参数、树投影及来源映射；combatant_details.py 保持原生校验；game_tools.py 映射内部 level，预设统一出口。
- [x] 原生分派独立到 GameAdapter.Combatants.cs，支持内部 level，统一门控原因；不可悬停路径经明确校验后生成公开 note。
- [x] 更新 schema、提示词、文件客户端、版本、接口文档及用户 TODO 的部分覆盖范围。
- [x] 运行完整 Python、构建、纯 C#、真实 stdio 与 GUI 场景验证，检查普通观察预设、球／剑／同伴、精确过滤和错误后续接。
- [x] 独立复审、修复实际发现，更新进度、提交、确认工作区与自有进程清理。

## 风险与审查重点

- 视口过滤取消不能变成读取隐藏模型字段；图标与计数规则必须一致。
- source_indices 的路径是原始地址，不能混用压缩后的返回下标；嵌套路径和空球槽均需测试。
- Full 的模型说明异常不能被 summary 或 sources:[] 静默吞掉；但 Summary 请求不生成悬停正文。
- get_observation 的采样令牌与对象应来自同次读取；悬停说明不得修改静态字段、缓存、语言或游戏流程。
- 不以测试通过替代实际游戏验证；原生测试扰动须 finally 恢复。

## 执行记录

- 基线：3475d4d，Mod 0.52.0、MCP 0.53.0、schema 34；游戏及依赖证据沿用核验记录中相同程序集。本次按用户授权在现有工作区连续实施，不创建其他实施代理。
- 技术定案：显式 null 仅对新 sources 表示未筛选；细粒度数组使用 source_indices 映射，规范来源可跨 preset 直接复用。该映射是控制定位信息，不携带游戏隐藏机制。

- 阶段 1：stage1-red.log 为 67 项中 5 个失败，复现许可与未知字段问题；stage1-green.log 为 67 项通过。未将此结果冒充 GUI 验证；两个专项验证入口已改为共用当前契约断言，实机仍随后验证。

- 阶段 2：native-red-2.log 记录旧运行时的三项预期失败；新运行时 native-green.log 的 38 项原生检查全部通过，纯 C# 为 60 项通过。stage2-gui/report.json 为 passed，球可见性及剑的两局检查通过，同一自有进程 PID 33190 已关闭。首轮 native-red 因脚本没有等待主菜单就绪而失败，修正等待后使用未覆盖的旧运行时重现；失败现场保留。

- 阶段 3 回归：新对象投影先观察模块缺失；工具集成随后观察 native level、未知参数与坏元数据的预期失败，接入后 16 项通过。完整首轮为 537 项、6 个子项失败，原因是未筛选 Full 被重新组装，破坏通用边界探针的原样返回；增加与既有预设一致的 Full 无筛选直通后 537 项通过，新增 CLI 与隔离元数据检查后 539 项通过。
- 独立复审：按模型选择约定由 gpt-6.1-sol/high 只读审阅；发现 CLI default 未映射内部 Full、意图 Sprite2D 缺少零缩放排除两项 P2。CLI 增加失败回归后修正；原生增加两项断言在旧代码上实测失败（review-zero-red），再修正。另补 CLI 多余参数不得静默丢弃的回归，修正为 IPC 前明确 invalid_request；不改变其他文件工具错误政策。复审未发现来源映射、真实空球槽、共享提示、许可、隐私或双门控测试入口的新问题；未让 reviewer 重复运行 GUI。
- GUI 首轮 gui-first 在旧文件验证脚本已通过结构检查后因收尾输出引用已删除的 tips 局部变量失败；两个专项脚本的打印均改为直接读取结果字段，保留失败目录。该批次不算游戏逻辑通过记录。
- 环境记录：一次未升级权限的异步集成检查触发已知 socket 限制并按45秒超时退出；相同检查沙箱外通过。没有把环境挂起当成产品回归。原生／GUI进程均使用独立IPC与存档，未安装正式Mod。
- 文档差异：MCP 错误速查表仍写所有 illegal_action/expired_request/invalid_request 后必须观察，与同页明确拒绝保留许可的正文不一致；已统一为遵循 recovery，未持有许可时仍先读取状态。

## 最终验证与交付

- 版本：Mod 0.53.0、MCP 0.54.0，观察 schema 仍为 34；内部 level 与可选悬停状态元数据不改变基础观察字段。正式游戏未安装本次版本。
- review-green-build.log：最终构建 0 warning / 0 error。csharp-final.log 为 60 项通过。review-native-green.log 使用最终候选 DLL，40 项原生检查通过，包括新加的两个零缩放回归；对应 review-zero-red 先在旧实现中复现两项失败。
- python-reviewed.log：541 项通过，37.941 秒。早期 537/539 项与已知沙箱挂起、旧全量探针失败均保留，不替代此最终记录。CLI default 与多余参数也分别有 red/green 日志。
- gui-reviewed/report.json：passed，六个独立测试局、一个自有进程 PID 38467；普通战斗、充能球、奥斯提、剑、选择战场、零能量均通过。主验证证据共 77 次 MCP 工具调用；另在普通战斗运行了两个已修复的旧验证入口，旧 stdio 验证器另有 3 次工具调用。没有测试入口加入公开 MCP 清单。
- 实际 note 由套件专用文件入口暂时禁用一条意图的鼠标事件后，通过正常 inspect_combatants 取得，再 finally 恢复；同时确认 summary 仍保留该静态意图、不附悬停元数据。不能将此夹具当作自然死亡帧的实测。
- 对象筛选验证了仅敌人、具体意图、规范来源及压缩映射、真实空球槽、无效路径合并、null 与 []；选择未完成时 [] 只保留上下文和导航 note。拒绝后直接到达原生动作检查，零能量出牌拒绝后直接结束回合。
- 相关原生读取前后观察与令牌一致；Full 与基础观察的公共字段相等，summary 与静态数据对应，default 使用现有统一空值规则。没有将文件客户端或测试配置的私有元数据带入公开样本。
- 最终构建、已准备运行时与 GUI 报告 DLL SHA-256 一致：3ae6924b77bb945968e288d3bb570753b0f0dab36d7b8e4a4175b3755773dfe9。自有测试进程均已关闭。
- 五份完整公开 JSON 原样保存于[交付样本清单](2026-11-03-combatants-implementation-examples/manifest.json)，没有用手工构造输出替代实测。

## 未验证范围

未新增自然死亡中每个 UI 帧的悬停演变、完整 LLM 通关、真正多人、第三方对象／提示类型、全部状态／意图／多剑组合或任意 Mod 图层像素遮挡的穷举验证。球与剑边界有本轮阶段 2 的独立 GUI 与原生检查；最终六局验证使用新的分派和输出，不把不同 DLL 的证据描述为同一批。其他工具完整错误审查仍按用户 TODO 留待后续。
