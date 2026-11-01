using Sts2Agent;

internal static class VisibleResourceChecks
{
    public static void Run(Action<bool, string> check)
    {
        var buffer = new TurnEventBuffer(8);
        var value = new VisibleResourceChange("energy_changed", buffer, () => new { id = 1, kind = "player", name = "The Ironclad" });
        value.Sample(3);
        value.Changed(2, 3);
        buffer.Add("card_played", new());
        check(value.Pending && buffer.Events.Count == 1, "native values stay private until actually displayed");
        value.Sample(2);
        check(!value.Pending && buffer.Events.Count == 2 && (string)buffer.Events[0]["type"]! == "energy_changed"
            && (int)buffer.Events[0]["before"]! == 3 && (int)buffer.Events[0]["after"]! == 2,
            "visible resource publication retains notification position");
        value.Changed(1, 2);
        value.Changed(4, 2);
        value.Sample(3);
        check(value.Pending && buffer.Events.Count == 2, "animation frames never become resource events");
        value.Sample(4);
        check(buffer.Events.Count == 3 && (int)buffer.Events[2]["before"]! == 2
            && (int)buffer.Events[2]["after"]! == 4, "unrendered intermediate resource values are coalesced");
        value.Changed(3, 4);
        value.Changed(4, 4);
        check(!value.Pending && buffer.Events.Count == 3, "invisible changes with no public difference are omitted");
        value.Changed(2, 4);
        value.Sample(null);
        value.Sample(2);
        check(!value.Pending && buffer.Events.Count == 3, "covering a pending resource discards it without replay");
        value.Changed(7, null);
        value.Sample(7);
        check(buffer.Events.Count == 3, "hidden resource changes never publish after restoration");
        value.Changed(6, 7);
        value.Sample(6);
        check((int)buffer.Events[^1]["before"]! == 7 && (int)buffer.Events[^1]["after"]! == 6,
            "restored resources use the new public baseline");
        var fresh = new VisibleResourceChange("stars_changed", buffer, () => new { id = 1 });
        fresh.Changed(9, 9);
        check(buffer.Events.Count == 4, "a newly visible current value never invents its hidden previous value");
        fresh.Changed(8, 8);
        check((int)buffer.Events[^1]["before"]! == 9 && (int)buffer.Events[^1]["after"]! == 8,
            "synchronous UI updates preserve a previously visible baseline");
        check(buffer.Events.Select(e => (int)e["sequence"]!).SequenceEqual(Enumerable.Range(1, 5)),
            "discarded resource reservations leave no sequence gaps");
        var limited = new TurnEventBuffer(1);
        var capped = new VisibleResourceChange("energy_changed", limited, () => new { id = 1 });
        capped.Sample(3);
        capped.Changed(2, 3);
        capped.Sample(2);
        capped.Changed(1, 2);
        check(limited.Truncated && limited.Events.Count == 1, "resource capture shares the bounded action buffer");
        var revealBuffer = new TurnEventBuffer();
        var reveal = new VisibleResourceChange("stars_changed", revealBuffer, () => new { id = 1 });
        reveal.Revealed(1);
        check(reveal.PendingReveal && revealBuffer.Events.Count == 0, "first revealed counter waits for an actual number");
        reveal.Sample(0);
        reveal.Sample(1);
        check(!reveal.PendingReveal && revealBuffer.Events.Count == 1
            && revealBuffer.Events[0]["before"] == null && (int)revealBuffer.Events[0]["after"]! == 1,
            "first revealed count never invents a hidden old zero");
        reveal.Revealed(2);
        reveal.Sample(null);
        reveal.Sample(2);
        check(revealBuffer.Events.Count == 1, "covering a first reveal cancels it without replay");
        var consecutiveBuffer = new TurnEventBuffer();
        var consecutive = new VisibleResourceChange("stars_changed", consecutiveBuffer, () => new { id = 1 });
        consecutive.Revealed(1);
        consecutive.Revealed(2, 1);
        consecutive.Sample(2);
        check(consecutiveBuffer.Events.Count == 2 && consecutiveBuffer.Events[0]["before"] == null
            && (int)consecutiveBuffer.Events[0]["after"]! == 1 && (int)consecutiveBuffer.Events[1]["before"]! == 1,
            "a visible first reveal is published before a subsequent star notification");
        var sampledBuffer = new TurnEventBuffer(2);
        var sampled = new VisibleResourceChange("max_energy_changed", sampledBuffer, () => new { id = 0 });
        sampled.SampleChange(3);
        for (int i = 0; i < 20; i++) sampled.SampleChange(3);
        check(sampledBuffer.Events.Count == 0 && !sampledBuffer.Truncated,
            "unchanged visible capacity never reserves event positions");
        sampled.SampleChange(4);
        check(sampledBuffer.Events.Count == 1 && (int)sampledBuffer.Events[0]["before"]! == 3
            && (int)sampledBuffer.Events[0]["after"]! == 4, "visible capacity changes keep public endpoints");
        sampled.SampleChange(null);
        sampled.SampleChange(7);
        check(sampledBuffer.Events.Count == 1, "hidden capacity changes never replay on restoration");
        sampled.SampleChange(6);
        check(sampledBuffer.Events.Count == 2 && (int)sampledBuffer.Events[1]["before"]! == 7,
            "restored capacity uses its new visible baseline");
        sampled.SampleChange(5);
        check(sampledBuffer.Truncated && sampledBuffer.Events.Count == 2,
            "sampled capacity respects the shared buffer limit");
    }
}
