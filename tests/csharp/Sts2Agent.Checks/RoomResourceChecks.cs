using Sts2Agent;

internal static class RoomResourceChecks
{
    public static void Run(Action<bool, string> check)
    {
        var buffer = new TurnEventBuffer(8);
        var gold = new RoomResourceChange("gold_changed", buffer, () => new { id = 0 });
        gold.Sample(100);
        gold.Sample(null, crossingRoom: true);
        gold.Changed(100, 112);
        buffer.Add("relic_counter_changed", new());
        check(gold.Pending && buffer.Events.Count == 1, "room gold waits for a displayed endpoint");
        gold.Sample(106);
        check(buffer.Events.Count == 1, "gold animation ticks do not publish intermediate totals");
        gold.Sample(112);
        check(!gold.Pending && buffer.Events.Count == 2
            && (string)buffer.Events[0]["type"]! == "gold_changed"
            && (int)buffer.Events[0]["before"]! == 100 && (int)buffer.Events[0]["after"]! == 112,
            "room gold is published in its native event position");
        gold.Changed(112, 119); gold.Sample(119);
        gold.Changed(119, 112); gold.Sample(112);
        check(buffer.Events.Count == 4, "separately displayed gain and loss remain separate events");

        var health = new RoomResourceChange("hp_changed", buffer, () => new { id = 0 });
        health.Sample(60); health.Sample(null, crossingRoom: true);
        health.Changed(60, 65); health.Changed(65, 63); health.Sample(63);
        check(buffer.Events.Count == 5 && (int)buffer.Events[^1]["before"]! == 60
            && (int)buffer.Events[^1]["after"]! == 63, "unseen room health intermediates remain private");
        health.Sample(null, crossingRoom: true); health.Changed(63, 60); health.Changed(60, 63); health.Sample(63);
        check(!health.Pending && buffer.Events.Count == 5, "unseen round trips do not invent visible changes");
        health.Changed(63, 64); health.Sample(null); health.Sample(64);
        check(!health.Pending && buffer.Events.Count == 5, "covering a pending room resource cancels publication");
        health.Sample(null); health.Changed(64, 65); health.Sample(65);
        check(buffer.Events.Count == 5, "restored hidden resources do not replay old notifications");
        health.Changed(64, 70); health.Sample(70);
        check(buffer.Events.Count == 5, "a mismatched resource baseline is not exposed");
        var limited = new TurnEventBuffer(0);
        var capped = new RoomResourceChange("gold_changed", limited, () => new { id = 0 });
        capped.Sample(100); capped.Changed(100, 112); capped.Sample(112);
        check(limited.Truncated && !capped.Pending && limited.Events.Count == 0,
            "room resources share the event limit without waiting on a rejected reservation");
    }
}
