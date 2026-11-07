# 先古详情预设与可见信息修复

> 当前状态：完成，共1项，已完成1项。产品、验收及独立审阅通过，合入main并清理临时分支；无剩余实现或阻塞。

依据[输出定稿](2026-11-07-inspect-ancient-review.md#输出定稿)及[实施计划](../superpowers/plans/2026-11-07-ancient-inspection-presets.md)。[23份修复后返回](2026-11-07-ancient-inspection-fixed-examples/README.md)与[原审阅样本](2026-11-07-inspect-ancient-examples/README.md)分开保存；当前接口见[先古指南](../development/ancients.md)。

## 实现

四项问题已处理：

- AncientInspection.InspectionUnavailableReason区分无对局、无先古房间、非单人及覆盖状态，提供关闭地图／牌组或查看选牌／奖励的具体提示；执行入口与available_actions共用该判断。只读拒绝沿用现有许可恢复策略。
- 成功详情要求同次scene:ancient、screen:{status:visible}与可见主体；全量字段和悬停来源先校验，再筛选或精简。坏响应清除许可，空筛选不能遮蔽错误。
- 选项lethal_warning直接使用原生WillKillPlayer回调；详情full/default保留布尔值，summary及基础观察省略false。schema46要求新字段；旧schema缺失时保持缺失，不伪造安全结论。
- 读取改用Displayed／DisplayedText，取消视口矩形过滤，保留实际隐藏、透明及裁剪规则。继续按钮区分可读与可点击，选项Clickable仍检查OnScreen；未揭示台词继续被排除。CanHover区分真实可用的鼠标／控制器入口，无法悬停时保留馈赠正文、返回空hover_tips，并在note中引用原始选项ID。

Python的ancient_presets负责summary和option_ids；ancient_details负责全量校验。summary保留名称、称号、页面说明、已显示对话、馈赠正文和按钮。get_observation.full/default/summary复用同一静态投影。option_ids省略/null取全部、[]为空、保留页面顺序、合并缺失ID到errors；note随筛选缩小，summary省略悬停不可用note。既有共用null过滤、上下文和notes装配继续复用。

Mod0.78.0、MCP0.80.0、schema46；当前基线集中在README。没有修改choose_ancient_option或advance_dialogue的错误恢复设计，没有正式安装或推送。

## 测试先行与构建

基线02eaa7d；游戏v0.107.1/release59260271、RitsuLib0.6.10、Godot4.5.1。目标程序集及原生源码依据沿用[审阅核验](2026-11-07-inspect-ancient-development-notes.md)。证据根`.tmp/2026-11-07-ancient-inspection-presets/`。

- 新增9个Python测试方法：初始22处断言失败，0.028秒，python-red-outside.log；接入后9项通过，0.105秒，python-green.log。覆盖参数路由、静态摘要／基础观察、筛选、完整校验、错误恢复及旧schema。
- 首次沙箱内异步测试在退出阶段受限，由60秒超时结束，部分日志保留；移至沙箱外。夹具首次构建因缺少Multiplayer命名空间及System.Environment歧义失败；只修正引用，build-fixture-fixed.log通过。
- 仅加入测试夹具、保留旧产品逻辑的DLL为d9507e78b7d6afd437ae6536a2a05dd7a8b0875eb75b2b34d1bb1f3bc01e7971。原生GUI先复现离屏馈赠缺失及致死标记缺失两项RED，56.250202404秒，PID43338退出，native-red/report.json保留。
- 首次完整Python807项运行38.309秒，发现4个失败及4个错误：无筛选默认投影的通用探针与历史目录断言。沿用其他详情的full／无筛选直接返回路径，更新新增参数／预设的旧目录断言；冻结契约JSON保持原样。修正后807项通过，39.447秒，python-full-fixed.log。
- C#145项通过，csharp.log。产品初次构建4.06秒；将可用工具列表也接入共用诊断后，最终构建4.10秒，均零警告／错误。最终DLL为dcee25a818d107d90f22860fcd7e98d59185142eef6712ac3adc6932b9cc4b22。

没有为无关功能扩大回归范围。最终构建后未再次修改C#，隔离运行时与编译产物保持同一哈希。

## 游戏内验证

新验证器verify_ancient_inspection通过真实MCP stdio工作；私有AncientDisplayFixture仅控制隔离页面的显示、禁用及裁剪，并在finally恢复。测试入口须同时满足testMode、suite及先古场景配置；公开工具目录不注册该入口。Native原生披风夹具分别保持80最大生命和通过原生LoseMaxHp降至9，均不领取致死馈赠。

最终12组用例在同一自有进程一次通过：288.501902867秒，PID45975；报告gui/report.json。显示探针同时验证85个私有入口在关闭testMode及关闭suite／场景两种状态下均被拒绝。两个自有进程均退出，未触碰正式对局。

| 组别 | 核验内容 |
| --- | --- |
| no_ancient | 冷读取拒绝不建立许可；已有许可时具体错误后可直接end_turn |
| basic | 冷详情、摘要、三个基础观察预设、null／空／重复／混合无效筛选、本地参数错误、资源不变、地图／牌组覆盖诊断、返回后直接领取与前进 |
| dialogue | 未揭示后文隐藏、原生逐句继续、末行后馈赠可选 |
| touch | 当前角色对应的Burning Blood／Black Blood悬停解释及正常领取 |
| selection／bundle／nested | 变牌、卡牌包、嵌套奖励覆盖时明确拒绝，当前专门详情工具仍可用 |
| safe／lethal | 详情false／true；default保留false，摘要／基础观察只保留true。人工核对实际80/80无红框与9/9红框截图，内容与回调一致 |
| display | 离屏仍可读且enabled:false；无悬停／禁用保留正文和来源note，筛选及summary正确移除无关note；控制器入口保留解释；隐藏／透明／真实裁剪均排除 |
| legacy_basic | 旧verify_ancients的普通领取、覆盖、资源与前进流程 |
| legacy_stability | 旧verify_ancient_stability的第一幕结束、进入先古、延迟采样后直接选择及旧许可拒绝 |

截图在gui/safe/verify/observation.png和gui/lethal/verify/observation.png；后者另存evidence.png。安全组启动后才为后续验证器增加显式截图及私有生命核对，安全画面的80/80由运行器既有截图确认；未声称该组执行了新增的私有断言。没有为截图重复运行已通过场景。

23份实际MCP返回包含18份full、1份default、4份summary，逐份保存参数、原始证据行／响应路径与SHA-256。离屏、无悬停及裁剪样本来自受控原生UI布局，说明读取边界；普通游玩未声称会自然出现这些异常布局。

## 文档与剩余范围

先古指南、基础观察指南、MCP入口、用户既有错误恢复／诊断待办范围与工具清单随接口更新。编辑MCP入口时发现占卜图片段落仍描述自动附图，已同步为默认文字、仅inspect_event可按需附图；占卜产品未修改，也未重复其旧验收。差异记录`.tmp/2026-11-07-ancient-inspection-documentation-report.md`。

未穷尽全部先古、角色与遗物组合；多人和任意第三方UI仍在现有支持范围之外。先古动作的错误恢复继续由后续逐工具审阅处理；这些未纳入新TODO条目。

## 独立审阅与合并

独立审阅/root/review_ancient_inspection_presets（gpt-6.1-sol/high，独立上下文）核对02eaa7d..fab770e，Critical0／Important0／Minor0，可合入。没有修复补丁或复审。

审阅列出的两项范围由主代理确认：

1. choose_ancient_option／advance_dialogue的既有恢复设计留在后续逐工具审阅。若此范围过窄，相关动作错误仍可能要求重新观察，需后续处理。
2. 多人及任意第三方UI继续处于当前原生单人支持范围之外。若需要更广兼容，仍可能需要人工交互及额外实现。

没有遗留Minor。实现提交fab770e，按项目约定本地快进合入main，清理feat/ancient-inspection-presets；没有推送或正式安装。技能工作目录仅归档本计划的五个文件，逐份核对SHA-256后删除原目录，兄弟目录保持原样；归档位于.tmp/2026-11-07-ancient-inspection-presets/inline-workspace/。

交付检查核对807项Python、145项C#、12组GUI、85项双模式门控、两项原生RED、两个已退出的自有进程、23份样本与18份成功响应重放、相对链接、版本及最终DLL哈希；记录见delivery-final.log。提交与合并后没有重建DLL或重复扩大测试。
