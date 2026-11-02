# 卡牌加入事件的公开去向

当前状态：完成。共 3 项，已完成 3 项；代码、协议、文档、独立复审及最终专项 GUI 验证均完成。没有剩余实施项；正式 Mod 未安装。

## 目标与契约

`card_added` 统一包含 `card.id/name` 和 `pile`。`deck` 表示永久牌组；`hand`、`draw`、`discard`、`exhaust`、`play` 分别表示战斗手牌、抽牌堆、弃牌堆、消耗堆和出牌结算区。身份已公开但去向没有公开证据时，`pile` 为 `null`。不输出堆内位置、顺序、牌面正文或未来结果。

普通出牌、抽牌、弃牌和消耗继续使用既有事件，不因进入其他牌堆就生成 `card_added`。永久变化仍限定 `pile:"deck"`。新生成牌的目标以实际入堆和公开 UI 对应关系为准，手牌满时的弃牌重定向必须正确；不能用稍后所在牌堆替代首次加入目标。

## 原因与证据

基线为 `ae4dc90`，Mod／MCP `0.46.0`、schema `27`。核对日期为 2026-11-02，游戏 Linux `v0.107.1`、RitsuLib `0.6.10`。目标程序集为游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；反编译证据保存在忽略目录 `.tmp/2026-11-02-card-add-destinations/source/`。

- `TurnJournal.CapturePublicCards` 只记录已展示身份，未提供战斗去向；Python `transition_details` 也仅允许 `pile:"deck"`。
- `CardPileCmd.AddGeneratedCardsToCombat` 先写入 `CardGeneratedEntry`，再执行实际入堆，最后才通知生成完成。后置通知可能晚于其他触发效果。
- `CardPileCmd.Add` 将满手牌重定向至 `Discard`；`CardPile.CardAdded` 可以确认实际目标，但不能单独作为公开信息。
- `CardCmd.PreviewInternal` 和 `CardPileCmd.Add` 创建 `NCardFlyVfx`；`Create` 的目标参数决定可见飞行终点。预览期间当前模型的牌堆不能直接当作已展示方向。
- `NCombatUi.PlayContainer` 是正在结算的牌所在区域，不是永久牌组。
- `CardCmd.Transform` 与通常生成的顺序相反：先 `AddInternal`，再在同一同步段写入 `CardGeneratedEntry`；不能只接受生成后才入堆的情况。
- `NExhaustPileButton` 初始隐藏，收到实际到达通知后才开始显示；第一次飞牌采样时入口未显示，并不表示整个动画都没有公开去向。

## 实施计划

使用当前工作区完成同一独立变更，验证后统一提交。技术栈为 C#／Harmony／Godot 原生 UI 与 Python MCP。

### 1. 公开协议

- [x] 在 `tests/python/test_inventory_events.py` 添加所有目标和未知目标的回执测试；缺失字段、非法目标及永久变化的战斗目标须被拒绝。
- [x] 先运行并确认旧实现失败，再修改 `src/sts2_mcp/output/game_output.py` 和 `transition_details.py`；仅 `card_added.pile` 接受新的目标范围。

### 2. 原生采集

- [x] 为战斗生成牌增加独立采集器：生成历史保留记录位置，实际入堆确定首次目标，可见手牌／结算区／消耗动画／飞牌动画提供公开证据。身份公开后发布；去向可以在本次动作内补全，隐藏和结束后不回放。
- [x] `TurnJournal` 转交生成、实际入堆和每帧采样；移除会重复记录的后置生成订阅。永久牌组保留现有独立记录。
- [x] 增加真实 MCP 场景和测试专用原生检查，覆盖生成进入手牌、抽牌堆、弃牌堆、满手重定向、普通移动不误报、身份与方向分离、隐藏及释放。

### 3. 验证与交付

- [x] 先以旧 DLL 运行目标 GUI 用例，确认缺少 `pile` 的失败，再构建新 DLL 重跑。
- [x] 串行执行完整 Python 测试与 GUI 验证，运行 C# 检查和构建，记录实际结果。独立审阅 UI 信息边界及生命周期。
- [x] 更新 [动作事件契约](../development/end-turn.md)、当前版本说明和本记录；仅提交本任务文件，不安装正式 Mod。

