# 药水预设、槽位筛选与读取边界实施

> 当前状态：实现与验证完成，inspect_potions 已核销。POTION-01–05、summary、原槽位筛选、位置映射与关联提示裁剪均已交付；独立审查发现已修复。暂无遗留实施步骤或阻塞。

## 范围与基线

按[药水审阅与定稿](2026-11-04-inspect-potions-review.md)和[实施计划](../superpowers/plans/2026-11-04-potion-inspection.md)实现。基线提交 ce8b689；交付代码版本 Mod 0.56.0、MCP 0.58.0、原生 schema 37。目标游戏 Linux v0.107.1、release build59260271，RitsuLib 0.6.10 兼容运行时；游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。持续维护版本表以 [README](../../README.md#当前版本与前提)为准。

原始日志、故障样本与测试报告保存在不入库的 `.tmp/2026-11-04-potion-implementation/`。游戏运行使用独立 runtime、IPC 和存档，正式 Mod 未安装。

## 问题处理与共用入口

| 问题 | 实现 |
| --- | --- |
| POTION-01 错误原因 | RequestDispatcher 公开经过明确许可的药水读取拒绝，区分顶栏未暴露、容器未就绪、槽位／图标无法识别。沿用 GameSession 读取恢复，无新增自动观察／重试 |
| POTION-02 离屏截断 | 展示读取使用 Displayed，药水槽位和图标不按视口位置截断；保留隐藏、透明、真实裁剪、纹理与非零面积检查 |
| POTION-03 悬停耦合 | VisibleHolders/Static 为读取入口，HoverAccess 只控制正文；不能悬停时保留静态信息并给 canonical note，原生 summary 不生成正文 |
| POTION-04 隐藏身份 | 基础观察与详情共用 DisplayedHolders/Static；任一无法识别槽位使整栏未知，详情明确拒绝，不把未知当空槽 |
| POTION-05 旧验证器 | 更新文件及 stdio 专项的上下文与字段检查；工具发现依据登记清单并识别已配置的可选截图工具，保留前后令牌、英语、位置及共享解释断言 |

OnScreenHolders 为事件保留原有屏幕内、启用与图标身份边界；InteractiveHolders 在其上增加焦点入口，供动作与目标定位使用。读取放宽不授权画外动作，不补记隐藏期间事件。药水静态格式供基础观察和专门工具共用，含条件出现的 usable_here、bouncing；商店商品页开／关可能改变 usable_here，不能预设为 true。

Python 使用共用 filter_indices、linked_help 和 null_fields，顺序为完整解码、筛选／摘要、空值过滤。只选空槽时不会留下 Block 提示；提示与不可悬停 note 的原槽位来源随筛选裁剪，压缩结果通过 slot_indices 映射。越界下标合并为部分错误，有效条目及其动作许可仍保留。

## 验证与独立审查

- 新增 13 个异步预设用例与 3 个 CLI 用例，均先失败后通过；覆盖省略／null／[]、空槽、重复、越界、关联裁剪、不可悬停 note、静态状态、坏响应及许可恢复。文件客户端保留原有默认 full 与 raw 协议，增加显式预设和槽位筛选。
- 完整 Python 回归 598 项通过；冻结架构基线未重新生成，新增 summary 的契约单独测试。
- C# 纯检查 91 项通过，解决方案构建无警告、无错误。
- 药水专项 GUI 6 场景／7 步骤通过（gui4/report.json），包含 27 项原生读取与事件边界检查；覆盖满栏、共享解释、空槽与筛选、summary、不可悬停 note、隐藏／离屏、牌组／三类牌堆／独立地图、真实使用与丢弃、后续选牌、火堆、商店商品页开／关。
- 相关 GUI 回归 4 场景／4 步骤通过（gui-regression/report.json）：display_readers、战斗／火堆 Fruit Juice 资源及 potion_used 事件、库存可见性。两批共 10 场景／11 步骤，使用同一 DLL SHA-256：`3207b4eaea1933c01829cb015e7cda9a0448c81ce5b96dd9899418be9b285249`。
- 最后补跑 GUI 清单、工具登记、文件基线及 CLI 的 22 项纯检查通过；示例逐份与原始响应、调用参数及哈希核对，文档链接与 diff 检查通过。
- 独立审查发现 1 项 Important：事件错误复用了更严格的悬停／动作门控。通过合成自动用药通知调用真实 PotionJournal 处理器，先复现遗漏，再拆分事件与动作入口；这是测试通知，不是自然发生的自动用药记录。未发现其他确定的 Critical／Important／Minor。

早期 GUI 失败与处理保留为证据：首轮测试漏做 null 数组保护；旧专项错误假定截图工具必定关闭；浏览测试在不可关闭的初始地图上尝试打开牌堆；商店测试错误假定 usable_here 必定为 true。均依据实际状态修正测试，没有放宽游戏动作条件。旧“直接调用原生药水工厂会保持能量前缀”的自检也不符合目标运行时；检查改为通过生产使用的 WithPotionValues 边界验证恢复，不把原生工厂本身承诺为只读 API。

## 完整公开返回与边界

代表性真实返回见[JSON 样例](2026-11-04-potion-inspection-implementation-examples/README.md)，保留调用参数、来源条目、文件与证据校验值。公开 JSON 不包含原生状态令牌、执行事实或测试控制数据。

GUI 的显隐、离屏和关闭悬停入口为隔离夹具；不代表已观察到正常游玩中的发生频率。保守的整栏未知策略仍限制读取其他槽位，未新增局部 unknown 对象。其他游戏版本、多人、第三方提示和所有药水动态正文组合未穷举验证；建筑师／结算顶栏入口保持既有规则，没有重新跑完整胜利解锁流程。
