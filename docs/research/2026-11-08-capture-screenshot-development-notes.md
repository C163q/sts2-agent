# capture_screenshot 开发核验

## 基线与证据

核验日期2026-11-08，代码基线b104d84d754f67bb15aae1f444c0d1eaa97d613d；Mod0.80.0、MCP0.82.0、schema47；Linux游戏v0.107.1／59260271、RitsuLib0.6.10、Godot4.5.1。建议范围见[审阅报告](2026-11-08-capture-screenshot-review.md)。

证据根目录`.tmp/2026-11-08-screenshot-tool-review/`。运行DLL与构建产物一致，SHA-256为`2a87d3a18c4c34dca800132ed4cdb489f4ac8e20dc1e9ec3bfb6be84cfb4a1b5`。沿用已核对的游戏程序集`data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256为`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。未重新编译、安装或更改正式游戏／Mod配置。

## 实现职责

| 层次 | 入口与当前行为 |
| --- | --- |
| 配置和目录 | [mcp_config.py](../../src/sts2_mcp/mcp_config.py)严格解析开关与保存目录，启动时固定；[mcp_server.py](../../src/sts2_mcp/mcp_server.py)按开关列工具，默认43、启用后44。关闭或未列出的工具在目录分发层拒绝。 |
| 工具元数据 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)将截图列为file effect、不要求旧许可、不刷新许可；无preset。注解readOnly/destructive/idempotent均false，符合新增文件的实际副作用。 |
| 参数与保存 | [screenshot_tool.py](../../src/sts2_mcp/screenshot_tool.py)校验filename，先写同目录临时文件，再通过os.link独占发布，finally删除临时文件。filename不传入游戏。 |
| 原生取图 | [RequestDispatcher.cs](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)先Capture生成同次snapshot，再调用[ViewportCapture.Read](../../src/Sts2Agent/Observation/ViewportCapture.cs)。[BridgeMod](../../src/Sts2Agent/Infrastructure/BridgeMod.cs)在图形FramePostDraw处理；headless改用ProcessFrame但显式拒绝取图。 |
| 媒体校验 | [media.py](../../src/sts2_mcp/output/media.py)验证尺寸类型／范围、base64、PNG头、块边界、CRC、结束标记及声明尺寸；这是PNG信封校验，不引入额外解码库。原生与Python均限制16,777,216像素／32MiB PNG。 |
| 公开结果与许可 | [game_session.py](../../src/sts2_mcp/game_session.py)把图片交ScreenshotStore保存，返回path/width/height；成功只在旧token与采样token相等时保留旧许可，首次截图不生成许可。结构化内容与文本JSON相同。 |

图形结果为游戏视口实际像素，保留中文，不经过玩法JSON的英语转写。不读取桌面窗口、边框或系统光标；选牌、地图、牌组等覆盖页直接按当前渲染保存。此次实际分辨率1760×990，不能用启动参数的逻辑窗口尺寸代替返回尺寸。

原生截图仍依赖通用Capture生成采样令牌；因此没有单独绕过观察代码故障的取图通道。本轮未注入这类故障，未据此提出全局快照改造。

## 问题根因与建议边界

### 本地保存失败丢失许可

_send已验证原生响应及snapshot_id后才调用ScreenshotStore.save；但ScreenshotError出口只保留错误码，丢弃采样token。execute的错误恢复也不处理file effect，因而file_exists及保存失败都撤销旧许可。

gui中duplicate前后snapshot一致，原PNG字节不变，但下一次end_turn为observation_required。gui-remaining中保存目录是普通文件，前后snapshot一致，同样阻挡后续end_turn。成功截图后直接end_turn和本地参数错误后直接end_turn均通过。

整改应只在有效原生取图成功、确认未交互且采样token与已有ticket一致时，允许已识别的本地保存失败保留旧许可。不能借截图建立新许可，也不能把状态变化、坏响应、取消、取图失败或未知文件结果直接归为不变。游戏动作仍由原生状态令牌与合法性二次检查。