## 审阅重点

1. 手牌溢出必须报告实际弃牌目标。
2. 先生成再移动或自动打出不能将最终牌堆冒充初次目标。
3. 已展示牌名但未展示方向时保留 `null`，不能读取隐藏牌堆推断。
4. 隐藏、覆盖、战斗替换及释放后不补发；生成后置通知不能重复记录。
5. 公开协议仍拒绝永久变化的战斗目标和隐藏顺序。

## 验证记录

- 定向 Python 测试先在旧实现失败（战斗目标被拒绝、未知目标类型被拒绝、缺失 `pile` 被接受），修复后 6 项通过。首次扩展测试漏掉 `claim_reward` 必需的 `reward_result`；已补齐真实返回结构，没有改动该工具协议。
- 旧 DLL `bd61aac0d043aedf65e18ceac0fa2957389d38fd18e0c64cc5a377a95617b0b1` 的 GUI 复现保存于 `.tmp/2026-11-02-card-add-destinations/gui-red/`：Anger 实际生成事件没有 `pile`，新版校验拒绝后 MCP 返回传输错误；底层完整回执保留在本次独立 IPC 中。自有进程 PID 25815 已由 runner 关闭。
- 初次新 DLL 的 6 项公共 MCP 场景通过；原生检查发现消耗入口初次显现较晚，过早丢弃飞牌证据会留下未知方向。独立审阅另外发现后续普通回堆可以误填初次方向，以及战斗变牌的反向通知顺序。新增真实原生测试后，`.tmp/2026-11-02-card-add-destinations/gui-review-red/` 的 31 项检查恰有这 3 项失败。
- 修复为后续移动关闭首次方向确认；同一渲染帧内保留最多 512 项实际入堆关联，支持原生变牌的同步通知倒序；可见飞牌继续等待入口公开，隐藏、结束或后续移动则取消。关联本身不授予公开信息。
- `.tmp/2026-11-02-card-add-destinations/gui-review-green/` 的 31 项原生检查全部通过，独立复审无剩余 Critical／Important／Minor。该自有进程 PID 30042 已关闭。
- 完整 Python：`timeout 120s .tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'`，412 项通过，用时 32.283 秒，退出码 0；摘要见 `.tmp/2026-11-02-card-add-destinations/python-final.txt`。与 GUI 串行运行。
- C# 检查：`dotnet run --project tests/csharp/Sts2Agent.Checks/Sts2Agent.Checks.csproj --no-restore --no-build`，60 项通过；最终构建 `dotnet build Sts2Agent.sln -m:1`（配置游戏及 RitsuLib 路径、`--no-restore`），0 警告、0 错误。日志分别为 `csharp-final.log`、`build-review-green.log`。
- 最终 DLL SHA-256 为 `d4156a0bcdc4a918b3db1fcfa9ca5f6d5036d854914782affad0ee21d97ced79`，与独立运行时一致。`scripts/gui_suite.py --suite tests/game/data/gui_suite_card_additions.json` 的 7 组用例全部通过，包括 31 项原生断言；证据为 `.tmp/2026-11-02-card-add-destinations/gui-final/report.json`，用例耗时 149.531 秒，自有进程 PID 31369 已关闭。
- 实测结果：Anger 副本进入弃牌堆；刀刃之舞通常 3 张 Shiv 入手，满手时 1 张入手、2 张进入弃牌堆；Leaf Slime (M) 的 2 张 Slimed 记录为弃牌目标；普通出牌不新增 `card_added`；Flash of Steel 奖励记录为永久入组。原生检查另覆盖抽牌堆、消耗堆、结算区、真实变牌、未知方向、后续回堆、目标入口隐藏、整页隐藏、不回放及释放。
- 7 份变更文档的 221 个本地链接及代码块闭合检查通过，`git diff --check` 通过。Mod／MCP 为 `0.47.0`，schema 为 `28`；没有更新正式 Mod。

## 未验证范围

没有穷举全部卡牌、怪物或第三方 Mod 的生成路径；未进行多人游戏或手动输入竞态测试。可见性仍使用项目既有节点／区域规则，不承诺任意像素遮挡识别。无法取得初次公开去向的路径保留 `null`，不会从最终牌堆补猜。
