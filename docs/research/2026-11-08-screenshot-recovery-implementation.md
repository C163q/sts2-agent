# 截图保存恢复实施与验证

> 当前状态：实现、验收和一次独立审阅的单轮修复完成。共2项，已完成1项；剩余归档、核销与合入。保留1项非阻断文档建议，无产品阻塞。

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

最小化／后台节流、暂停渲染、实际超过像素上限、真实磁盘耗尽、发布恰逢操作系统取消、非Linux文件系统未新增实测；维持既有边界，不扩大兼容保证。

## 独立审阅与单轮修复

review_screenshot_recovery使用gpt-6.1-sol/high、新上下文只读审阅3620942..af5b1d5；Critical无，Important1项、Minor1项，结论修复后可合入。没有第二次派审。

I1：共享ipc_directory在环境变量缺失时回退旧目录，验证器此前没有强制显式变量。修复局限于截图入口，在创建客户端、报告或配置前拒绝缺失／空串／空白的STS2_AGENT_VERIFY_IPC_DIR，其他验证器默认行为不改。新增[test_screenshot_verifier.py](../../tests/python/test_screenshot_verifier.py)先RED三处构造客户端违规，GREEN后21项相关检查2.352秒通过、全量844项39.301秒通过。

首个I1探针的Mock返回对象导致序列化错误，记录在review-i1-red.log；随后改为客户端构造即明确失败，review-i1-explicit-red.log证明三处隔离违规，原始失败日志保留。严格检查只增加缺失变量的早期拒绝，不改变已通过的显式IPC流程，因此没有重启这三类通过的游戏或重建DLL。

M1保持为非阻断文档改进：截图指南的单测示例命令仍只跑旧test_screenshots模块，未列出新增恢复及入口隔离模块。本轮实际执行了21项相关和844项全量检查，验收不受影响；后续可补齐示例命令，不增加用户TODO。

审阅搁置范围及裁定：

| 范围 | 裁定和依据 | 剩余影响 |
| --- | --- | --- |
| PNG完整解压／格式语义 | 按定稿保持PNG信封校验及原生取图机制 | 不声称已完整解码验证任意PNG生产者 |
| 真实I/O、系统取消瞬间、后台、非Linux | 保留明确未实测范围，注入只证明代码路径 | 这些环境仍需实际验证／适配 |
| 无execution facts的旧成功响应 | 按要求保留成功同token兼容，错误恢复不借缺失证据 | 旧成功路径沿用原证据强度，错误可能需重新观察 |
| 固定夹具所有动作的通用可用性预检 | 已知确定流程直接断言成功，只有可选close_map动态判断 | 原生或夹具变化时测试会失败，需同步调整步骤 |
| 旧stdio单测中的固定数量 | 只迁移专用游戏验证器，不全局整理既有目录回归断言 | 新增工具时仍需同步维护相关旧单测 |

## 文档一致性

截图指南旧规则将所有保存失败都视为需重新观察，已改为与代码一致的有限条件恢复。架构说明原先只列五种动作并称仅这些支持未提交恢复，与登记表已扩展的现状不符；改为引用登记表和统一错误文档，避免继续手工维护重复名单。原失效的固定IPC／数量验收说明将在新入口验收后替换。
