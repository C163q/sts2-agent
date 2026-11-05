# travel_to_node 典型 full JSON

以下是[审阅基线](../2026-11-05-travel-to-node-development-notes.md)下真实 stdio MCP 的完整 structuredContent，未手工删字段，均显式传入 preset:full。夹具只准备隔离局面，旅行由公开工具完成；不表示自然完整游玩。

| 场景 | JSON |
| --- | --- |
| 普通火堆；飞鞋跳线的到达结构相同 | [rest.full.json](rest.full.json) |
| 战斗开始，player_ready 及能量恢复／抽牌事件 | [combat.full.json](combat.full.json) |
| 入场遗物触发选牌，choice_required | [choice.full.json](choice.full.json) |
| 商店到达；宝箱到达结构相同，场景／操作列表不同 | [shop.full.json](shop.full.json) |
| 问号进入实际事件 | [event.full.json](event.full.json) |
| 第二幕起点进入先古之民 | [ancient.full.json](ancient.full.json) |
| 没有操作许可，未发送原生请求 | [no-permission.full.json](no-permission.full.json) |
| 额外参数错误，本地拒绝并保留已有许可 | [invalid-argument.full.json](invalid-argument.full.json) |
| 非候选节点，丢失已有许可；未开地图／覆盖／绘图拒绝的公开格式相同 | [unavailable.full.json](unavailable.full.json) |
| 查看后状态改变，原生拒绝旧状态 | [stale.full.json](stale.full.json) |

成功不附完整房间正文和候选卡牌，按需使用相应详情工具。图像块计数全部为 0。[manifest.json](manifest.json) 保存每份原调用参数、原始证据文件和数组下标、图像块计数与文件 SHA-256，可逐对象核对来源。
