# 可选截图工具

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

`capture_screenshot` 用于记录 LLM 调用工具时实际显示的游戏画面，方便与 JSON 观察、出牌结果和选牌页面比对。截图保持当前游戏语言及视口原始分辨率，输出为 PNG。

## 启动配置

在仓库根目录执行：

```sh
cp mcp-config.json.example mcp-config.json
```

根据机器环境编辑 `mcp-config.json`：

```json
{
  "screenshots": {
    "enabled": true,
    "directory": ".tmp/screenshots"
  }
}
```

MCP 启动时默认读取仓库根目录的 `mcp-config.json`，与启动进程的工作目录无关。默认文件不存在、没有 `screenshots` 或 `enabled=false` 时，截图工具不进入目录，调用会被拒绝；`enabled=true` 时公开 capture_screenshot。完整数量与目录见[MCP 工具范围](mcp.md#工具范围)。运行中不重新读取配置，修改后须重启 MCP 连接。

`directory` 在启用时必填。绝对路径直接使用；相对路径以配置文件所在目录为基准，支持开头的 `~`，不展开 `$HOME` 等环境变量。首次保存时创建缺少的目录，PNG 使用当前 MCP 进程的文件权限保存。目录不可写或磁盘空间不足时返回保存错误。

也可在原有启动参数中增加 `--config /absolute/path/mcp-config.json`。显式指定的文件不存在、JSON 损坏、重复键、未知字段或类型错误都会使启动失败，原因写到标准错误。实际配置已被 Git 忽略；`.env` 仍只用于构建和安装环境，MCP 不读取它。

截图配置控制工具注册，客户端另外管理调用授权。安装与更新遵循[正常游戏指南](live-game.md#更新与排错)；[接入方式](mcp.md)的其余参数保持一致。

## 调用与结果

调用：

```json
{"filename":"01-before-play.png"}
```

结果示例，路径及尺寸取决于实际环境：

```json
{
  "path": "/absolute/path/sts2_agent/.tmp/screenshots/01-before-play.png",
  "width": 1280,
  "height": 720
}
```

`filename` 可省略，此时生成 UTC 时间加随机后缀的文件名；指定时仅接受5至128字符、以小写`.png`结尾的文件名，不能含目录分隔符或ASCII控制字符，另受目标文件系统的长度限制。目录由配置确定。已有同名文件或符号链接返回 `file_exists`，不会覆盖。完整文件通过独占方式发布，保存失败不留下半张目标图片。

成功结果仅有 `path`、`width`、`height`，`content` 为同一对象的紧凑 JSON。工具不向 LLM 返回图片或 base64；客户端需要自行读取文件才能将其作为视觉输入。该工具有本地写文件副作用，MCP 注解为非只读、非破坏、非幂等。

## 画面与动作边界

截取调用时最近完成渲染的游戏视口，包括战斗、选牌、查看战场、地图和牌组页。采样保留当前遮挡、滚动、悬停与语言，仅包含游戏视口。最小化、后台节流或渲染暂停时不保证产生新画面，可能超时；不自动激活窗口。

截图在帧后主线程读取像素，经内部 IPC 交给外部进程保存；用户文件路径不会传入游戏，游戏线程不等待文件保存。当前上限为 `16,777,216` 像素、PNG `32 MiB`。headless、空视口或超过上限返回 `screenshot_unavailable`，不以黑图冒充成功。

截图不生成新动作权限；成功且采样令牌与旧许可一致时保留旧许可。已识别的本地保存拒绝，如同名文件、目录是文件或文件名过长，在原生图像有效、执行证据明确未交互且已采样、令牌与旧许可一致时也保留。没有旧许可时不会借截图建立许可。

未发送的本地参数错误保留旧许可；原生请求失败、保存错误缺少上述证据、令牌变化、坏响应、取消或未知文件结果清除许可。建议按 `get_observation → capture_screenshot → 游戏动作` 记录决策前画面，动作返回后再截图记录结果。两次调用分别采样，期间动画可能继续；比对时保留各自调用顺序与画面时间。

选牌时直接截图可见的选牌界面；调用 `set_selection_view(view="battlefield")` 后再截图，记录查看战场；返回选牌仍须显式调用 `set_selection_view(view="selection")`。截图本身不会切换两者。

| 错误 | 处理 |
| --- | --- |
| `invalid_request` | 参数错误时按提示修改；配置关闭时提示启用screenshots.enabled并重启MCP连接，recovery为check_configuration |
| `file_exists` | 换文件名或省略文件名 |
| `screenshot_unavailable` | 检查图形游戏及分辨率，headless 不支持 |
| `screenshot_save_failed` | 按具体提示检查目录、文件名／路径长度、权限、只读文件系统或空间／配额 |
| `timeout`、`transport_error` | 检查游戏与 IPC；先检查目录是否已有文件，避免重复记录 |

未知I/O或临时文件清理失败标记outcome:unknown；目标PNG可能已经存在，先检查目录和文件再重试。与其他工具共享控制锁和串行请求；取消不能撤回已经完成的保存。可确认的本地保存拒绝按上述条件保留旧许可，其余失败在游戏动作前重新观察。

## 验证

边界测试：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p test_screenshots.py
```

真实游戏验证使用独立存档、IPC及日志目录，运行时准备见[往返指南](roundtrip.md)。图形套件会创建测试局、使用技能药水和结束回合：

```sh
.tmp/mcp-venv/bin/python scripts/gui_suite.py --suite tests/game/data/gui_suite_screenshots.json --output .tmp/screenshot-check/gui
```

[verify_screenshots.py](../../tests/game/verifiers/verify_screenshots.py)要求显式设置STS2_AGENT_VERIFY_IPC_DIR；变量缺失或空白时，在创建客户端、报告和配置前拒绝，不回退到共享IPC。suite用gui场景复用已有对局，独立menu／headless场景要求新实例位于主菜单。工具集合从注册表校验，不固定数量。报告及capture目录须使用新位置，已有报告／图片时拒绝覆盖。

独立headless验证先在一个终端启动实例：

```sh
python3 scripts/run_roundtrip.py --work-dir .tmp/screenshot-check/headless-game
```

另一个终端运行：

```sh
STS2_AGENT_VERIFY_IPC_DIR="$PWD/.tmp/screenshot-check/headless-game/ipc" .tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_screenshots --scenario headless --report .tmp/screenshot-check/headless/evidence.json
```

menu场景使用同样的显式IPC约定和独立图形实例。当前验证结果及限制见[截图恢复实施记录](../research/2026-11-08-screenshot-recovery-implementation.md)；旧[审阅基线](../research/2026-11-08-capture-screenshot-development-notes.md)和[早期验证](../research/2026-10-30-screenshots-validation.md)保留其原始范围。
