# 事件详情与占卜文字观察实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans 实施；沿用当前会话执行，完成后进行一次独立审阅。
>
> 当前状态：实现与验收完成，共1项任务，已完成1项；当前进行独立审阅，合入尚未完成，暂无阻塞。

**Goal:** 修复事件详情读取与校验，提供与玩家可见图案一致的占卜文字棋盘及共用事件摘要。

**Architecture:** 普通事件分开静态展示、悬停与点击，统一读取拒绝原因。占卜通过 UI 贴图、控件几何及已揭开格子转译可见部位，不读取 cell.Item 或物品模型位置；纯棋盘组装与 Godot 采样分离。Python 先完整校验，再按共用摘要投影；图片仅由 inspect_event.include_image 显式请求。

**Tech Stack:** C#/.NET 9、Godot 4.5.1、Python MCP、现有文件 IPC 与隔离 GUI 套件。

**Spec:** [核验与已确认规则](../../research/2026-11-07-inspect-event-review.md)、[开发依据](../../research/2026-11-07-inspect-event-development-notes.md)。下列具体化规则作为实施依据。

## Global Constraints

- inspect_event 支持 default/full/summary，默认 default；不新增筛选。
- get_observation.full/default/summary 的事件与占卜主体均使用 inspect_event.summary；actions_only/top_bar 保持既有范围。
- include_image 仅属于 inspect_event，布尔值、默认 false；get_observation 不接受此参数，也不请求 PNG。
- cell_rows 使用 #、.、s、S；visible_fragments 按坐标描述实际可见部位，未知保留 unrecognized。透明留白不因内部占用而填充。
- 静态图案尺寸和部位词表可提供解释；隐藏身份、内部物品分组及未来随机奖励不得进入返回。
- 原生绘制材料、悬停条件与 Image API 须核对源码或目标程序集；未知外观保留未知。
- 现行合同更新至 Mod 0.76.0、MCP 0.78.0、schema 45；不正式安装或推送。

## Review Focus

- 只显示卡牌下半部时，修改隐藏横幅的稀有度不得改变文字输出；由纯检查与游戏夹具对照验证。
- 隐藏格子和透明留白不能泄露存在的物品或内部矩形；由空白、同图换隐藏物品及每种图案局部揭开验证。
- summary 和基础观察省略正文后，仍须在完整解码时拒绝矛盾页面与损坏碎片；Python 参数／许可测试覆盖。
- 可见但不可点击选项仍应读取静态内容，悬停仅按实际有效输入与锁定条件判断；GUI 显示夹具覆盖。
- 默认文字不依赖 PNG 成功；显式请求坏图必须拒绝且不授予许可，action_only 和普通事件不产生图片；媒体失败与 stdio 检查覆盖。

### Task 1: 完成事件详情与文字棋盘

**Files:**
- 修改 EventInspection.cs、DivinationInspection.cs、GameAdapter.Event.cs／Divination.cs、GameAdapter.AvailableTools.cs。
- 新增 Observation/DivinationBoard.cs 与 Observation/DivinationGlyphs.cs；前者只组装已允许的格子与碎片，后者负责已显示 UI 贴图及部位转译。
- 新增 output/event_presets.py；修改 event_details.py、divination_details.py、observation_details.py／observation_presets.py、contracts/rooms.py、request_arguments.py、tool_registry.py、public_output.py。
- 测试位于 tests/python/test_event_inspection_presets.py、tests/csharp/Sts2Agent.Checks/DivinationBoardChecks.cs 与 tests/game/verifiers/verify_event_inspection.py；在原生测试入口注册显示／碎片验证夹具。
- 同步 events.md、divination.md、observation.md、mcp.md、TODO 中已有占卜条目、README 和工具清单；新实测样例与证据单独保存。

**Interfaces:**
- 共用 Python event_summary(value) 与 divination_summary(value) 从已校验数据投影；inspect_event_preset(payload, preset, include_image=False) 负责预设及图片尺寸元数据。
- 纯 C# DivinationBoard.Build(hidden, patches) 接收 11×11 覆盖状态及已揭开 UI 碎片，返回 cell_rows 与 visible_fragments；不依赖游戏物品模型。
- DivinationGlyphs.Read(screen, cells, hidden) 只读取当前 UI 图像及控件几何，产出供 Build 使用的片段。

- [x] Step 1: 写入并运行失败测试。核对事件各预设、无筛选、include_image 类型与默认值；矛盾页面、碎片缺失／重复／越界／被遮罩、S 标记；可见下半牌的等价输出、隐藏／空白、图片失败与许可。
- [x] Step 2: 实现共用拒绝、静态／悬停／点击分离及完整 Python 校验和摘要，运行针对测试转绿；记录原生输入和图文语义核对。
- [x] Step 3: 完成可见碎片验证并实现纯棋盘与 UI 转译，接入两观察入口及 inspect_event 可选 PNG；未知／不支持形状保留未知。
- [x] Step 4: 编译，运行 Python 全套、C# 纯检查和隔离 GUI。普通事件翻页／锁定／覆盖、占卜全部图案的局部与完整揭开、默认文字和可选图片、地图／牌组往返及奖励衔接均需新证据；失败保留并定位，禁止将容忍重试作为通过。
- [x] Step 5: 更新持续维护文档、版本与典型新 JSON，校验链接、样本来源及哈希、进程退出和 Git 范围后提交。Task-done 运行一次交付证据校验器，预期零错误。
## 最终审阅与合入

一次独立分支审阅，修复重要问题并运行有针对性的失败→通过检查；归档自有执行记录后合入 main 并删除临时分支。
