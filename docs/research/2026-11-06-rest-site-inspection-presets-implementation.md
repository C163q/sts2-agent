# 火堆详情预设、读取边界与静态输出

> 当前状态：实施与验收完成，共1项，已完成1项；738项Python、124项C#、九类最终GUI及79项双模式门控通过，独立审阅Critical0／Important0／Minor0，功能e951513已合入main，无剩余必修项或阻塞。

需求见[输出定稿](2026-11-06-inspect-rest-site-review.md#输出定稿)，原问题与实测基线见[开发核验](2026-11-06-inspect-rest-site-development-notes.md)，步骤见[实施计划](../superpowers/plans/2026-11-06-rest-site-inspection-presets.md)。

## 行为与实现

- inspect_rest_site支持default/full/summary和option_ids。default/full保留完整说明，summary提供静态按钮信息；原生ID筛选保持顺序、去重、合并未知ID，[]为空，省略或null全部。
- get_observation的full/default/summary共用相同静态投影，统一省略火堆顶层及选项description，其他null按预设处理。完整说明仍由inspect_rest_site.default/full提供。
- 读取与点击就绪分开，取消选项读取及全局Ready对候选的视口条件；真正隐藏、透明和裁剪仍排除，单个点击保留可交互判断。普通灰置可悬停时保留正文，无聚焦能力的按钮显示enabled:false。
- full不可悬停说明为null，note来源为rest_site.options.<ID>；筛选同步裁剪note，summary省略悬停note。
- 详情与可用列表共用固定原因判断；scene/screen、正文与来源先完整校验，再精简和筛选。纯读取的明确拒绝保留旧许可；坏响应清除许可。choose_rest_option的动作错误恢复留待该工具审阅。

[RestSiteInspection.cs](../../src/Sts2Agent/Observation/RestSiteInspection.cs)负责可读性、静态行及悬停正文；动作继续使用Ready/Clickable。[rest_site_details.py](../../src/sts2_mcp/output/rest_site_details.py)提供校验与共用rest_site_summary，[rest_site_presets.py](../../src/sts2_mcp/output/rest_site_presets.py)在校验后应用摘要和筛选。Python参数留在外部层，原生操作不增加筛选参数。

## 基线与证据

基线5291421，Mod0.72.0、MCP0.74.0、schema41；游戏Linux v0.107.1/release59260271，RitsuLib0.6.10。目标程序集及原生方法证据沿用开发核验：RestSiteOption动态说明、NRestSiteButton焦点处理和NRestSiteRoom的SetText/FadeOutOptionDescription。证据根`.tmp/2026-11-06-rest-site-inspection-presets/`。

测试先行：新增9项Python在旧实现出现50个预期失败；旧DLL no_rest因笼统提示失败。仅加入受保护UI夹具的构建（0警告／0错误，6.08秒，DLLc0fabe48ec4e9fe132b2051bb6113271b9e2a4787406cfedaefe55c32fb6d4f5）中，display_red证明HEAL移出视口后被旧观察丢弃，且详情不可用。两个失败游戏进程均退出，finally恢复UI。

首个正式构建0警告／0错误，4.06秒，DLL ea18ada7130df4abb4e0ea234f44feb632eb48701631592276d76761cb914e75。65项相关Python最终通过（2.963秒），124项C#通过。

完整Python首轮738项出现3失败／4错误：新projector在full无筛选时不必要地访问通用BoundaryProbe未提供的业务字段；按既有预设函数保留无筛选原样返回，实际响应仍先完整解码。旧MCP目录断言也补齐option_ids；冻结基线的新增summary由独立预设测试覆盖，未改写历史样本。针对边界28项通过后，完整738项通过（45.602秒），首轮日志保留。

专用RestSiteDisplayFixture仅在testMode、suite环境及rest场景存在时可调，提供no_hover/disabled/offscreen/hidden/transparent/clipped/fade，保留并恢复修改的控件属性；fade使用原生说明淡出方法。测试入口同时进入禁用测试模式／无suite的门控清单，不作为公开MCP工具。

## 隐藏前进按钮的修正与最终验收

首轮八类GUI（146.342秒，104次MCP）与旧basic（25.815秒，13次MCP）通过后，核对初始截图发现新读取多返回了屏幕外的禁用前进按钮。截图实际没有该按钮；目标程序集定点反编译的NProceedButton._Ready/OnDisable证实它以HidePos移出屏幕隐藏，Visible仍为true。该问题由扩大读取范围引入，不能把首轮通过当作完整验收。

补上普通火堆未完成活动时proceed:null的GUI断言，在上述DLL上确认失败（footer-red）。前进控件恢复实际显示判断，选项列表仍取消视口过滤；英文注释说明原生移屏隐藏的原因。NProceedButton.cs、原截图及失败响应保存在证据根，最初导出的30份临时样本另存pre-footer-fix-samples，没有改写原审阅16份样本。

最终构建0警告／0错误，4.56秒；构建与隔离运行时DLL同为4464221c7fc4b19d15a44cd9c2efdb71a1c1b7db2b78becde562bd2afa131e34。完整Python738项通过（40.453秒），C#124项通过。最终九类GUI一次通过（八类专项及旧basic，167.046秒、117次MCP、24次已记录原生辅助调用），自有进程已退出；其中双门控均拒绝79个测试入口。

最终覆盖离屏保留、隐藏／透明／裁剪排除、不可悬停静态字段加note、说明淡出时可读且动作禁用、原生隐藏前进、预设／筛选和纯读取拒绝后的直接续接。受控旧坏响应探针也重新运行：visible对照通过，四种矛盾上下文均拒绝且不生成许可。GUI所有轮次共238次MCP、50次已记录原生辅助调用，包含预期RED、前进修正前的通过轮次和最终验收，不表述为单轮全绿。

[30份最终实际返回](2026-11-06-rest-site-presets-examples/README.md)包含24份full、2份default和4份summary，无图像内容。[详情summary](2026-11-06-rest-site-presets-examples/inspect.summary.json)与[基础观察summary](2026-11-06-rest-site-presets-examples/observation.summary.json)的火堆主体相同；full仍保留proceed:null等普通空值，但不返回火堆description。

## 文档与验证边界

持续维护文档原先记载基础观察保留当前展开description、读取要求操作就绪且无summary／筛选，现按确认要求与实现同步；原审阅JSON保留，不覆盖为新格式。文档差异见证据根documentation-conflict-report.md。

CLONE、HATCH、MEND、第三方选项、真实超时和全部遗物组合未新增实测；静态字段与动态说明以已列GUI和目标版本源码为依据。

## 最终独立审阅与保留范围

独立只读审阅5291421..e951513，Critical0、Important0、Minor0，可合入；审阅核对现有日志与样本，没有重复运行测试，也没有发现需要进一步重构的职责混杂或逻辑重复。

保留原生前进控件的实际显示判断，有HidePos源码和截图支持；极端布局中若该控件完全离屏，也不会返回。选项列表仍取消视口过滤，两个范围有明确区别。

choose_rest_option的原有动作拒绝许可恢复按规格留待该工具逐项审阅；本次新增目标聚焦能力保护已检查。误调用该动作被拒后仍可能需要重新观察，现有TODO和未核销工具继续保留此范围。