### 原因丢失

ScreenshotError仅有code；ScreenshotStore把mkdir、临时文件创建及发布中的多数OSError统一转成screenshot_save_failed。error_output只提供通用目录／权限／空间建议。storage-probes/report.json记录真实本地文件系统行为：

- 保存目录本身是文件：mkdir得到FileExistsError／errno17。
- 90个中文字符加.png：共94字符，符合参数上限，但UTF-8为274字节，发布得到errno36；当前提示没有让用户缩短文件名。

两项均用有效1×1原生载荷夹具执行真实文件保存；不是额外GUI样本，没有残留临时图片。关闭配置的实际MCP调用也在目录分发层被统一报成参数无效，而GameTools本地的Screenshots are disabled解释没有到达该路径。

建议沿用错误码，只对已识别的本地原因提供稳定提示和恢复建议，未知原因保留通用文本；不直接公开任意操作系统异常。配置关闭应提示开关及重启连接。一般异常、取消及状态改变的恢复规则不放宽。

### 专用验证脚本过时

[verify_screenshots.py](../../tests/game/verifiers/verify_screenshots.py)在初始化后断言工具数43，当前启用截图实际44；它还固定使用.tmp/roundtrip/ipc，忽略独立验证工作目录，且不在当前suite允许的验证器清单中。现行截图指南提供的直接运行命令因此不能作为有效验收入口。未为再次证明固定计数错误而重复启动旧脚本。

截图指南已改为明确记录该验证缺口，移除失效的可运行命令。候选整改是迁入现有GameSession和verification_runtime的目录／对局约定，按当前工具目录核对注册，并保留独立headless分支。产品代码和该脚本尚未修改。

## 验证结果与限制

11项截图Python检查通过，2.252秒，涵盖配置、注册、参数、PNG信封、独占写入／符号链接、状态变化、取消、许可与stdio；只运行相关检查，没有重复全量834项。

图形gui取得8张实际PNG：主菜单、战斗、选牌、战场查看、地图、牌组六种画面，加两个自动命名样本；逐张核对文件、PNG声明尺寸和哈希。选牌及地图图片经查看确认中文UI和当前覆盖页。duplicate的原图保持不变，首次截图不建立许可，成功与本地参数错误后可直接继续。

该整体报告在最后强制close_map时失败：close_card_view已返回covered/map，但available_actions不含close_map；实际返回按钮禁用，原生正确拒绝。最初测试说明误判为地图已关闭，读取实际返回后更正；属于脚本未按available_actions操作，不是截图故障。保留失败报告，不改为成功，未重复已完成的图像场景。

gui-remaining补测保存目录错误及关闭配置，通过，39.414秒；headless独立实例通过，13.577秒，不创建截图目录或许可。首个gui运行77.414秒；三自有游戏进程123784、124146、124334均已退出。最初本地存储探针误用缺少anyio的系统Python，在导入阶段停止；随后使用项目venv完成，没有修改依赖或产品。

[9份实际JSON](2026-11-08-capture-screenshot-examples/README.md)不使用full后缀，因为本工具没有preset。manifest提供参数、来源行号、原生文件及SHA；图片保留在本地证据目录，不提交PNG／base64。目录保存失败的辅助调用未逐次记录原生文件名，可从该独立IPC目录唯一的像素响应及前后同token复核。

verification.json核对9份JSON与原返回逐项相等、8张PNG与原生像素载荷字节相等、保存错误前后及取图采样token一致、199个相对文件链接存在，以及三个自有游戏进程退出。构建／运行DLL和游戏程序集SHA也已复核；这是已记录检查点的验收，不将首轮图形脚本的失败报告改为通过。

未新增实测：最小化／后台节流、窗口暂停、实际超过像素上限、磁盘耗尽、权限动态变化、取消恰逢文件发布、非Linux文件系统。取消和坏图像的边界已有Python夹具检查，不把它们描述为新增GUI结果。没有新增用户TODO，产品代码、版本、正式安装和个人存档不变。
