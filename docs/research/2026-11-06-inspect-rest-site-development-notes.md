# inspect_rest_site 开发核验依据

> 当前状态：修复已实施、验收并合入main；本文保留原基线的65项Python、七类GUI、51次MCP及16份返回。当前实现见[实施记录](2026-11-06-rest-site-inspection-presets-implementation.md)。用户可读结论见[审阅记录](2026-11-06-inspect-rest-site-review.md)。

## 基线与证据

- 提交2e0037b，Mod0.71.2、MCP0.73.2、schema41；核对日期2026-11-06。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10。游戏安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，已重新核对SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建与隔离运行时DLL同为c290e150238ebb92e072a5cdc6aa210778237d2c76deb0a96c6c69a9fe64ca40，未构建、升级版本或正式安装。
- 原始证据根`.tmp/2026-11-06-rest-site-inspection-review/`。七类GUI共用拥有的隔离进程，场景间重建对局，不继承上一场景状态。

## 问题与建议范围

| 编号 | 优先级 | 证据、影响与建议 | 状态 |
| --- | --- | --- | --- |
| REST-01 | 中 | RestSiteRequest将无页面、覆盖、动画、队列和非单人合并拒绝，未标public_message；GUI各类公开错误均为The requested action is unavailable。提供共用InspectionUnavailableReason并用于读取与可用列表 | 待定稿，GUI已确认 |
| REST-02 | 中 | inspect_rest_site_details只判断scene及rest_site结构，不验证screen与详情是否一致。受控探针的四种covered/hidden矛盾响应均被接受并生成新许可。与其他已审详情保持同次上下文校验 | 待定稿；不是正常Mod穿透覆盖的证据 |
| REST-03 | 低 | 读取、available_actions都依赖操作Ready；Ready要求所有按钮OnScreen和动画/队列结束，Read又对选项Label做OnScreen。读取与点击限制混杂，离屏过滤也仍存在 | 源码确认，特殊UI未新增实测；建议小范围分离 |

full读取没有调用HoverAccess.CanFocus，而是对所有已列选项调用Option.Description。普通原生灰置选项的NButton仍启用、仅_isUnclickable阻止选择，OnFocus可显示说明，当前输出正确。特殊MouseFilter/FocusMode导致不可聚焦但仍显示的控件缺少统一note分支，仅源码核对；后续修复应保留静态字段、限制说明并给来源提示，不能把灰置直接当不可悬停。

## 当前链路

