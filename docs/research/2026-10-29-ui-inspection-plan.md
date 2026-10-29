# 通用界面说明 JSON 实施记录

当前状态：已完成，共 3 项。文件接口、独立审阅、中文游戏验证及样本交付均已完成；新版 Mod 已安装，用户重启后已从正式缩小甲虫战斗只读采样。未接入 MCP，其他查看工具仍在后续范围。

## 目标与边界

依据 [悬停说明范围](2026-10-29-ui-hover-tip-audit.md)，分步实现，第一步只增加文件操作 `inspect_ui`，取得实际游戏 JSON。能力与意图、药水、遗物仍由后续独立工具处理；本次不增加 MCP 工具、不展开地图或牌堆、不补格挡说明。游戏基线为 `v0.107.1`，Mod 升为 `0.5.0`。

输出为 `scene: combat` 和 `hover_tips` 数组，每条包含 `title`、`description`、`sources`。`sources` 使用基础观察字段路径，例如 `player.energy`；同标题同正文合并，保留所有来源。英语格式化复用 `EnglishCardText.Read`，不触发悬停方法、不切换语言、不修改现有提示缓存。原始协议额外带 `snapshot_id`，玩法输出移除控制信息。

只读操作在 Godot 主线程同步完成，不要求动作令牌，也不进入 `available_actions`。当前仅允许无遮挡的战斗画面；其他场景返回 `illegal_action`。只对当前可见且具备悬停说明的对象读取，头像遵循 `ShowTip`，结束回合遵循当前准备状态，牌堆须已绑定。入口字段存在不代表当前具备提示。

## 实施与验证

### 1. 文件协议及读取

- [x] 新增 `UiInspection.cs`，负责可见对象筛选、英语提示生成、字段关联与共享提示整合；头像复用 `AscensionHelper.GetHoverTip`，其余按已核对的节点实现重建提示。
- [x] `GameAdapter.Execute` 在动作令牌检查前处理 `inspect_ui`；`roundtrip_client.py` 支持命令并保留明确允许的 `hover_tips` 字段，不引入卡牌或意图说明。
- [x] 先添加输出投影测试并确认失败，再实现并确认通过；新增主线程读取检查，编译核对目标程序集签名。

### 2. 游戏内检查与样本

- [x] 新增测试模式检查：英文能量说明、场景及来源、无越界提示、隐藏能量和结束回合过滤、默认隐藏星星排除、语言及缓存不变；所有 UI 扰动均在 `finally` 恢复。
- [x] 独立中文 GUI 实例读取 `get_state → inspect_ui → get_state`，确认令牌不变，保存 `.tmp/roundtrip/ui-inspection.json` 与检查报告；不操作正式存档。
- [x] 执行 Python 回归、目标版本编译及已有可见性检查。真实正式战斗读取需用户重启加载新版，不将测试战斗样本描述成用户当前战斗。

### 3. 交付

- [x] 更新当前说明、接口限制和验证记录；独立审阅后处理影响正确性的发现。
- [x] 将新版 Mod 安装至已有游戏 Mod 目录，保留已加载文件的原 inode；不停止用户游戏，不改 MCP 禁用配置。
- [x] 单独执行 Git 暂存及提交，随本记录交付。给出可审阅 JSON 链接、样本场景和未验证范围。

## 重点检查

覆盖菜单、过渡画面、裁剪或隐藏入口时不能读取对应模型说明；头像在无进阶且无成就限制时不得补提示；隐藏第二首领不能泄露；同名提示正文不同时不得合并；读取不改变语言、已有提示缓存、手牌描边、随机状态或游戏流程。地图场景、其他版本和其他 Mod 自定义图标未纳入。

## 验证证据

- Python 输出测试先出现 2 项预期失败（原转换丢弃 `hover_tips`），实现后全量 `30` 项通过；命令为 `.tmp/mcp-venv/bin/python -m unittest discover -v -s scripts -p 'test_*.py'`，沙箱外执行以支持 SDK 异步通信。
- SDK `9.0.122` 目标游戏程序集构建通过，`0` 警告、`0` 错误。
- 中文独立 GUI 实例生成实际 `11` 条提示，`.tmp/roundtrip/ui-inspection-check.json` 保留前、中、后读取且令牌完全一致；主菜单读取拒绝证据在 `.tmp/roundtrip/ui-setup.json`。
- `.tmp/roundtrip/ui-checks.json` 为 `15` 项全部通过，覆盖英语资源图标、头像进阶英语模板、隐藏/视口外/禁用过滤、来源和重复项、语言与原有能量提示缓存不变、重复读取一致；`.tmp/roundtrip/observation-checks.json` 为既有 `27` 项全部通过。
- `verify_hand.py` 同一实例读取 `5` 张手牌，观察令牌不变，既有 `8` 项手牌检查通过；报告为 `.tmp/roundtrip/ui-hand-regression-check.json` 和 `.tmp/roundtrip/hand-checks.json`。游戏日志无 `[ERROR]`。
- 测试战斗为 Ironclad 对 Slimes Weak，首领为 Vantom；无进阶、星星、消耗牌堆和当前房间图标，因此相关提示未出现在独立实例样本。
- 用户重启新版 Mod 后，在正式 Shrinker Beetle 战斗第 1 回合、生命 `64/80`、进阶 `6` 的场景完成 `verify_ui.py` 只读采样：`.tmp/live/ui-inspection.json` 共 `13` 条，包括头像累计进阶、当前 Enemy 房间和 Ceremonial Beast 首领说明。`.tmp/live/ui-inspection-check.json` 记录前、中、后观察令牌完全一致；未执行任何正式战斗动作。
- 双首领、可见星星、可见消耗牌堆和地图等场景未验证。全部独立测试实例已停止，正式游戏继续运行。

## 审阅修复

独立审阅发现初版只检查可见性，禁用的牌堆和结束回合仍可能附送当前不能悬停获得的提示。核对目标程序集 `NClickableControl.RefreshFocus` 后，读取增加 `IsEnabled || AllowFocusWhileDisabled` 条件，并保留允许禁用聚焦的派生节点规则。新增两项真实 GUI 检查先复现失败，证据为 `.tmp/roundtrip/ui-disabled-red-checks.json` 和 `ui-disabled-red-response.json`；修复后 `15/15` 检查通过，恢复后的重复读取及观察令牌仍一致。最终 Python 全量回归 `30/30` 通过，无未处理的阻断审阅项。
