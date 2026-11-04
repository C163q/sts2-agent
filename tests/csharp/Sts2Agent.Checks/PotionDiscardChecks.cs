using System.Text.Json;
using Sts2Agent;

internal static class PotionDiscardChecks
{
    public static void Run(Action<bool, string> check)
    {
        var queued = new PotionDiscardProgress();
        check(queued.Status == "unknown", "discard without enqueue evidence is unknown");
        queued.Submit();
        check(queued.Status == "queued", "native discard submission is pending, not a removal");
        queued.ObserveDiscard(); queued.Finish(false);
        check(queued.Status == "discarded", "visible removal confirms the discard");
        var hidden = new PotionDiscardProgress(); hidden.Submit(); hidden.Finish(false);
        check(hidden.Status == "unknown", "finished discard without public removal evidence stays unknown");
        var canceled = new PotionDiscardProgress(); canceled.Submit(); canceled.Cancel(); canceled.Finish(false);
        check(canceled.Status == "not_discarded", "native Finished after verified Cancel retains cancellation");
        var failed = new PotionDiscardProgress(); failed.Submit(); failed.Finish(true);
        check(failed.Status == "unknown", "faulted discard cannot imply successful removal");
        var detached = new PotionDiscardProgress(); detached.Submit(); detached.Abandon();
        check(detached.Status == "unknown", "lost discard context is not a promise of later execution");
        var removedThenFailed = new PotionDiscardProgress(); removedThenFailed.Submit();
        removedThenFailed.ObserveDiscard(); removedThenFailed.Finish(true);
        check(removedThenFailed.Status == "discarded", "public removal remains known after a later hook fault");
        using var response = JsonDocument.Parse(ResponseBuilder.WithTransition(
            "{\"scene\":\"combat\"}", new { stop_reason = "choice_required", complete = true, events = Array.Empty<object>() },
            potionDiscard: new { slot_index = 1, name = "Block Potion", status = "queued" }));
        check(response.RootElement.GetProperty("potion_discard").GetProperty("status").GetString() == "queued"
            && response.RootElement.GetProperty("transition").GetProperty("events").GetArrayLength() == 0,
            "discard outcome is top level and never fabricates a removal event");
        using var other = JsonDocument.Parse(ResponseBuilder.WithTransition(
            "{\"scene\":\"combat\"}", new { stop_reason = "player_ready" }));
        check(!other.RootElement.TryGetProperty("potion_discard", out _), "other action replies do not inherit discard metadata");
    }
}
