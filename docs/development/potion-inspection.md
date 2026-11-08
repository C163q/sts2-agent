# 药水详情、摘要与槽位筛选

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。`inspect_potions` 读取当前已展示药水栏的静态信息及按需悬停说明。动作及目标另见[药水工具](potion-actions.md)。

## 参数与返回

MCP 参数：

| 参数 | 规则 |
| --- | --- |
| `preset` | `default` 为默认：完整内容并按[公共规则](mcp.md#输出预设)省略普通 null；`full` 保留 null；`summary` 只读静态槽位数据 |
| `slot_indices` | 从 0 开始的原始药水槽位，与动作的 `potion_slot` 相同；省略／null 为全部，[] 为空；重复忽略，结果保持原生顺序 |

成功结果包含同次快照的 `scene/screen`，不附带 available_actions 或 transition。成功读取可直接提供下一动作许可，不要求先 get_observation；明确读取拒绝只保留已有许可，具体规则见[MCP 调用语义](mcp.md#调用和错误语义)。

| 字段 | 内容 |
| --- | --- |
| `potion_slots[]` | 从左到右的槽位；确认空槽为 null。已占用项包含 name，full/default 另有 description |
| `usable_here`、`bouncing` | 存在时保留的静态显示状态，与基础观察共用读取；例如商店中特殊药水的可用标记及药水弹跳提示 |
| `slot_indices[]` | 仅显式传入非 null 筛选数组时返回，与结果 potion_slots 逐项对应，值为原始槽位 |
| `slot_tip` | full/default 固定一份通用槽位 title/description，满栏及空筛选也保留；summary 不返回 |
| `hover_tips[]` | full/default 的额外悬停解释，按标题和正文同时相同去重；不重复药水主体正文，无解释时为 []；summary 不返回 |
| `hover_tips[].slot_indices` | 解释关联的原始槽位；筛选后裁剪，来源为空时删除整条解释 |
| `notes.hover_tips_unavailable` | full/default 中已展示但不能悬停的药水来源，如 potion_slots.2；筛选后无关联来源则删除；summary 不返回此 note |
| `errors[]` | 有效槽位仍正常返回，越界下标去重合并为 potion_slot_indices_out_of_range，不将越界当空槽 |

summary 的 potion_slots 与 `get_observation.summary.top_bar.potion_slots` 相同，不返回药水 description、slot_tip 或 hover_tips。原生 summary 直接走静态读取，不先生成正文再删除。空槽在所有预设中保留 null，不压缩成不存在的槽位。

例如，原槽位为 `[Skill Potion, null, Block Potion]`，使用 `{"preset":"summary","slot_indices":[2,1,2]}` 时，槽位部分为：

```json
{
  "slot_indices": [1, 2],
  "potion_slots": [null, {"name": "Block Potion"}]
}
```

上例中的格挡药水仍使用 `potion_slot:2`。full/default 的相关提示也引用原槽位 2，不改为压缩结果中的位置 1。只选空槽 1 时 hover_tips 为 []，不留下 Block 解释；notes 采用相同关联裁剪规则。参数格式、负数、非整数及未知字段本地明确拒绝，不发送原生请求。

## 显示与悬停边界

支持当前暴露的战斗顶栏、战斗外页面，以及地图、牌组和三类牌堆浏览覆盖上的药水栏；选牌页与切回战场时也按实际暴露情况读取。胜负结算仅在 outcome 页的顶栏暴露时可读，后续摘要与解锁页面不因此开放。用药条件见[场景与停止边界](potion-actions.md#场景与停止边界)。

药水槽位与图标不按视口位置截断；隐藏、透明、无纹理、零面积或被实际裁剪的图标不能用于识别名称。容器或任一槽位无法确认时，基础观察将整栏标为未知，full 中为 potion_slots:null；详情返回带具体原因的 illegal_action。未知不当作确认空槽，也不删除位置。

已展示但禁用、或鼠标与控制器悬停入口均不可用时，药水仍保留静态信息；full 的 description 为 null，并附不可悬停 note，default 省略普通空正文。其他槽位的正文继续可读。summary 不要求能悬停。

槽位说明是[可见信息边界](../observation.md)允许的固定帮助，即使满栏也可提供。正文来自当前药水实例的原生 HoverTip/DynamicDescription；技能药水说明其选择与费用规则，但不附送随机候选。共享解释按标题与正文同时相同去重，标题相同但动态值不同的提示分别保留。资源图标转成 `<Energy>`、`<Star>` 等，保留正文换行，未知提示类型显式报错。

读取在游戏主线程同步完成，复用独立英语作用域，不触发 OnFocus 动画、随机音效或用药流程；动态能量图标前缀在 finally 中恢复，不改写提示缓存。稀有度、模型 ID、未来结果和完整目标合法性不在返回范围；后者使用 inspect_targets。

## 文件客户端

文件客户端默认仍输出 full；可显式选择预设和原槽位筛选：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_potions --preset summary --slot-indices 2
```

`--slot-indices` 后不带数字表示空筛选，省略该选项取全部。`--raw` 返回原生协议与控制信息，公开筛选只在非 raw 输出中应用。原生文件操作仅接受可选内部 `level:full/summary`，不直接接受 MCP 的 preset 或 slot_indices。

## 验证入口与范围

静态及悬停读取见 [PotionInspection](../../src/Sts2Agent/Observation/PotionInspection.cs)，公开校验与槽位筛选见 [potion_details](../../src/sts2_mcp/output/potion_details.py)及 [potion_presets](../../src/sts2_mcp/output/potion_presets.py)。

`verify_potions.py` 与 `verify_mcp_potions.py` 检查当前返回结构、同次上下文、位置与基础观察一致、共享解释及原始槽位关联，以及读取前后的令牌、语言与状态不变。

[药水 GUI 清单](../../tests/game/data/gui_suite_potion_inspection.json)覆盖满栏重复提示、空槽、预设及筛选、不可悬停 note、隐藏／离屏边界、覆盖页、战斗与战斗外用药、丢弃及后续选牌。入口见[GUI 测试指南](gui-testing.md)。显隐及悬停扰动由隔离夹具注入，用于验证边界；自然游玩证据以实施记录注明的场景为准。

源码核对、验证证据及未穷举范围见[实施记录](../research/2026-11-04-potion-inspection-implementation.md)。
