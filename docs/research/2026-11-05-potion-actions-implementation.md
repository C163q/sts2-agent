# 药水动作与地图覆盖：开发及验证记录

> 当前状态：实现、验证与独立审查完成，共 3 项，已完成 3 项；use_potion 已核销，discard_potion 仅共享错误恢复及规则修复，仍待独立内容审阅。暂无阻塞。用户确认范围见[审阅说明](2026-11-04-use-potion-review.md)，未新增 use_potion.summary，地图参数与主体／摘要不变。

本文供开发及复测使用；用户侧的问题说明与决定仍在审阅说明中。

## 实现范围

- `PotionStageUnavailableReason` 提供全局阶段诊断，供可用工具与请求复核复用；保留父事件、先古之民及购买流程等待可操作子奖励页时的例外。
- `PotionActions.RemovalReason/Reason/TargetReason` 分别处理原生移除限制、手动使用与目标原因；`PotionRequest` 的明确前置拒绝公开安全原因并声明 action_submitted:false，开始禁用槽位后不再给这一保证。use/discard 共用恢复声明，discard_potion 的完整内容审阅仍未核销。
- `PotionInspection.ExposedHolders` 保留原槽位位置；`DisplayedAt` 识别具体槽位图标，`Interactive` 只核对该槽位。基础观察仍保留原有“任一槽位无法辨认时整栏未知”的输出规则，动作及查询不会因无关槽位不能交互而整体失败。
- `PotionJournal` 仅记住实际展示过的药水身份，采样时清除隐藏或身份不符的旧记录；消费／丢弃事件检查仍暴露的槽位，而非要求已移除图标仍存在。`RunInventoryJournal.PotionObtained` 只依赖目标槽位展示，不使用整栏交互状态。
- `ObservationContext.Visibility` 统一已暴露地图的 screen.status 为 covered；map.status:visible 仍表示地图自身可见。Python 地图详情与基础观察的校验同步；图、候选、max_steps、selectable 和 get_observation.map 主体规则不变。
- 参数说明明确 potion_slot 使用原始槽位，筛选结果通过 slot_indices 对照；inspect_targets 简述目标提示与可用性，target_id 不再暗示只能从该查询取得。

## 基线与证据

- 修改基线 `cfa02a2`，开发分支 fix/potion-action-feedback。Mod `0.64.0`、MCP `0.66.0`，schema `40`；当前兼容表仍唯一维护在 [README](../../README.md#当前版本与前提)。
- 游戏 Linux v0.107.1，release build 59260271。2026-11-05 重新核对安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- RitsuLib 0.6.10，本地 `.tmp/ritsulib-end-turn-review` 提交 `772f280964f2efc7c7e2f29fc59844e68616dd57`。本地同版本原生源码及入口继承[开发核验记录](2026-11-04-use-potion-development-notes.md#基线与证据)，额外核对 `.tmp/2026-10-31-shop/source/NPotionContainer.cs` 的 OnUsedPotionRemoved 及 NPotionHolder.RemoveUsedPotion。
- 原始日志、完整响应、游戏报告及截图位于 `.tmp/2026-11-05-potion-actions/`。旧审阅 JSON 不覆盖；新样例在验证完成后单独保存。

## 已执行的验证

- 错误恢复及参数测试先 RED：4 项中出现 3 个失败；修复后专项 28 项通过。新地图上下文 3 项先 RED，正反向校验和其他地图测试已纳入完整集合。
- 旧 DLL 的 gui-journal-red、gui-map-red 分别确认缺少自动药水事件、地图 status 为 visible，均为预期失败，保留证据。
- 首次新构建 `991a4702be8d4f5a800b86fac3261a90e789806f42279027d604d4921373f060` 的 gui-focus 中地图通过，但自动药水仍漏记：原生通知时图标已被清除，DisplayedAt 不能作为移除事件发生后的条件。改用已记住的显示身份及 ExposedAt 后复测；采样仍要求当前图标身份匹配，避免恢复显示后补记旧事件。
- 最终采用构建 `7f04d0ee3ba6588e69e250bdeb8445f1f48f44f48470a84015d53dfad6582875`；34 类药水情形全部通过，另完成药水详情、地图选路和建筑师页面三组既有回归。采用的报告包含 38 次成功用例、37 类不同配置；其中地图用药在审查修复后重复补测，不将执行次数当作不同场景数。
- 完整 Python 最终 663 项通过（python-final.log，38.920 秒）；此前 660 项通过（python-map-sync.log，45.851 秒）；此前 python-combined.log 暴露旧测试仍以 covered 为非法状态等问题；后续补查确认过渡中 map:null 是合法旧行为，已保留该观察规则及对应旧测试。冻结的 tests/data/tool_contracts JSON 不变，仅测试包装对明确批准的 screen.status 变化作局部适配。
- 构建零警告／零错误，C# 114 项通过。混合异步专项在沙箱内达到 30 秒超时，保留 python-map-green.log；不算通过，完整集合在沙箱外验证。

## 独立审查、补测与限制

独立审查发现一项重要问题：can_continue 仍只接受 screen.status:visible，使 covered 的战斗外地图用药成功后丢失续接许可。新增 MapContinuationTests 与 MapPotionChainTests 两项先 RED，修复后 662 项通过；实测无中间读取的用药→用药→丢弃通过。战斗覆盖、其他页面覆盖、取消、超时、未知结果仍不因此续接。仅进行一次独立审查，无待处理的重要问题或低优先级发现。

原生地图刚打开时可选路状态会正常变化。gui-supplement 的连续动作成功，但“地图所有字段必须不变”的测试断言错误；gui-supplement-final 则遇到动画结束导致合法 stale_state。最终夹具在动作链开始前等待地图就绪，再验证无中间读取的续接；不自动重试已提交动作，也未修改地图就绪逻辑。两个失败目录保留。

进一步根据现行地图文档，保留 map:null 的过渡观察；新增一项先 RED 的回归，避免因统一 screen.status 强制补齐用户留待后续设计的地图主体。相关变更仅在基础观察校验，不改变 map 的生成规则。

[46 份完整返回](2026-11-05-potion-actions-examples/README.md)及其[来源清单](2026-11-05-potion-actions-examples/manifest.json)独立保存，不覆盖旧审阅样例。原始报告中统一 evidence 记录共 347 次 MCP 调用；旧专项子程序的额外报告另存。真实多人、自定义目标类型、RitsuLib 缺失及自然超时仍不纳入新增实测范围；未知结果由既有共用契约和模拟测试检查，不自动重试。

七个自有游戏 PID 均已核对退出。正式游戏与正式 Mod 安装未操作；交付保留本地修复分支，使用已验证的 DLL，不在提交后重新构建来替换测试证据。

样例来源、SHA-256、相对链接、JSON 片段、目录数量及工具核销检查全部通过，结果见 verification.json。文档与修复一并提交；没有新增用户 TODO，仅更新既有错误恢复条目的覆盖范围。
