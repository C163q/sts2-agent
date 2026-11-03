# 战斗对象读取、错误恢复与预设实施

> 当前状态：实施中，共 3 阶段，已完成 1 阶段；错误恢复与验证入口代码已完成，67 项 Python 回归通过，GUI 在后续统一验证；正在统一静态读取，最后实现预设和对象筛选。暂无阻塞。依据为[工具核验与已确认设计](2026-11-03-inspect-combatants-review.md)。

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

- [ ] 原生检查先覆盖不可悬停静态保留、隐藏图标排除、离屏图标及计数保留；原有断言调整为新契约。
- [ ] CombatantInspection.Read 增加 Summary/Full，拆分静态值与悬停生成；CombatObservation 组装共用静态对象，原有专属字段独立保留。
- [ ] 图标专用显示读取复用显隐／裁剪，独立于视口；同步 OrbInspection、SovereignBladeInspection 和相关检查。不改无关工具。
- [ ] 构建、纯 C# 检查与隔离游戏检查，核对静态／基础观察一致和真实悬停边界，记录后提交。

### 3. 工具参数、筛选与交付

- [ ] 新增 tests/python/test_combatant_presets.py：嵌套并集、位置映射、空球槽、共享提示裁剪、[]/null、无效路径、未知字段、静态／完整边界、坏数据不可由筛选绕过；先观察失败。
- [ ] 新增 combatant_presets.py 负责参数、树投影及来源映射；combatant_details.py 保持原生校验；game_tools.py 映射内部 level，预设统一出口。
- [ ] 原生分派独立到 GameAdapter.Combatants.cs，支持内部 level，统一门控原因；不可悬停路径经明确校验后生成公开 note。
- [ ] 更新 schema、提示词、文件客户端、版本、接口文档及用户 TODO 的部分覆盖范围。
- [ ] 运行完整 Python、构建、纯 C#、真实 stdio 与 GUI 场景验证，检查普通观察预设、球／剑／同伴、精确过滤和错误后续接。
- [ ] 独立复审、修复实际发现，更新进度、提交、确认工作区与自有进程清理。

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
