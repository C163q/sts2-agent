# 事件确认弹窗核对与验证

## 基线与源码证据

2026-10-31，Linux 游戏 v0.107.1，分支 v0.107.1，提交 59260271，发布于 2026-06-18；RitsuLib0.6.10。目标程序集为游戏目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。构建使用 .NET9；MCP 使用 mcp1.26.0。

原生类型和成员：

| 类型 | 核对结论 |
| --- | --- |
| `Trial.Reject/DoubleDown` | 首次拒绝生成致死红框选项；DoubleDown 创建 NAbandonRunConfirmPopup，不直接结束对局，选项允许重复点击 |
| `NAbandonRunConfirmPopup` | Ready 从 main_menu_ui 设置固定标题/正文及按钮；入场 tween0.3秒；Yes 走 RunManager.Abandon，No 只关闭 |
| `NVerticalPopup` | Header、Description、YesButton、NoButton；两个按钮连接 Released 回调及 Close；Close 调用 NModalContainer.Clear |
| `NModalContainer.Add/Clear` | 记录当前唯一 OpenModal；Clear 排队释放子节点并移除模态，遮罩另有退出 tween |
| `RunManager.Abandon/AbandonInternal` | 单人异步启动放弃任务，标记 IsAbandoned，原生强制杀死玩家；不能把调用返回当作任务完成 |
| `CreatureCmd.Kill` | 所有玩家死亡后调用 RunManager.OnEnded(false)，打开原生游戏结束画面 |

证据为上述目标版本反编译源码。新增核对产物位于忽略目录 `.tmp/2026-10-31-confirmation/source/`；Trial、弹窗及 RunManager/CreatureCmd 沿用[事件调研](2026-10-31-events.md)中同一程序集证据。没有引入新的第三方库或依赖未核对的游戏接口。

## 实现与可见边界

Mod0.28.0、MCP0.24.0、schema13。新增 `respond_to_confirmation`，默认工具39个，启用截图存档后40个。完整协议和真实 JSON 示例维护在[事件接口](../development/events.md#事件确认弹窗)。

Harmony 仅观察 DoubleDown 新增的真实弹窗，将节点、事件和 run 绑定；设置或其他路径打开相同类型不会取得授权。观察加入模态实例代次，外部换成相同文字的新弹窗会改变令牌。新字段只包含实际可见的固定原生本地化项；英文读取不切换 UI 语言。模态覆盖时事件和顶栏隐藏，地图、事件选择和药水操作不可用。

触发弹窗返回可操作的 `action_completed`；取消等候遮罩退出再回事件；确认等待放弃任务和原生整局失败信号，返回 `run_lost`，不自动点击失败画面。`complete` 表示该逻辑边界，不表示死亡字样等装饰动画已停止。

## 验证记录

本次忽略证据目录为 `.tmp/2026-10-31-confirmation/`。

- 基线236项 Python 通过。新增8项确认框测试先失败后通过；完整244项 Python、24项 C# 检查通过，Mod 编译0警告0错误。
- `cancel-run1.json`：36次 MCP/私有测试调用。实际进入 Trial、首次拒绝、第二次拒绝打开弹窗；截图与英文标题/正文/Yes/No核对。验证完整动作观察连续复用、底层事件/地图/药水拒绝、C#严格参数、取消前后玩家资源及事件 RNG 不变、再次打开、外部取消重开后的旧令牌拒绝、同类型无来源弹窗拒绝及退出后回事件。
- `confirm-run1.json`：9次调用。弹窗等待4秒后明确确认；原生 IsAbandoned、OnEnded(false)、HP0及 `run_lost` 核对，后续动作许可撤销。截图记录实际死亡画面。
- 真正图形截图来自隔离游戏视口：`cancel-run1/02-confirmation.png`、`03-cancelled.png`、`04-unowned.png`，以及 `confirm-run1/03-run-ended.png`。右上角有原生遥测提示，未遮挡确认框；没有改动正式游戏画面或对局。

Python 测试同时验证字段过滤、缺损观察不授予许可、严格参数、未知弹窗的人工边界，以及真实 stdio TextContent/structuredContent 相同。测试中本地假游戏传输用于注入坏响应；原生来源、合法性及结算依赖上述真实游戏验证。

## 审阅与关联回归

独立只读审阅未发现确认框核心逻辑的阻断问题；发现两处启用截图的旧验证脚本仍断言39个工具。已通过真实图形实例复现两者在目录断言处失败，改为当前40个，并同步截图脚本过时的成功输出数量。后续图形重跑还复现了截图脚本写死1280×720、截图后误认为完整动作许可已撤销的旧断言；当前原始视口1760×990，完整动作观察可连续复用。验证脚本已改成核对PNG真实尺寸、连续动作成功以及切到地图后许可撤销，产品语义保持不变。`review-green/rewards.json` 的29次奖励调用、`review-final/screenshots.json` 的完整截图流程均通过；截图覆盖主菜单、战斗、选牌、战场查看、地图和牌组，包含文件名冲突及非法路径检查。问题报告保存于忽略的 `.tmp/2026-10-31-screenshot-verifier-report.md`。普通事件翻页/覆盖/旧ID、通用Trial入口、占卜地图覆盖与关闭、10次原生战斗动作观察连续复用均已通过。

验证构建 DLL SHA256 为 `9fe92013a3208cc9c0e230a7b60b097cf8a20de7ec131e6e6bdd227fdb5a9108`，与隔离实例实际加载文件一致。安装及正式重启状态另以交付记录为准。

## 未验证范围

未穷举57种事件的所有分支、多人、第三方事件或其他模态；未知弹窗继续人工输入。没有运行 LLM 自主对局。正式游戏须完整重启后加载新 DLL，MCP 须重连获取工具目录；隔离加载不代替正式加载验证。游戏本身在隔离退出时仍会输出 Godot 静态 StringName 清理错误，放弃测试会出现原生 `How did the game end??` 提示，不声明启动或退出日志全无警告。
