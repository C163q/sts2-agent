# inspect_treasure 典型完整返回

基线 d01713c，真实 stdio MCP 完整 structuredContent；14 份样本，包括 12 份 full、2 份 default，均无图片。问题、候选 summary 及验证范围见[审阅记录](../2026-11-06-inspect-treasure-review.md)。

未开箱不展示预先生成的遗物。已领取和空箱的静态结构相同，以不同实测来源保留。覆盖／无宝箱错误保留当前笼统提示；许可差异通过 recovery 展示。opening 为瞬态，未单独采集其成功详情样本。

每份调用参数、来源及 SHA-256 见 [manifest.json](manifest.json)。

| 完整 JSON | 场景 |
| --- | --- |
| [closed.full.json](closed.full.json) | 未开箱，完整空值 |
| [closed.default.json](closed.default.json) | 未开箱，default 保留 relic:null |
| [opened-anchor.full.json](opened-anchor.full.json) | 已开箱，遗物正文及关键词帮助 |
| [opened-anchor.default.json](opened-anchor.default.json) | 已开箱，default |
| [collected.full.json](collected.full.json) | 已领取，仅有 Proceed |
| [empty.full.json](empty.full.json) | 白银熔炉空箱 |
| [nested-relic.full.json](nested-relic.full.json) | 可引出嵌套奖励的遗物 |
| [transform-relic.full.json](transform-relic.full.json) | 可引出变牌选择的遗物 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖拒绝 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖拒绝 |
| [selection-covered.full.json](selection-covered.full.json) | 变牌选择覆盖拒绝 |
| [extra-rewards-covered.full.json](extra-rewards-covered.full.json) | 额外奖励覆盖拒绝 |
| [no-permission.full.json](no-permission.full.json) | 无宝箱页且没有已有许可 |
| [with-permission.full.json](with-permission.full.json) | 无宝箱页，保留已有许可 |
