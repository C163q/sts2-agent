# 可选截图工具

`capture_screenshot` 用于记录 LLM 调用工具时实际显示的游戏画面，方便与 JSON 观察、出牌结果和选牌页面比对。适用于 Mod `0.27.0`、MCP server `0.23.0`、Linux 游戏 `v0.107.1`。截图保持当前游戏语言及视口原始分辨率，输出为 PNG。

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

MCP 启动时默认读取仓库根目录的 `mcp-config.json`，与启动进程的工作目录无关。默认文件不存在、没有 `screenshots` 或 `enabled=false` 时关闭；工具列表保持默认 38 个工具，调用截图工具会被拒绝。`enabled=true` 时增加截图工具，共 39 个。运行中不重新读取配置，修改后须重启 MCP 连接。

`directory` 在启用时必填。绝对路径直接使用；相对路径以配置文件所在目录为基准，支持开头的 `~`，不展开 `$HOME` 等环境变量。首次保存时创建缺少的目录，PNG 使用当前 MCP 进程的文件权限保存。目录不可写或磁盘空间不足时返回保存错误。

也可在原有启动参数中增加 `--config /absolute/path/mcp-config.json`。显式指定的文件不存在、JSON 损坏、重复键、未知字段或类型错误都会使启动失败，原因写到标准错误。实际配置已被 Git 忽略；`.env` 仍只用于构建和安装环境，MCP 不读取它。

截图配置只控制本项目的工具注册，不代替客户端自己的工具授权策略。Mod 必须更新到支持截图的版本并完整重启游戏；[接入方式](mcp.md)的其余参数保持一致。RitsuLib 不需要变动。

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

`filename` 可省略，此时生成 UTC 时间加随机后缀的文件名；指定时仅接受最长 128 字符、以 `.png` 结尾的文件名，不能含目录分隔符或控制字符。目录由配置确定。已有同名文件或符号链接返回 `file_exists`，不会覆盖。完整文件通过独占方式发布，保存失败不留下半张目标图片。

成功结果仅有 `path`、`width`、`height`，`content` 为同一对象的紧凑 JSON。工具不向 LLM 返回图片或 base64；客户端需要自行读取文件才能将其作为视觉输入。该工具有本地写文件副作用，MCP 注解为非只读、非破坏、非幂等。

## 画面与动作边界

截取调用时最近完成渲染的游戏视口，包括战斗、选牌、查看战场、地图和牌组页。工具不关闭遮挡、不滚动、不悬停、不切换语言，也不改变游戏流程；不会截图其他桌面窗口、窗口边框或系统光标。最小化、后台节流或渲染暂停时不保证产生新画面，可能超时；不自动激活窗口。

截图在帧后主线程读取像素，经内部 IPC 交给外部进程保存；用户文件路径不会传入游戏，游戏线程不等待文件保存。当前上限为 `16,777,216` 像素、PNG `32 MiB`。headless、空视口或超过上限返回 `screenshot_unavailable`，不以黑图冒充成功。

截图不准备动作权限；成功且采样令牌一致时保留已有权限。错误、取消或状态变化清除旧权限。建议按 `get_observation → capture_screenshot → 游戏动作` 记录决策前画面，动作返回后再截图记录结果。两次调用并非原子快照，入场与卡牌动画可能继续；截图不能证明前一个 JSON 与像素来自完全相同的时刻。

选牌时直接截图可见的选牌界面；调用 `set_selection_view(view="battlefield")` 后再截图，记录查看战场；返回选牌仍须显式调用 `set_selection_view(view="selection")`。截图本身不会切换两者。

| 错误 | 处理 |
| --- | --- |
| `invalid_request` | 修正文件名或参数；工具关闭时不能调用 |
| `file_exists` | 换文件名或省略文件名 |
| `screenshot_unavailable` | 检查图形游戏及分辨率，headless 不支持 |
| `screenshot_save_failed` | 检查配置目录、文件系统权限和剩余空间 |
| `timeout`、`transport_error` | 检查游戏与 IPC；先检查目录是否已有文件，避免重复记录 |

与其他工具共享控制锁和串行请求。取消不能撤回已经完成的保存；错误后应重新观察再执行游戏动作。

## 验证

边界测试：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p test_screenshots.py
```

真实游戏验证只用于独立实例，先按[往返指南](roundtrip.md)准备运行时。图形验证启动参数为 `python3 scripts/run_roundtrip.py --windowed --potion-scenario skill`，在新实例主菜单运行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_screenshots.py --report .tmp/screenshot-check/graphical.json
```

验证会创建测试战斗、喝技能药水、切换选牌/战场、打开地图及牌组、结束一个回合，并保存截图。重复执行须更换报告目录，避免覆盖检查触发。headless 验证另启动新的无窗口测试实例，并给验证命令增加 `--headless`。阶段证据与未验证范围见[截图验证](../research/2026-10-30-screenshots-validation.md)。
