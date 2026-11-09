# 故障机器人游玩反馈核验

> 当前状态：已完成。共 4 项，已完成 4 项；证据核对、附魔误报修复、球槽展示调整、文档、审阅与验证均已完成，无遗留事项。

## 基线与原始证据

核对日期为 2026-11-09，游戏 Linux release v0.107.1、build 59260271，RitsuLib 0.6.10；反馈对应 Mod 0.85.0、MCP 0.88.0、schema 49。交付目标为 Mod 0.86.0、MCP 0.89.0、schema 50。

原始对局回执位于 `.tmp/live/ipc/responses/`，时间约 16:43—17:55；截图为 `.sts2-agent/screenshots/01-neow.png` 至 `13-run-summary.png`，其中 `11-axebot-orbs.png` 展示充能球。核对游戏安装目录的 `data_sts2_linuxbsd_x86_64/sts2.dll`，相关类型为 `CardModel`、`AbstractModel`、`EnchantmentModel`、`CardCmd`、`Spiral`、`Sharp`、`LordsParasol`、`OrbQueue` 和 `NOrbManager`；反编译资料留在忽略目录 `.tmp/2026-11-09-defect-feedback/source/`。

## 附魔事件误报

结论：确有误报，需要修复。

- `1f09f61e4fb64112908bd2e28a0d5950.json`（17:21:44）在删牌选择打开时，包含同一张 Strike 的 7 条附魔变化；下一次选择回执又出现一条。
- `2da2ee43a31740b7b1a9f993c37b5c96.json`（17:34:31）先记录阳伞购买的卡牌、遗物和药水，随后同一张 Strike 重复 5 次附魔变化。这些购买事件与随后删牌预览触发的重复附魔通知分别核对。
- `9aa8d103add74e97852f7c358db8ab54.json`（17:50:46）中，Strike 与 Ice Lance 各重复 5 次；实际购买还包含 War Paint 的两次升级，应继续保留这些真实事件。
- 更早的 `7d748c414eb54abba0a52420bd9b31ef.json`（17:17:29）包含 Barrage+、Barrage 和 Ice Lance 的附魔变化。误报过滤针对副本，不按事件名称、连续次数或商店购买场景统一丢弃。

原生 `AbstractModel` 先复制实例字段，再调用 `CardModel.DeepCloneFields`。后者为副本复制附魔并调用 `EnchantInternal`，此时副本仍携带从原牌复制的 `EnchantmentChanged` 订阅；直到 `AfterCloned` 才清除订阅。本项目原有无 sender 回调捕获了原牌，因此副本通知被记到了原牌上。原生选牌预览与本项目 `BrowsedCard.Read` 的隔离副本都可触发这条路径。

修复将附加／清除的采集放到已核对的 `CardModel.EnchantInternal` 和 `ClearEnchantmentInternal` 调用上，使用实际被修改的实例核对永久牌组身份。直接附魔数量和基础变量修改仍沿原有数值采集路径记录；附加／清除内部的数值写入继续抑制重复事件。

## 球槽顺序与事件编号

结论：原来的数组和事件均使用原生从右到左的队列顺序，没有“激发 0、新球入 2”的编号矛盾。`NOrbManager.TweenLayout` 和手柄左右导航都能核对方向；`OrbQueue` 在尾部加入球，满槽充能先移除队首。

按确认的接口要求，公开数组改为从左到右，各非空球显式返回原生 `slot_index`，0 为最右槽；事件编号保持原义。例如三个槽只有一个球时，数组为 `[null, null, {"slot_index":0,...}]`。不增加可由编号直接确定的 `is_rightmost`。

`OrbInspection` 在读取牌面数值后按固定槽位反转输出，不按动画中的实时坐标重新排序；记录器仍使用原生节点列表，保留激发和入栏的实际编号。战斗对象悬停、空槽帮助与 sources 筛选路径都按公开数组下标关联，筛选结果中的 `source_indices` 继续报告原数组位置。完整契约见[充能球顺序](../development/combatant-inspection.md#充能球顺序)。

schema 50 对非空球的显式编号做完整校验；旧 schema 响应仍可按原格式读取。

## 验证

证据根目录为 `.tmp/2026-11-09-defect-feedback/`，只使用隔离游戏实例、测试存档与 IPC。

| 检查 | 结果 |
| --- | --- |
| 修改前预览误报 | `red-clone/report.json` 按预期失败：原牌附魔不变，6 个副本产生 6 条虚假附魔事件；其他原生检查通过 |
| 球槽输出测试 | 新增 4 项先失败后通过，覆盖各预设、编号保留、来源筛选、筛选前拒绝坏编号及旧格式兼容 |
| Python 全量 | 866 项通过 |
| C# 纯检查 | 155 个 PASS |
| Mod 构建 | 0 警告、0 错误 |
| 游戏回归 | `green-first/report.json` 的 11 局全部通过：副本误报、真实附魔变化、普通／阳伞删牌、球槽显示／可见性／筛选／预设、激发／缩槽／连续充能事件；测试 DLL 哈希与构建产物一致 |
| 独立代码审阅 | 未发现需修改的问题 |
| 文档与格式 | 改动 Python／JSON 可解析，306 个本地文档链接目标存在，`git diff --check` 通过 |

原生检查分别覆盖永久卡牌 25 项、物品变化 19 项、球槽可见性 20 项、球事件边界 55 项（24 组样本）。套件结束后已关闭自有进程。本次未更新正式游戏目录中的 Mod，也未操作正式对局。