- [tool_registry.py](../../src/sts2_mcp/tool_registry.py)：effect=read、requires_permission=False，使用通用default/full，没有summary／筛选。
- [GameAdapter.RestSite.cs](../../src/Sts2Agent/Adapter/GameAdapter.RestSite.cs)：inspect与choose共用Ready前置；成功InspectionSuccess使用已捕获上下文，没有UiChanged或ForceClick。
- [RestSiteInspection.cs](../../src/Sts2Agent/Observation/RestSiteInspection.cs)：Current核对当前RestSiteRoom及有效节点；Exposed要求无地图／选牌／其他覆盖、无卡牌预览且非战斗；Ready进一步要求队列、_choicesTween、_descriptionTween、按钮执行与屏幕内状态。Read(full:true)逐项动态Description，基础观察Read()只提供静态选项及实际已展开的顶层说明。
- [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：inspect_rest_site与选择同样依赖Ready。
- [rest_site_details.py](../../src/sts2_mcp/output/rest_site_details.py)：验证选项ID唯一、字段类型和full说明，覆盖状态不允许包含详情；但未把screen与可见详情关联。共用inspection_details随后合并scene_context，并不会替该reader检查覆盖矛盾。
- [GameSession](../../src/sts2_mcp/game_session.py)已实现纯读取明确拒绝保留旧许可；首次拒绝不生成许可，坏响应应清除许可。REST-02意味着这类矛盾响应尚未被认定为坏响应。

## 目标版本原生来源

本地反编译证据均位于`.tmp/2026-10-31-rest-site/source/`，未纳入Git。

- RestSiteOption.cs：IsEnabled注释明确不可用仍可悬停；Generate可能推进RNG和修改状态。当前工具使用已有按钮，没有重新Generate。
- NRestSiteButton.cs：Create设置_isUnclickable，Reload灰置；OnRelease阻止选择，OnFocus不以_isUnclickable阻止说明；RefreshTextState直接显示Option.Description。
- NRestSiteRoom.cs：UpdateRestSiteOptions从当前Options构造按钮；SetText立刻设置说明，FadeOutOptionDescription运行1秒_descriptionTween。ShowChoices/HideChoices使用0.5秒_choicesTween。Ready把文字淡出、按钮是否屏幕内等纳入全部读取前置，故只读也受限制；未新增该淡出窗口的GUI复现。
- HealRestSiteOption.cs：说明使用GetHealAmount的HealVar.PreviewValue及ModifyExtraRestSiteHealText；本次GUI看到24HP和Dream Catcher追加卡牌。
- SmithRestSiteOption.cs、CookRestSiteOption.cs：灰置说明分别来自descriptionDisabled，烹饪人数/最大生命为UI文字中的2张/9点。
- LiftRestSiteOption.cs、KindleRestSiteOption.cs：说明包含3-TimesLifted及5层填火，来自UI同一getter。
- DigRestSiteOption.cs：真正拉取遗物发生在OnSelect，说明沿用基础文本；当前查看未调用OnSelect。
- CloneRestSiteOption.cs、HatchRestSiteOption.cs及MendRestSiteOption.cs：同一Title/Description规则；CLONE显示附魔名称，HATCH使用基础说明；MEND是多人目标流程。未新增这些分支的GUI样本。

## 受控坏响应探针

context-probe.json经真实GameTools执行，外部传输使用完整受控响应；有一个visible对照和四个坏上下文：covered、covered+map、covered+deck、hidden。五者均返回详情并生成许可。此探针核对的是外部层校验，不能冒充真实游戏输出或其可见性故障；正常Mod在GUI的四类覆盖均正确拒绝。

## GUI与许可验证

[七类清单](../../tests/game/data/gui_suite_rest_site_inspection_review.json)与[验证器](../../tests/game/verifiers/verify_rest_site_inspection_review.py)一次全部通过，128.991秒、51次MCP，PID216314已退出，运行时DLL保持原哈希。没有图像内容，也未操作桌面或模拟鼠标。

- no_rest：首次失败后end_turn需观察；成功观察后再次查看失败保留许可，直接end_turn成功。
- basic：直接以详情开始，无须先get_observation；default省略null。地图、牌组覆盖拒绝后可直接关闭，随后休息并读取options:[]与前进按钮。
- disabled：SMITH／COOK灰置但有具体说明；本地summary与option_ids参数拒绝后可直接合法休息。
- tent：五个原生候选，锻炼后移除LIFT，其余四项及proceed按原生状态读取。
- selection：锻造选择覆盖，详情拒绝后直接取消，恢复原选项。
- heal_rewards：休息打开追加奖励，详情拒绝后直接proceed结束子奖励，返回火堆。
- dig：读取DIG说明，没有选择或预读实际挖掘结果。

python.log中休息处、许可、GUI套件、输出边界及default预设相关65项通过，3.013秒；未重建或重复完整C#／Python回归。[16份真实返回](2026-11-06-inspect-rest-site-examples/README.md)包含15份full和一份default，来源与SHA-256写入manifest。

## 未验证范围

CLONE、HATCH、MEND、第三方选项、动画中的读取、离屏和不可聚焦控件没有新增游戏实测；特殊恢复量修正和全部遗物组合未穷举。文字映射、当前页面上下文及普通灰置/奖励/选牌等以本节所列GUI及目标源码为依据，不外推到所有变体。
