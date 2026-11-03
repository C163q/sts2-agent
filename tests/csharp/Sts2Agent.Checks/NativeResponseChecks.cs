using System.Text.Json;
using Sts2Agent;

internal static class NativeResponseChecks
{
    public static void Run(Action<bool, string> check)
    {
        check(new Request("id", "get_state", null).WantsDivinationImage,
            "legacy requests retain board media by default");
        using var noImage = JsonDocument.Parse("{\"include_divination_image\":false}");
        check(!ResponseOptions.Parse(noImage.RootElement).IncludeDivinationImage,
            "explicit response options suppress board media");
        foreach (string bad in new[] { "null", "[]", "{\"include_divination_image\":null}",
            "{\"include_divination_image\":1}", "{\"extra\":true}", "{\"include_divination_image\":true,\"include_divination_image\":false}" })
        {
            bool rejected = false;
            try { using var value = JsonDocument.Parse(bad); ResponseOptions.Parse(value.RootElement); }
            catch (JsonException) { rejected = true; }
            check(rejected, "malformed response options are rejected: " + bad);
        }
        using var observed = JsonDocument.Parse("{\"snapshot_id\":\"own\",\"schema_version\":35,\"scene\":\"event\",\"screen\":{\"status\":\"covered\",\"view\":\"map\"}}");
        using var inspection = JsonDocument.Parse(ResponseBuilder.Inspection(observed.RootElement,
            new { snapshot_id = "wrong", scene = "wrong", hand = new object?[] { null } }));
        var state = inspection.RootElement;
        check(state.GetProperty("snapshot_id").GetString() == "own"
            && state.GetProperty("scene").GetString() == "event"
            && state.GetProperty("screen").GetProperty("view").GetString() == "map"
            && state.GetProperty("schema_version").GetInt32() == 35
            && state.GetProperty("hand")[0].ValueKind == JsonValueKind.Null,
            "all details bind the same snapshot context without removing null slots");
        var buffer = new TurnEventBuffer(1);
        buffer.Add("stars_changed", new() { ["before"] = null, ["after"] = 3 });
        var transition = TransitionResult.Create("choice_required", buffer);
        string result = ResponseBuilder.WithTransition(observed.RootElement.GetRawText(), transition,
            rewardResult: new { reward_id = 2, status = "pending" });
        using var action = JsonDocument.Parse(result);
        check(action.RootElement.GetProperty("transition").GetProperty("events")[0].GetProperty("before").ValueKind == JsonValueKind.Null
            && action.RootElement.GetProperty("reward_result").GetProperty("status").GetString() == "pending"
            && action.RootElement.GetProperty("snapshot_id").GetString() == "own",
            "structured action assembly preserves event nulls native outcomes and snapshot");
        foreach (string reason in new[] { "player_ready", "choice_required", "run_won", "timeout", "interrupted" })
            check(TransitionResult.Complete(reason) == (reason is not ("timeout" or "interrupted")),
                "shared completion rule: " + reason);
        buffer.Add("gold_changed", new());
        check(!TransitionResult.Complete("player_ready", buffer), "event truncation makes every boundary incomplete");
        var evidence = new RequestExecution();
        evidence.UiInteractionStarted(); evidence.RecordCapture(() => observed.RootElement.Clone());
        using var failure = JsonDocument.Parse(ResponseBuilder.WithExecution(
            ResponseBuilder.Error("id", "screenshot_unavailable", "capture failed"), evidence));
        check(!failure.RootElement.GetProperty("ok").GetBoolean()
            && failure.RootElement.GetProperty("execution").GetProperty("ui_interaction_started").GetBoolean()
            && failure.RootElement.GetProperty("execution").GetProperty("state_captured").GetBoolean(),
            "media errors retain independently recorded execution facts");
        foreach (Exception error in new Exception[] { new TimeoutException("direct"),
            new System.Reflection.TargetInvocationException(new TimeoutException("reflected")),
            new AggregateException(new TimeoutException("single aggregate")) })
        {
            using var classified = JsonDocument.Parse(ResponseBuilder.Failure("id", error));
            check(classified.RootElement.GetProperty("error").GetProperty("code").GetString() == "timeout",
                "wrapped timeouts retain the original transport classification");
        }
        var captured = new RequestExecution();
        var capturedSnapshot = captured.RecordCapture(() => ObservationSnapshot.Create(
            "{\"schema_version\":35,\"scene\":\"event\",\"screen\":{\"status\":\"visible\"}}", false, null, null, null));
        bool serializationFailed = false;
        try { ResponseBuilder.Inspection(capturedSnapshot.State, new { unsupported = (Action)(() => { }) }); }
        catch (NotSupportedException) { serializationFailed = true; }
        using var captureFailure = JsonDocument.Parse(ResponseBuilder.WithExecution(
            ResponseBuilder.Error("id", "game_error", "serialization failed"), captured));
        check(serializationFailed && captureFailure.RootElement.GetProperty("execution").GetProperty("state_captured").GetBoolean(),
            "response serialization failure does not erase a completed capture fact");
    }
}
