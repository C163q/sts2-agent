# 商店购买反馈与稳定性实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 当前状态：已完成，共1项，已完成1项；独立审阅可合入并已合入main，无未完成必需步骤；1项非阻塞校验建议记录在实施报告。

**Goal:** 修复购买前置拒绝、具体诊断、结果ID校验及金币动画导致的选择过期，增加明确pending。

**Architecture:** ShopInspection共用页面／单品原因，购买流程集中监听和结果；PurchaseOutcome独立表达任务终态与输入边界。ActionSettling增加独立选择动画标志，RunUi.GoldMotionPending同时服务常规资源等待和选择边界；MCP在结果精简前核对请求ID及pending边界。

**Tech Stack:** C#／Godot／Harmony、Python MCP、纯C#检查及隔离GUI。

**Spec:** [输出定稿](../../research/2026-11-07-buy-item-review.md#输出定稿)和其中引用的开发核验。

## Global Constraints

- item_id、default/full及精简回执保留；只在受支持输入且任务尚未结束时pending，不跟踪后续动作的购买终态。
- 原生购买、扣款、补货和选择；不直接改状态，不把领取失败当作未交互。
- 旧schema可缺购买结果；schema44的action_completed／choice_required要求结果，其他购买状态未知边界可省略；ID范围与请求一致性始终校验。
- Mod0.75.0、MCP0.77.0、schema44；当前版本统一维护README。
- 不正式安装或推送；英文注释／提交、中文文档；验收后自行合入main。

## Review Focus

- 预先拒绝可续接，但首次无许可、stale、已交互或矛盾证据不能恢复。
- 匹配且有界的购买ID才可续接，pending与输入边界相符；未知／故障任务不能变成canceled。
- 选择可等待金币动画，但不能等暂停的购买／卡牌任务，且中断等边界不被金币拖住。
- 静态商品读取与点击条件分别处理，隐藏、已替换、已用和价格不可读原因准确；开关及详情不退化。
- 送货员改payload后按同一Entry解绑；后续选择／奖励保持自己的回执，不附送购买终态。

### Task 1: 完成购买安全与反馈

**Files:** ShopInspection.cs、GameAdapter.Shop.cs、新GameAdapter.Purchase.cs／Actions/PurchaseOutcome.cs，ActionSettling.cs、GameAdapter.ActionObservation.cs、RunUi.cs；action_details.py、tool_registry.py、inspection_details.py及版本；tests/python/test_purchase_feedback.py、C#检查、verify_buy_item_review.py；相关当前文档及本任务记录／样本。

**Interfaces:** PurchaseUnavailableReason(Context?)与ItemUnavailableReason(slot)返回固定原因；Find仅定位当前ID／payload，点击统一经ItemUnavailableReason；PurchaseOutcome.AtBoundary(reported,task,awaitingInput)决定已知／pending／未知；ActionSettling.Sample追加可选choiceMotionPending；purchase_details(state,arguments=None)校验完整结果。

- [x] **Step 1:** Python写明拒绝续接、ID错配／越界／pending／缺结果的校验及未知边界；C#验证pending分类与选择等待金币但不等暂停父任务；GUI移除旧stale容忍，改具体提示和直接续接。
- [x] **Step 2:** 新Python、C#及至少一类旧DLL GUI确认RED；保留审阅中的金币过期证据作为原生复现，不自动重试掩盖失败。
- [x] **Step 3:** 实现共用购买／单品检查、同Entry监听过程及结果；接入明确拒绝协议、请求ID读取和schema44规则；共用金币动画标志接入选择等待。
- [x] **Step 4:** 针对性及全量Python、C#、构建通过；十类专项一次通过，额外重复变牌场景直接选择，回归开关和详情／显示；不允许选择stale或夹具等待。
- [x] **Step 5:** 同步文档、版本、十五到二十份典型修复后JSON；核对新旧来源／哈希、日志／进程／链接并提交feat: improve shop purchase feedback and recovery。

Python：`.tmp/mcp-venv/bin/python -m unittest tests.python.test_purchase_feedback`；RED为拒绝仍get_observation、错误ID被接受或pending不支持，GREEN为安全续接／坏响应清许可。C#通过`tests/csharp/Sts2Agent.Checks`，新增API缺失导致的编译RED须明确记录。

证据根`.tmp/2026-11-07-shop-purchase-feedback/`，所有输出使用全新路径；完整验收按[隔离运行](../../development/roundtrip.md)和[GUI指南](../../development/gui-testing.md)，最终verify_delivery.py验证实际报告而不重复编译。

## 最终审阅与合入

- [x] 独立最终审阅，必要问题按RED→GREEN处理。
- [x] 归档并校验本任务工作目录，合入main、删除临时分支并核销。
