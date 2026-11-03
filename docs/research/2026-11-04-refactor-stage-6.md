# 第 6 阶段：展示、悬停与共用读取

> 当前状态：已完成并验证，阶段清单 8/8，整体完成 6/7。第 7 阶段组合回归与收尾尚未开始；当前无正在执行步骤，暂无阻塞。

## 范围与核对基线

执行[架构计划第 6 阶段](../superpowers/plans/2026-11-03-tool-architecture-refactor.md#第-6-阶段展示悬停与共享领域片段)，从 `21989bf` 继续，不提前完成第 7 阶段或核销用户 TODO／逐工具审阅。本阶段对应 RF-10、RF-11 及 RF-14 的共享读取部分；RF-01–14 的最终逐项核对仍由第 7 阶段完成。

本次核对 Linux 游戏 `v0.107.1`（release build59260271）、RitsuLib `0.6.10`，游戏目录的 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`，与本任务审查基线相同。原生证据为 `NRelicInventoryHolder.RefreshStatus/OnFocus`、`NClickableControl.RefreshFocus/ConnectSignals/Enable/Disable` 和 `NButton.OnDisable`，本机反编译证据位于 `.tmp/2026-11-03-architecture-refactor/`。

`RelicStatus.Disabled` 只改图标着色，不禁用 holder。原生 RefreshFocus 使用启用或 AllowFocusWhileDisabled 条件，并允许鼠标和控制器焦点；OnFocus 读取实际遗物的 HoverTips。没有确认到自然游玩中已显示但两种入口均关闭的实例，本轮通过明确标记的测试夹具注入验证，不当作自然机制复现。

## 实现与职责

- RelicInspection.Static 同时供基础观察与详情使用；统一展示顺序、计数、熔化外观。不按视口坐标截断，但保留实际隐藏、透明、零缩放、裁剪及待删除检查。持有总数仍独立计数，不把隐藏当成遗物丢失。
- RelicInspection.Inspect 分离静态条目和悬停正文。full/default 无法读取悬停时保留条目并关联 `relics.N` note，summary 原生直接跳过正文且没有该 note。筛选只裁剪关联来源，不重编号规范来源。
- HoverAccess 核对原生焦点条件，UI 与遗物共用基础焦点判断，各自保留屏幕或图标边界。普通没有关键词解释仍是合法空列表；未知提示类型照常失败。
- PotionInspection.DisplayedHolders 共用顶栏与详情的槽位枚举，详情额外保留交互条件，不把药水权限混进静态顶栏。
- HoverTextSources 共用 UI／战斗对象的标题加正文去重和来源顺序，领域本地化及 note 判断仍在领域入口。
- PrivateFields 从 CardSelection 迁出。必需字段缺失抛 MissingFieldException；Optional 保留在选牌多类型界面的 prefs／已选卡／完成源、动画字段探测，以及结算页多类型按钮的提示探测。不借迁移改变克隆牌堆、动态预览、半隐藏牌或比较侧别；CardAppearance 已共享实节点／浏览外观，不为搬迁再造一层格式化器。

原生 schema 调至 `36`，来源版本 Mod `0.55.0`、MCP `0.57.0`。inspect_relics 接受内部 `arguments.level`；省略保持 full，MCP 仅 summary 发送 level，既有 full 请求不改写。当前 scene/screen 解码支持已核验的 35/36；不承诺任意未来 schema。持续维护版本仍只在 README。

## 调用点清单

下表按源文件列出 OnScreen／Displayed／Browsable 的调用或委托位置（本阶段工作树），对应行号不是稳定接口。没有把 OnScreen 全局替换为 Displayed。

- OnScreen：屏幕内按钮、非浏览战场身体、手牌与 HUD 的实际控件；不是原生列表成员资格。
- Displayed：不按视口截断的状态／意图／充能球／悬浮剑／遗物图标和标签；保留实际裁剪与显示边界，零缩放由领域规则判断，充能球事件保留入场等待例外。
- Browsable：原生已打开的结算／历史滚动列表和展开内容；选择／浏览卡牌部分按领域枚举原生完整候选，不强行套同一个几何判断。
- Shown：节点生命周期和树可见性，不能单独证明控件位于画面或可悬停。VisibleUi.Text/Number 与 DisplayedText/DisplayedNumber 分别沿用相应谓词。

| 文件 | 谓词与行号 | 使用范围 |
| --- | --- | --- |
| [CardSelection](../../src/Sts2Agent/Actions/CardSelection.cs) | OnScreen: 96,99,147,151,160,184 | 动作控件、页面入口或原生操作前置条件 |
| [DeckEnchantSelection](../../src/Sts2Agent/Actions/DeckEnchantSelection.cs) | OnScreen: 44 | 动作控件、页面入口或原生操作前置条件 |
| [DeckUpgradeSelection](../../src/Sts2Agent/Actions/DeckUpgradeSelection.cs) | OnScreen: 30 | 动作控件、页面入口或原生操作前置条件 |
| [EventConfirmation](../../src/Sts2Agent/Actions/EventConfirmation.cs) | OnScreen: 73 | 动作控件、页面入口或原生操作前置条件 |
| [PotionActions](../../src/Sts2Agent/Actions/PotionActions.cs) | OnScreen: 49,62 | 动作控件、页面入口或原生操作前置条件 |
| [GameAdapter.AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs) | OnScreen: 26,42,55,100 | 动作控件、页面入口或原生操作前置条件 |
| [GameAdapter.RunEnding](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs) | OnScreen: 50,54 | 动作控件、页面入口或原生操作前置条件 |
| [GameAdapter.Shop](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs) | OnScreen: 47 | 动作控件、页面入口或原生操作前置条件 |
| [GameAdapter.Views](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs) | OnScreen: 45,127,139,142 | 动作控件、页面入口或原生操作前置条件 |
| [CardAdditionJournal](../../src/Sts2Agent/Events/CardAdditionJournal.cs) | OnScreen: 179,180,181,182 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [CombatResourceJournal](../../src/Sts2Agent/Events/CombatResourceJournal.cs) | OnScreen: 45,57,58 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [PotionJournal](../../src/Sts2Agent/Events/PotionJournal.cs) | OnScreen: 49,50 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [RunInventoryJournal](../../src/Sts2Agent/Events/RunInventoryJournal.cs) | OnScreen: 79,81,174,191,197,209 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [RunResourceJournal](../../src/Sts2Agent/Events/RunResourceJournal.cs) | OnScreen: 42 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [TurnJournal](../../src/Sts2Agent/Events/TurnJournal.cs) | OnScreen: 115,281,301 | 动作发生期间的已展示数据，不扩大隐藏区间记录 |
| [AncientInspection](../../src/Sts2Agent/Observation/AncientInspection.cs) | OnScreen: 48,50 | 当前领域画面、按钮、说明或列表的原有边界 |
| [CardAppearance](../../src/Sts2Agent/Observation/CardAppearance.cs) | OnScreen: 33,40 | 手牌／战场／顶栏；浏览克隆沿原有入口独立读取 |
| [CardView](../../src/Sts2Agent/Observation/CardView.cs) | OnScreen: 35 | 当前领域画面、按钮、说明或列表的原有边界 |
| [CombatObservation](../../src/Sts2Agent/Observation/CombatObservation.cs) | OnScreen: 81,100,122,187,189,190,192,194,226,240,249,272,293,298,299,328；Displayed: 169,179 | 手牌／战场／顶栏；浏览克隆沿原有入口独立读取 |
| [CombatResources](../../src/Sts2Agent/Observation/CombatResources.cs) | OnScreen: 14 | 当前领域画面、按钮、说明或列表的原有边界 |
| [CombatantInspection](../../src/Sts2Agent/Observation/CombatantInspection.cs) | OnScreen: 48；Displayed: 102,103,106,121,122 | 领域图标／标签展示；身体、动画及悬停条件保持独立 |
| [DeckView](../../src/Sts2Agent/Observation/DeckView.cs) | OnScreen: 43,49,61 | 当前领域画面、按钮、说明或列表的原有边界 |
| [DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs) | OnScreen: 36,90,95,99,101 | 当前领域画面、按钮、说明或列表的原有边界 |
| [EpilogueInspection](../../src/Sts2Agent/Observation/EpilogueInspection.cs) | OnScreen: 24 | 当前领域画面、按钮、说明或列表的原有边界 |
| [EventInspection](../../src/Sts2Agent/Observation/EventInspection.cs) | OnScreen: 40,50 | 当前领域画面、按钮、说明或列表的原有边界 |
| [MapView](../../src/Sts2Agent/Observation/MapView.cs) | OnScreen: 55 | 当前领域画面、按钮、说明或列表的原有边界 |
| [OrbInspection](../../src/Sts2Agent/Observation/OrbInspection.cs) | Displayed: 28,29,33,48,49 | 领域图标／标签展示；身体、动画及悬停条件保持独立 |
| [PileInspection](../../src/Sts2Agent/Observation/PileInspection.cs) | OnScreen: 30 | 当前领域画面、按钮、说明或列表的原有边界 |
| [PotionInspection](../../src/Sts2Agent/Observation/PotionInspection.cs) | OnScreen: 22,23,24,34 | 当前领域画面、按钮、说明或列表的原有边界 |
| [RelicInspection](../../src/Sts2Agent/Observation/RelicInspection.cs) | Displayed: 17,39,40,49 | 领域图标／标签展示；身体、动画及悬停条件保持独立 |
| [RestSiteInspection](../../src/Sts2Agent/Observation/RestSiteInspection.cs) | OnScreen: 29,41,44,53 | 当前领域画面、按钮、说明或列表的原有边界 |
| [RewardInspection](../../src/Sts2Agent/Observation/RewardInspection.cs) | OnScreen: 48,97,107 | 当前领域画面、按钮、说明或列表的原有边界 |
| [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs) | Browsable: 96,141,162,177,179,180,184,186,188；OnScreen: 110,120,126,135 | 已打开的结算／历史浏览主体；按钮仍按屏幕判断 |
| [RunUi](../../src/Sts2Agent/Observation/RunUi.cs) | OnScreen: 92 | 当前领域画面、按钮、说明或列表的原有边界 |
| [ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs) | OnScreen: 51,61,103,104 | 当前领域画面、按钮、说明或列表的原有边界 |
| [SovereignBladeInspection](../../src/Sts2Agent/Observation/SovereignBladeInspection.cs) | Displayed: 20,30 | 领域图标／标签展示；身体、动画及悬停条件保持独立 |
| [TargetInspection](../../src/Sts2Agent/Observation/TargetInspection.cs) | OnScreen: 37 | 当前领域画面、按钮、说明或列表的原有边界 |
| [TreasureInspection](../../src/Sts2Agent/Observation/TreasureInspection.cs) | OnScreen: 28,29,38,44 | 当前领域画面、按钮、说明或列表的原有边界 |
| [UiInspection](../../src/Sts2Agent/Observation/UiInspection.cs) | OnScreen: 26,46,51,56,96 | 当前领域画面、按钮、说明或列表的原有边界 |

遗物调用由 Shown 移到 Displayed，计数和 melted 改读 Displayed 标签／图标，修复原有“条目保留而字段因离屏丢失”的差异。实际裁剪仍删除相应条目，持有总数不随之减少。VisibleUi 的三个谓词和文本入口位于 [VisibleUi](../../src/Sts2Agent/Observation/VisibleUi.cs)。

## 验证记录

证据根目录：`.tmp/2026-11-04-refactor-stage-6/`。编译与纯检查不能替代下述原生验证。

- Python 新增测试先观察到旧实现拒绝 null 正文、缺少原生 summary 级别；修复后专题测试通过。全量初跑 580 项中 8 失败、1 错误：包括新增 level 的冻结请求差异及一个漏校验的 null 正文加非空 hover_tips；已修复校验，只 summary 发送 level，并显式记录冻结基线的这一私有协议差异，未重写冻结样本。第二次全量 580 项通过（41.171 秒）。
- C# 新增反射绑定／去重检查先因缺少入口而失败；实现后 91 项纯检查通过。Mod 编译零警告、零错误；中途测试变量重名由编译发现并修正。
- 原生夹具检查覆盖遗物变灰仍有正文、禁用显示条目保留、鼠标与控制器入口、实际裁剪、零缩放、透明、缺失纹理、离屏 0 计数与英语格式化副作用。
- 首次 GUI 在新增验证脚本误用不存在的 open_map 时停止；第二次在夹具地图不提供 close_map 时停止。两次原生遗物检查和缺失悬停 note 均已通过，但整批仍记为失败。脚本已按实际 inspect_map 和 available_actions 调整；后续 15 场景重跑通过，但该中间构建不作为最终审查修复的验收。
- 蜡质熔化检查补充离屏仍读取实际颜色的断言；不使用模型 IsMelted 猜测尚未刷新的图标。

## 决策与未验证范围

- 保持已经使用的主工作区和分阶段提交方式；不新建分支、合并或推送。证据保留到第 7 阶段。
- 卡牌实节点与浏览克隆已各自使用共同格式／外观片段，本轮不合并上下文不同的读取流程；这样保留目标预览与比较两侧的既有信息边界。
- 未确认自然游玩的不可悬停遗物场景；禁用／输入入口关闭／离屏及裁剪均为夹具验证。没有穷举第三方 Mod 的图层遮挡与自定义提示，也没有安装正式 Mod。

## 独立审查与修复门槛

独立只读审查发现 2 项 Important：结算异构按钮并不都有 `_hoverTip`，改成必需反射会拒绝正常结算；公共零缩放早退会抢先拦截充能球入场等待例外，可能取消待发布事件。另发现兼容 player_result 拒绝合法的新遗物 null 正文与 note。后者虽然不在生产 MCP／CLI 成功链路，仍是文档保留且测试／验证代码实际使用的入口，按对既有调用者的影响升级为本轮必须修复项，不留作遗留。

三项问题均完成 RED→GREEN：确定性零缩放入场、真实结算流程和兼容入口 null＋note，最终全量及 GUI 结果见下文；无延期审查项。

充能球回归检查已在修复前实际失败：`zero-scale entry waits without becoming public` 和 `zero-scale entry retains its pending channel event` 均为 false，pending channel 最终没有发布。修复将遗物的零缩放检查收回遗物入口，不修改通用 Displayed，从而保留原有充能球入场等待例外。该轮原生检查还发现两条旧断言仍要求离屏取消记录，与已经确认的无视口截断规则不符；实际返回了正确的 channel／槽位变化。验证改为核对保留这些离屏变化，另新增真实 ClipContents 裁剪夹具验证隐藏不回放，不修改玩法来满足旧断言。

兼容入口修复前，带 null 正文与规范来源的合法遗物结果在 player_result 有／无 operation 两种调用均报错；回归用例已复现。兼容处理复用 relic_details 校验新协议证据，同时保留旧的部分字段片段；没有建立另一份 null／来源规则。

审查修复后的首轮补充 GUI：充能球完整原生检查已通过（含确定性零缩放与真实裁剪），容量检查仅有两条旧断言失败，分别要求离屏 melted 为 null、不可悬停条目被删除。两者均与本轮已确认的展示契约相反，实际结果符合新契约；断言已同步，最终同构建套件另行重跑。该中间批次仍记为失败，不计作完整通过。

## 最终构建验证

- Mod 构建零警告、零错误；C# 纯检查 **91 项通过**（`csharp-final.log`）。
- 全量 Python **582 项通过**，39.749 秒（`python-final.log`）；包含冻结输出／请求差异、依赖方向、登记与媒体／会话约束。未重生成冻结样本。
- 最终 GUI **17 场景、21 步全部通过**（`gui-complete/report.json`），包括充能球完整事件检查、容量／熔化、遗物共用读取、蜡质熔化、充能球／奥斯提／君王之剑详情、选择、Affliction、牌组／牌堆、66×2 测试路由门控、事件／先古之民／火堆／商店、占卜媒体与建筑师背景。
- 最终构建 DLL SHA-256：`d94ad297ef7b013a920a060e3f3376e2c51dbf4429bfd404ff8591fdcbe8115d`；源构建与隔离运行时一致。所有最终 GUI 证据要求同一哈希。
- 独立 `victory_unlock` 结算回归通过（`gui-ending-complete/report.json`）：奖励、建筑师对白、胜利结算、总结／发现、解锁至返回主菜单。修复前 `gui-ending-red` 明确复现 NGameOverContinueButton._hoverTip 缺失；修复后全流程同构建通过。
- 标准库文件 CLI `--help`、Python compileall、629 个文档相对链接目标及 diff 空白检查通过。没有安装正式 Mod。

原生检查包括 **55 项充能球、29 项容量／熔化、31 项遗物检查**，全部通过。汇总见 `.tmp/2026-11-04-refactor-stage-6/verification-summary.json`。本阶段沿用已有主工作区与小范围共享片段，不合并上下文不同的卡牌读取；选牌、动画与结算的异构探测保留显式 Optional。若这些分类不再符合未来游戏类型，可能拒绝读取或缺少提示，届时须按新程序集核对，不能静默扩大可选范围。
