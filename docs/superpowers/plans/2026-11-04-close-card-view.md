# 卡牌浏览关闭错误恢复实施计划

> 当前状态：实施、验证及独立审查完成，共 3 项，已完成 3 项；批准范围无遗留，证据及未覆盖范围见[实施记录](../../research/2026-11-04-close-card-view-implementation.md)。暂无阻塞。

依据[关闭工具审阅](../../research/2026-11-04-close-card-view-review.md)，代码基线 `62d998a`。用户已确认修复 CLOSE-01–02，保持 default/full 和 actions_only，不新增参数或 summary。

## 约束与接口

- CardView 的关闭合法性与安全原因共用入口：`CloseUnavailableReason(Control? screen)` 返回 null 表示可关闭，CanClose 使用它；无浏览页、被覆盖／隐藏／未就绪、非浏览选择、返回按钮缺失／隐藏／禁用分别给适当原因。不公开内部异常或隐藏内容。
- close_card_view 在 UiChanged／ForceClick 前明确拒绝时声明 ui_unchanged:true；一旦点击即按原有未知结果与异常规则处理。MCP 仅登记该工具采用既有证据校验，不修改共用许可状态机，不凭错误码／false 执行事实恢复许可。
- 保留关闭首个 await 前完成、后续只采样、不重复关闭新页面的行为。保留完整观察先校验、成功刷新许可、地图／选择上下文与最小投影；文件与 MCP 路径同步。
- 目标程序集及证据沿用审阅；Godot 操作在游戏线程，不阻塞游戏线程。现有 feature 分支原地实施，相关协议统一验证后提交，不安装 Mod、不推送或合并。

## 1. 拒绝恢复回归与实现

- [x] 新建 test_close_card_view.py：显式未交互拒绝后可直接 end_turn；无保证／已交互／矛盾／无旧许可不恢复；安全原因不泄露私有消息。先观察失败，再登记 unchanged_view_rejections。
- [x] 统一 CardView.CloseUnavailableReason／CanClose，原生前置拒绝附安全原因及 ui_unchanged:true；不修改点击之后的成功／异常流程。更新 Mod／MCP 版本，schema 保持不变。
- [x] 验证本地坏参数不发 IPC、不清许可，最终省略字段仍先校验，成功无旧观察也可授权；专项和全 Python／C# 检查通过。

## 2. 游戏验证

- [x] 新增 verify_card_view_close.py 与专项 GUI 清单：无页面拒绝后直接结束回合；选牌拒绝后直接取消；正常关闭、地图保留、选择战场返回及直接下一步；公开具体原因并保持原生状态。
- [x] 先让 GUI 用例在旧构建出现预期失败，再构建／准备隔离运行时，复测通过；有限超时并等待自有进程完成，保留失败证据。

## 3. 文档、审查与交付

- [x] 同步牌组指南、MCP／文件错误语义、原有 TODO 的已覆盖范围、审阅及核销清单；旧示例保持基线，新导出实际拒绝与续接样例。
- [x] 独立只读最终审查，处理重要问题；检查来源、哈希、链接及 diff 后提交 Conventional Commit。记录未验证的返回按钮隐藏／禁用、额外覆盖和所有瞬态。

## 重点边界

显式未交互只能保留已有许可，不能创造许可；已点击或超时／取消不能恢复；坏原生字段不能被最小输出掩盖；关闭不穿透选择／详情／地图；所有原因与 available_actions 判定一致。

证据目录：`.tmp/2026-11-04-close-card-view-implementation/`。
