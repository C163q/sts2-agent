using Sts2Agent;

internal static class RelicCounterChecks
{
    public static void Run(Action<bool, string> check)
    {
        var buffer = new TurnEventBuffer();
        var changes = new RelicCounterChanges<object>(buffer);
        var relic = new object();
        changes.Sample(relic, "Girya", 0);
        changes.Sample(relic, "Girya", 0);
        check(buffer.Events.Count == 0, "counter baseline and duplicate redraw have no event");
        changes.Sample(relic, "Girya", 1);
        buffer.Add("hp_changed", new() { ["before"] = 1, ["after"] = 2 });
        changes.Sample(relic, "Girya", 2);
        check(buffer.Events.Count == 3 && (string)buffer.Events[0]["type"]! == "relic_counter_changed"
            && (int)buffer.Events[0]["before"]! == 0 && (int)buffer.Events[2]["after"]! == 2,
            "each displayed counter change keeps mixed event order");
        changes.ForgetExcept([]);
        changes.Sample(relic, "Girya", 99);
        check(buffer.Events.Count == 3, "restored hidden counter creates a fresh baseline");
        changes.Sample(relic, "Girya", null);
        changes.Sample(relic, "Girya", 0);
        check(buffer.Events.Count == 5 && buffer.Events[3]["after"] == null
            && buffer.Events[4]["before"] == null && (int)buffer.Events[4]["after"]! == 0,
            "visible counter label disappearance and zero reveal retain null comparison sides");
        var other = new object();
        changes.Sample(other, "Girya", 0);
        changes.ForgetExcept([other]);
        changes.Sample(other, "Girya", -1);
        check(buffer.Events.Count == 6 && (int)buffer.Events[5]["after"]! == -1,
            "displayed signed integer counters remain actual UI values");
        changes.Clear();
        changes.Sample(other, "Girya", 3);
        check(buffer.Events.Count == 6, "clearing counter state never replays previous values");
        check(buffer.Events.Select(e => (int)e["sequence"]!).SequenceEqual(Enumerable.Range(1, 6)),
            "counter changes use dense shared event sequences");
    }
}
