# 截图保存恢复实施与验证

> 当前状态：实施中，共2项，已完成1项；代码和三类隔离验收完成，正在完成文档及一次独立审阅。暂无阻塞。

基线3620942，要求见[输出定稿](2026-11-08-capture-screenshot-review.md#输出定稿)，步骤见[计划](../superpowers/plans/2026-11-08-screenshot-recovery.md)。证据根目录`.tmp/2026-11-08-screenshot-recovery/`。

## 实现

ScreenshotError通过受控原因提供目录非目录、文件名／目录路径过长、权限、只读文件系统和空间／配额不足提示，原始OS异常不公开。未知I/O及清理失败标记outcome:unknown；目标可能已发布，不恢复许可。原有独占发布、已有文件／符号链接保护和finally清理保留。

GameSession仅在原生图像有效、执行证据完整且明确已采样／未交互、错误为已识别的本地保存拒绝、采样token等于已有token时恢复旧许可。CAPTURED_READ_ONLY为独立内部证据，不复用动作未提交保证。不同令牌、冷调用、缺失／矛盾证据、坏PNG、原生失败、未知结果和取消均有负例。成功截图保持原来的同令牌规则；兼容旧成功响应不等于允许缺少证据的保存错误恢复。

GameTools和MCP目录层共用关闭配置提示，返回invalid_request／check_configuration，说明启用screenshots.enabled及重启连接；任意未知工具仍按原规则拒绝。成功结果仍只有path/width/height，filename及无preset保持。提示词改为描述本地PNG及像素尺寸。

只修改Python，MCP0.83.0；Mod0.80.0、schema47不变，没有重建C#。运行与构建DLL均保持`2a87d3a18c4c34dca800132ed4cdb489f4ac8e20dc1e9ec3bfb6be84cfb4a1b5`，游戏仍为目标v0.107.1／59260271、RitsuLib0.6.10。原生API核对沿用[开发核验](2026-11-08-capture-screenshot-development-notes.md)。

## 测试

- red.log：19项相关检查先失败，11处失败、1处错误，证明旧许可和提示缺口。
- directory-length-red.log：配置目录过长不能误指修改filename，单项先失败后修正。
- unknown-outcome-red.log：未知I/O和清理失败须公开未知结果，单项先失败后修正。
- task1-final-green.log：20项截图相关检查通过，2.310秒；task1-final-full.log：全量843项通过，39.352秒。Task1提交ec0540d。

已覆盖未知I/O、临时文件清理失败后的已发布目标、完整／缺失／矛盾执行证据、不同token、坏PNG、原生失败、冷调用及本地保存期间取消。OS原因和清理故障采用受控文件系统注入；正常目录错误和UTF-8长文件名使用实际文件系统。

## 隔离验证入口

verify_screenshots.py使用verification_runtime的传入IPC与ensure_run；gui通过GameSession复用已配置的技能药水测试局，menu／headless在独立主菜单执行。目录按tool_definitions比较，不再固定工具数量；支持工作区外报告／IPC的绝对证据路径。

GUI套件验证同名、目录是文件及长名字后直接end_turn，以及选牌同名后直接skip。恢复文件目录的故障准备使用finally，图片与原生PNG字节逐张比较。地图返回是否可用依据available_actions，不再强制点击禁用按钮。主菜单冷截图不建立许可，关闭配置和任意未知工具分别保持正确提示。

三类隔离验收均通过：gui套件检查六种画面中的战斗、选牌、战场、地图、牌组，独立menu补主菜单；headless分别检查冷调用及有旧许可后的原生拒绝。共取得8张PNG，逐张与原生载荷字节相等，保持原视口尺寸和语言。启用／关闭工具集合从登记表比较，截图关闭提示配置，任意未知工具没有被误当作截图开关错误。

final-python-full.log全量843项通过，39.410秒；没有重建或重复C#检查，因为Native接口和DLL均未更改。GUI／menu／headless的具体耗时、进程身份及最终文件重放见verification.json；全部自有进程退出。

gui73.091秒、menu20.321秒、headless16.048秒，游戏进程132012、132379、132540及独立验证子进程均退出。verification.json复核41次实际MCP调用、17份非图像成功原生重放、8张PNG字节、12份JSON及376个相对文件链接，构建／运行DLL保持2a87身份。

[12份实际JSON](2026-11-08-screenshot-recovery-examples/README.md)来自通过的原生MCP调用，不生成或裁剪；参数、来源行号、原生文件及SHA在manifest中。未知I/O／清理失败、权限／只读／空间不足及保存期间取消采用Python受控注入，不冒充新增GUI故障。旧审阅失败报告和9份JSON保留原基线，没有新增用户TODO、更新正式安装或修改个人存档。

最小化／后台节流、暂停渲染、实际超过像素上限、真实磁盘耗尽、发布恰逢操作系统取消、非Linux文件系统未新增实测；维持既有边界，不扩大兼容保证。最终独立审阅结果完成后补齐。

## 文档一致性

截图指南旧规则将所有保存失败都视为需重新观察，已改为与代码一致的有限条件恢复。架构说明原先只列五种动作并称仅这些支持未提交恢复，与登记表已扩展的现状不符；改为引用登记表和统一错误文档，避免继续手工维护重复名单。原失效的固定IPC／数量验收说明将在新入口验收后替换。
