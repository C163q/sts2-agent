# 先古致死馈赠的原生鼠标对照

> 当前状态：复查完成。有效原生鼠标点击也触发相同运行时致命错误；用户随后报告原版也崩溃，现按原版可复现问题记录，具体底层根因仍未确定。未修改产品。

关联[选择馈赠审阅](2026-11-07-choose-ancient-option-review.md)及[开发核验](2026-11-07-choose-ancient-option-development-notes.md)。

## 条件与有效输入

- 代码5e26549，Mod0.78.0、MCP0.80.0、schema46；Linux游戏v0.107.1，RitsuLib0.6.10，Godot4.5.1。
- 沿用原隔离夹具cape_lethal：当前生命／最大生命均为9，第一项Distinguished Cape已显示、启用并带致死红框。
- 用户说明旧鼠标尝试时没有确认控制授权，因此旧记录不能作为有效原生点击对照。复查在用户授权后，新开自有实例并保持窗口等待输入。
- 测试窗口绑定PID52128、窗口20971524。最初移动到960,732时，实际悬停在第三项，截图确认存在桌面缩放坐标偏差；校正到704,588后，第一项斗篷高亮，并显示Apparition及相关解释。
- 核对悬停截图后发送一次原生左键点击。此次选择未调用choose_ancient_option，也未经过该MCP动作的提交、等待或按请求建立的事件记录；观察只使用隔离游戏的只读IPC。

证据根`.tmp/2026-11-07-ancient-mouse-recheck/`：before.json／before.png为点击前状态，hover.png为偏移位置，hover-corrected.png为已核对的第一项悬停，hold_game.py及工具执行记录说明操作步骤。

## 结果与结论

点击后游戏stdout先出现“How did the game end??”，随后出现与两次MCP复现相同的错误：

```text
Fatal error. Invalid Program: attempted to call a UnmanagedCallersOnly method from managed code.
```

后续只读get_state没有返回，最终进程退出码为-6，即SIGABRT。201.820817736秒的实例总时长包含等待鼠标授权与逐步校对输入，不表示点击后的崩溃延迟。自有进程已退出。

这次有效鼠标对照说明，崩溃不以choose_ancient_option的专有调用路径为必要条件。该实例仍加载当前Mod与RitsuLib、采用直接入房夹具；单凭这项对照不能区分原生游戏、共用Mod Hook、依赖或夹具的影响。

Agent未在此实例中完成不加载Mod／依赖或自然推进的对照；用户后续的原版测试单列如下。

## 原版对照反馈

2026-11-07，在提供原版启动与控制台复现方案后，用户反馈：“原版游戏也崩溃了”。这是用户提供的独立对照结果，不是Agent启动并取得日志的测试实例。

原版方案以-nomods跳过Mod加载，通过settings.save的full_console启用原生控制台，并用ancient VAKUU DISTINGUISHED_CAPE打开馈赠；源码核对的原生命令还会补写地图历史。用户的结果说明，Mod、RitsuLib及MCP不是发生崩溃的必要条件；该问题按原版也可复现记录，不再作为选择工具三项整改的前置阻塞。

尚未取得用户原版崩溃日志，不能声称它与隔离环境的UnmanagedCallersOnly错误完全相同，也不能据此确定具体底层根因。原始隔离失败和无效鼠标探针继续保留；原版问题的记录不表示已修复或已完成正常死亡结算验收。

## 验证与范围

运行时及编译产物DLL均保持dcee25a818d107d90f22860fcd7e98d59185142eef6712ac3adc6932b9cc4b22，没有重建、正式安装或修改游戏状态执行方式。核对了点击前9/9与启用／警告字段、有效悬停截图、致命日志、SIGABRT、进程退出及两个DLL哈希；证据文件哈希见verification.json。

没有重复Python、C#或其他GUI用例；其余三项选择工具问题维持原审阅结论。
