# 火堆详情预设、读取边界与共用静态格式实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 当前状态：实施与验收完成，共1项，已完成1项；独立审阅通过并已合入main，无剩余必修项或阻塞。

**Goal:** 修复火堆读取诊断和上下文校验，提供summary及option_ids，基础观察同步省略火堆description。

**Architecture:** RestSiteInspection共用页面可读原因、静态读取及按焦点能力提供的正文；动作保留独立Ready/Clickable。Python先完整校验，rest_site_summary共用静态投影，再筛选候选及关联note；get_observation直接复用静态投影。

**Tech Stack:** C# / Godot、Python MCP、隔离原生游戏GUI。

**Spec:** [输出定稿](../../research/2026-11-06-inspect-rest-site-review.md#输出定稿)及[源码与原审阅证据](../../research/2026-11-06-inspect-rest-site-development-notes.md)。用户已确认实现及基础观察省略description，沿用当前目录临时分支、完成后自动合入main的约定。

## Global Constraints

- inspect_rest_site支持default/full/summary，默认default；option_ids省略/null全部，[]空，去重、原生顺序、未找到ID合并。
- summary及get_observation三种主体预设省略火堆顶层和选项description；其余空值沿用预设规则。
- full不可悬停说明为null，并提供rest_site.options.<ID>来源note；default过滤null，summary去除悬停note，筛选裁剪相关来源。
- 完整校验先于输出精简；矛盾上下文和说明来源清除许可，纯读取明确拒绝保留已有许可。
- 选项读取取消视口过滤，保留隐藏／透明／裁剪边界；原生前进按钮通过移屏隐藏，仍按实际显示判断；点击仍须目标可交互，choose_rest_option的错误恢复留待该工具审阅。
- 原生数据读取与测试UI变换在游戏线程进行；专用夹具须testMode、suite和rest场景三重条件，并恢复改动。
- Mod/MCP功能版本升至0.72.0/0.74.0；schema41不变，版本兼容基线只在README维护。

## Review Focus

- 页面切换或覆盖：scene/screen与详情一致，旧令牌不能由坏响应续接；Python矩阵和GUI覆盖拒绝验证。
- 过滤成空、混合存在／不存在ID：完整校验全部行，保留页面上下文，错误和note引用原生ID；Python及GUI组合验证。
- 灰置与无法悬停不同：灰置保留可读正文，无法聚焦保留静态字段与note；GUI disabled/no_hover验证。
- 离屏与真正隐藏不同：只去除视口边界，隐藏、透明、裁剪仍排除；专用夹具逐项验证，并保留动作目标保护。
- 动画仍在运行：可读页面允许详情，但选项enabled按实际动作条件计算；原生FadeOutOptionDescription夹具验证，不把所有过渡当可读。

### Task 1: 共用静态格式、详情修复与筛选

**Files:**
- Create: `src/sts2_mcp/output/rest_site_presets.py`、`src/Sts2Agent/Testing/Fixtures/RestSiteDisplayFixture.cs`、`tests/python/test_rest_site_presets.py`。
- Modify: `RestSiteInspection.cs`、`GameAdapter.RestSite.cs`、`GameAdapter.AvailableTools.cs`、`rest_site_details.py`、`observation_details.py`、`tool_registry.py`及对应测试／测试入口。
- Docs: rest-site/mcp/observation/gui-testing、README、工具清单、既有两项TODO的已覆盖范围、实施报告与真实返回。

**Interfaces:**
- Consumes: VisibleUi.Displayed/DisplayedText、HoverAccess.CanFocus、scene_context、共用default过滤和GameSession读取许可。
- Produces: InspectionUnavailableReason(NRestSiteRoom?)、Inspect()；rest_site_summary(value)、rest_inspection_arguments(arguments)、rest_site_preset(payload,preset,option_ids)。

- [x] **Step 1: 写失败用例。** Python验证上下文拒绝、summary与基础观察静态字段一致、description省略、nullable正文来源、筛选顺序／空／缺失和完整校验优先。GUI验证器增加本地预设／筛选以及明确拒绝提示；新fixture-only代码提供offscreen/no_hover/disabled/hidden/transparent/clipped/fade模式，重置恢复。
- [x] **Step 2: 运行RED。** 新Python用例预期在预设／校验处失败；旧DLL的no_rest专项预期在具体原因断言失败。仅加入测试夹具构建一次、准备隔离运行时，再运行display_red，预期离屏HEAL被旧读取丢弃。每步保存全新日志，初始化、异步运行和清理以有限超时在沙箱外完成。
- [x] **Step 3: 实现。** 分离页面可读和点击就绪，公开固定原因；取消读取及全局Ready的视口条件，单个Clickable保留实际交互判断并拒绝无聚焦能力的按钮。读取保留静态行，full按CanFocus获取Description，否则null及来源。Python严格校验上下文、nullable正文与来源；共享静态投影去除description，先校验再摘要／筛选，note同步裁剪。注册参数且不发送Python筛选到原生，更新版本和受影响旧断言。
- [x] **Step 4: 验证。** 相关Python通过后，完整unittest discover、目标依赖dotnet build（无还原）及C# checks通过；准备隔离运行时，运行原七类专项加display，并回归旧verify_rest_site.basic和test dispatch双模式门控。GUI预期所有分支通过，基本场景须断言未完成活动时proceed:null；记录失败／修正而不覆盖证据。源与运行时DLL一致，所有自有进程退出。
- [x] **Step 5: 文档与样本。** 更新当前契约、原审阅保留基线；导出实际full/default/summary、筛选、note及错误的典型JSON，核对来源和哈希，清单闭合28/44。记录基础观察description约定与已修复状态的文档差异，未测范围如实保留。`.tmp/2026-11-06-rest-site-inspection-presets/verify_delivery.py`校验上述日志、样本、链接、版本、进程与git diff --check，预期通过。
- [x] **Step 6: 提交。** `feat: add rest site inspection presets and shared static output`。执行计划任务验收后进行一次独立完整审阅，按技能处理审阅结果、归档并核对本任务工作区，合入main和删除临时分支；不正式安装或推送。
