# 事件确认弹窗设计

## 目标与范围

接通目标游戏 v0.107.1 的 Trial 事件原生放弃本局确认框。仅支持单人、由当前 Trial 的 `DoubleDown` 实际打开的 `NAbandonRunConfirmPopup`；设置、主菜单及未知来源的同类弹窗不授予操作。沿用[事件调研](../../research/2026-10-31-events.md#trial-的确认框)的第三步范围，不自动代选，不增加地图旅行。

## 观察与操作

新增可空 `confirmation`，包含 `status: "visible"`、`type: "abandon_run"`、英文 `title`、`description`、`options`。两个选项各含 `id: "confirm" | "cancel"`、原生 `text`、`enabled`。`screen` 为 `{"status":"visible","view":"confirmation"}`，底层 `event` 按覆盖规则置空；没有受支持弹窗时 `confirmation` 为 null。未知弹窗继续人工输入边界。

新增 `respond_to_confirmation({"option":"cancel" | "confirm"})`，严格拒绝缺失、非字符串、未知值或额外参数。需要当前观察许可；成功完整动作结果可继续复用。取消返回原事件，允许再次点击 DoubleDown；确认点击原生确认按钮，等待原生整局失败并返回 `run_lost`。弹窗出现本身是 `action_completed` 的可操作边界，不能继续标记人工输入。

## 实现约束

- Harmony 只观察 Trial.DoubleDown 调用前后新增的真实模态节点，将节点、事件实例与 run 实例关联；不按弹窗类型或文字推测来源。
- 独立 `EventConfirmation` 负责来源核对、可见读取和按钮合法性；GameAdapter 负责点击、状态许可和异步结算。使用已核对的原生 NVerticalPopup 按钮与 ForceClick。
- 弹窗实例变化必须改变观察哈希，防止外部取消再打开相同文字后重用旧令牌。
- 等待弹窗入场动画；取消还须等待模态遮罩退出，确认等待原生失败信号及画面稳定。不得阻塞主线程。
- 文本只读取实际可见的固定原生本地化项，英文渲染不改游戏语言或随机状态。

## 验证与交付

Python 验证字段过滤、覆盖边界、参数、许可复用、坏观察撤销许可及真实 MCP stdio。隔离图形实例验证真实中文弹窗截图与英文文本、取消/重复打开、旧令牌、底层事件/地图/药水操作拒绝、非事件来源同类弹窗不支持、明确确认后原生本局结束。回归事件、占卜和相关战斗流程。编译、全套 Python/C# 检查和独立审阅后提交，备份安装新 Mod；正式游戏完整重启后的加载另行标明是否验证。
