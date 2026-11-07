# 结算查看、展示状态与基础观察卡牌实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> 当前状态：已完成，共3项，完成3项；实现、验收及独立审阅单轮修复完成并合入main，临时分支清理。无阻塞。结果及边界见[实施记录](../../research/2026-11-08-result-inspection-implementation.md)。

**Goal:** 基础观察统一face，页面status准确表达展示进度，结算详情提供可靠诊断、校验及summary。

**Architecture:** 保留专项卡牌格式，基础观察显式选择face模式。各原生页面分离DisplayComplete与Ready，通过共用状态入口输出visible/not_ready/covered；Python共用状态校验。结算详情复用原生读取和公共摘要，完整响应先校验再投影。

**Tech Stack:** Python MCP/unittest，C# Godot/RitsuLib，隔离游戏GUI及现有测试夹具。

**Spec:** [结算输出定稿](../../research/2026-11-07-inspect-run-result-review.md#输出定稿)、[跨场景规则](../../research/2026-11-08-observation-consistency-review.md)。

## Global Constraints

- 不新增content_complete；主体not_ready表示当前展示未完成，visible表示当前展示完成，covered表示被覆盖。screen.status保持可见／覆盖语义；操作合法性仍独立判定。
- 基础观察full/default全部标准卡牌使用face_full/face_default，summary使用共用摘要；专项完整详情、比较身份及必要null保留。
- inspect_run_result新增summary；页面提示只保留source/title，卡牌摘要，药水／遗物只保留名称，故事正文保留。基础观察共用静态结果，但卡牌采用face／summary规则。
- 当前部分内容可读取且有not_ready标识，不读取隐藏、未揭示或未来内容；不因单人守卫、按钮禁用或队列阻塞本身声称展示不完整。
- 明确读取拒绝保留已有许可，矛盾响应清除；本任务不整改run_result_option动作恢复。
- 仅本地提交并合入main，不安装正式Mod、不推送。维护文档中文，提交与注释英文。

## Review Focus

- 动画中已显示的部分数据：status必须not_ready，未显示正文／悬停仍不泄露；原生GUI故障夹具及受控数据测试。
- 展示完成但按钮全部禁用：主体visible，动作不可用且查看可用；独立GUI检查。
- 非结算的事件／先古／建筑师／占卜／商店／宝箱／奖励／火堆：检查共用状态语义，保留既有动作检查和局部phase/view/chest；GUI覆盖。
- 错配screen、缺失完整条目、隐藏图标及来源引用：投影前拒绝，schema兼容边界明确；响应变异及GUI隐藏检查。
- 基础观察候选、卡包、比较和解锁卡牌：所有预设均不提供正文／逐牌解释，专项完整查看仍可；Python所有路径及典型GUI。

---

### Task 1: 基础观察卡牌统一face

**Files:** src/sts2_mcp/output/card_format.py、observation_details.py；tests/python/test_card_formats.py、test_run_ending.py及必要旧断言；相关维护文档。

**Interfaces:** format_game_cards增加selection_mode/result_mode，默认full以保留专项路径；observation_details显式传face_full。default仍走公共空值入口。

- [x] 编写所有候选／卡包／比较／结算face及专项完整保留用例，运行专项确认RED。
- [x] 实现显式模式映射；更新与目标相反的既有断言，不改历史样例。
- [x] 专项及完整Python套件通过；提交`fix: use card faces throughout basic observations`。

### Task 2: 页面主体展示状态与操作就绪分离

**Files:** 新增src/Sts2Agent/Observation/PresentationState.cs；将RunResultMotion扩为共用PresentationMotion；修改EventInspection、AncientInspection、EpilogueInspection、RunResultInspection、DivinationInspection、ShopInspection、TreasureInspection、RewardInspection、RestSiteInspection；Python共用页面状态及各详情校验；测试状态夹具及GUI验证器。

**Interfaces:** PresentationState.Status(bool exposed,bool complete)输出三种状态；每类页面DisplayComplete使用已核对的原生展示信号。Ready维持原操作条件，新增或复用DisplayComplete，不能用按钮或任务就绪代替展示进度。

- [x] 编写Python not_ready部分数据、visible禁用按钮及screen可见性分离用例；原生状态／动画夹具先在旧DLL确认失败。
- [x] 核对目标程序集的展示字段；实现共用入口和对应原生DisplayComplete，详情／基础观察复用；不完整时统一note。
- [x] Python解析允许not_ready并核对上下文；既有状态有业务意义时保留phase/view/chest，操作检查不放宽。
- [x] 构建、C#、Python专项及完整套件通过；原生跨页面稳定／动画／禁用／恢复GUI验证；提交`refactor: separate presentation status from action readiness`。

### Task 3: 结算详情诊断、摘要与完整校验

**Files:** RunResultInspection、GameAdapter.RunEnding、GameAdapter.AvailableTools；src/sts2_mcp/output/run_ending_details.py、结算预设、tool_registry；测试结算检查及GUI流程；README版本、schema及维护文档。

**Interfaces:** RunResultInspection.InspectionUnavailableReason提供具体只读拒绝；Read提供当前完整或部分可见内容及提示来源；result_summary按已确认字段投影；get_observation复用静态结果并保留face卡牌。

- [x] 编写错配页面／缺字段／提示来源／summary／读取恢复用例，先运行确认RED。
- [x] 实现详情读取与动作分离、具体错误、当前协议完整校验和summary；隐藏或不可悬停提示不越界，徽章引用使用当前基础列表。
- [x] 统一版本Mod0.79.0、MCP0.81.0、schema47；更新必要协议消费者与真实验证器。
- [x] 专项、完整Python、构建、C#及GUI通过：胜负首屏／汇总、教程、时间线、章节、卡牌／药水／遗物解锁、本局详情夹具、无关菜单、partial／禁用及错误恢复。
- [x] 导出真实full/default/summary JSON，验证来源／链接／DLL／自有进程退出，更新现行文档并提交`feat: add consistent run result inspection presets`。

## 最终交付

一次全分支独立只读审阅；按实际影响处理，必要修复RED→GREEN，无重复审阅。更新工具清单为42/44，合入main，清理临时分支及本计划专属工作区；保留未验证边界及证据。
