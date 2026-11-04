using System.Text.Json;
using Sts2Agent;

internal static class CardPlayChecks
{
    public static void Run(Action<bool, string> check)
    {
        using var valid = JsonDocument.Parse("{\"cards\":[{\"card_id\":7,\"target_id\":3},{\"card_id\":8}]}");
        var inputs = CardPlayOptions.Parse(valid.RootElement, multiple: true);
        check(inputs.Length == 2 && inputs[0] == new CardPlayInput(7, 3) && inputs[1] == new CardPlayInput(8, null),
            "batch parsing preserves input order and omitted targets");
        foreach (string raw in new[] { "null", "[]", "{}", "{\"cards\":[]}", "{\"cards\":null}",
            "{\"cards\":[null]}", "{\"cards\":[{\"card_id\":true}]}", "{\"cards\":[{\"card_id\":-1}]}",
            "{\"cards\":[{\"card_id\":7,\"target_id\":null}]}", "{\"cards\":[{\"card_id\":7},{\"card_id\":7}]}",
            "{\"cards\":[{\"card_id\":7,\"card_id\":8}]}", "{\"cards\":[{\"card_id\":7}],\"extra\":true}" })
        {
            bool rejected = false;
            try { using var value = JsonDocument.Parse(raw); CardPlayOptions.Parse(value.RootElement, true); }
            catch (JsonException) { rejected = true; }
            check(rejected, "invalid native batch arguments are rejected: " + raw);
        }
        var progress = new CardPlayProgress();
        check(progress.Status == "not_submitted", "new card progress is not submitted");
        progress.Submit(); check(progress.Status == "queued", "accepted enqueue remains pending");
        progress.Begin(); check(progress.Status == "resolving", "begin execution is not proof of play");
        progress.Cancel(); progress.Finish(false);
        check(progress.Status == "not_played" && progress.Canceled, "Finished after Cancel remains not played");
        var skipped = new CardPlayProgress(); skipped.Submit(); skipped.Begin(); skipped.Finish(false);
        check(skipped.Status == "not_played", "native pile rejection without Cancel is not a play");
        var played = new CardPlayProgress(); played.Submit(); played.Begin(); played.Play(true);
        check(played.Status == "resolving", "visible play waiting on choice stays resolving");
        played.Finish(false); check(played.Status == "played", "visible real play and completion are both retained");
        var hidden = new CardPlayProgress(); hidden.Submit(); hidden.Begin(); hidden.Play(false); hidden.Finish(false);
        check(hidden.Status == "unknown", "hidden play cannot be reported as witnessed or absent");
        var failed = new CardPlayProgress(); failed.Submit(); failed.Begin(); failed.Play(true); failed.Finish(true);
        check(failed.Status == "unknown", "faulted native action is not reported as complete play");
        var replaced = new CardPlayProgress(); replaced.Submit(); replaced.Abandon();
        check(replaced.Status == "unknown", "lost lifecycle tracking cannot claim no play");
    }
}
