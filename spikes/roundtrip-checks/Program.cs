using Sts2Agent;

static void Check(bool value, string name)
{
    if (!value) throw new Exception(name);
    Console.WriteLine("PASS " + name);
}

Check(TurnBoundary.Decide(true, false, true, false, false) == "choice_required", "choice before next turn");
Check(TurnBoundary.Decide(true, false, false, false, false) == null, "animations are not completion");
Check(TurnBoundary.Decide(true, false, false, true, false) == "player_ready", "next playable turn");
Check(TurnBoundary.Decide(true, true, false, false, true) == "combat_won", "native victory");
Check(TurnBoundary.Decide(true, true, false, false, false) == "combat_lost", "native loss");
Check(TurnBoundary.Decide(false, false, false, true, false) == "interrupted", "combat replacement");
var events = new TurnEventBuffer(2);
events.Add("died", new() { ["name"] = "Decimillipede" });
events.Add("revived", new() { ["name"] = "Decimillipede" });
Check(events.Events.Count == 2 && (int)events.Events[0]["sequence"]! == 1
    && (string)events.Events[1]["type"]! == "revived", "death and revival preserved in order");
events.Add("died", new());
Check(events.Truncated && events.Events.Count == 2, "overflow is explicit");

using (var actionEvents = new ActionEventScope(2))
{
    Check(ReferenceEquals(ActionEventScope.Current?.Buffer, actionEvents.Buffer), "one action owns the shared buffer");
    actionEvents.Buffer.Add("gold_changed", new() { ["before"] = 99, ["after"] = 89 });
    ActionEventScope.Current!.Buffer.Add("card_drawn", new() { ["card"] = new { id = 3, name = "Strike" } });
    string original = "{\"id\":\"fixture\",\"ok\":true,\"state\":{\"snapshot_id\":\"same\",\"transition\":{\"stop_reason\":\"choice_required\",\"complete\":true,\"events\":[]},\"reward_result\":{\"status\":\"pending\"}}}";
    using var recorded = System.Text.Json.JsonDocument.Parse(actionEvents.Apply(original));
    var state = recorded.RootElement.GetProperty("state");
    var transition = state.GetProperty("transition");
    Check(transition.GetProperty("events")[0].GetProperty("sequence").GetInt32() == 1
        && transition.GetProperty("events")[1].GetProperty("sequence").GetInt32() == 2
        && transition.GetProperty("events")[1].GetProperty("type").GetString() == "card_drawn",
        "resource and combat events keep one capture sequence");
    Check(state.GetProperty("snapshot_id").GetString() == "same"
        && state.GetProperty("reward_result").GetProperty("status").GetString() == "pending"
        && transition.GetProperty("stop_reason").GetString() == "choice_required",
        "event attachment preserves tokens, boundaries and native outcomes");
    actionEvents.Buffer.Add("hp_changed", new());
    using var truncated = System.Text.Json.JsonDocument.Parse(actionEvents.Apply(original));
    Check(!truncated.RootElement.GetProperty("state").GetProperty("transition").GetProperty("complete").GetBoolean(),
        "shared buffer overflow makes the action incomplete");
    string error = "{\"ok\":false,\"error\":{\"code\":\"illegal_action\"}}";
    string inspection = "{\"ok\":true,\"state\":{\"hand\":[]}}";
    Check(actionEvents.Apply(error) == error && actionEvents.Apply(inspection) == inspection,
        "errors and observations without transitions are not rewritten");
}
Check(ActionEventScope.Current == null, "disposing releases the current action buffer");
try { using var scope = new ActionEventScope(); throw new InvalidOperationException("fixture"); }
catch (InvalidOperationException) { }
using (var nextAction = new ActionEventScope())
    Check(nextAction.Buffer.Events.Count == 0, "failed and consecutive actions never reuse earlier events");

var settling = new ActionSettling();
var deferred = new TurnEventBuffer(4);
var firstSlot = deferred.Reserve("relic_obtained");
deferred.Add("max_hp_changed", new() { ["before"] = 80, ["after"] = 82 });
var hiddenSlot = deferred.Reserve("card_added");
deferred.Add("hp_changed", new() { ["before"] = 40, ["after"] = 42 });
Check(deferred.Events.Count == 2 && (int)deferred.Events[0]["sequence"]! == 1,
    "unpublished changes never enter a receipt or leave sequence gaps");
firstSlot?.Publish(new() { ["relic"] = new { name = "Strawberry" } });
Check(deferred.Events.Count == 3 && (string)deferred.Events[0]["type"]! == "relic_obtained"
    && (int)deferred.Events[2]["sequence"]! == 3,
    "late visible identity retains native occurrence order");
firstSlot?.Publish(new() { ["relic"] = new { name = "Other" } });
Check(deferred.Events.Count == 3 && (int)deferred.Events[1]["before"]! == 80,
    "publishing one reservation twice never creates duplicate events");
Check(deferred.Reserve("card_added") == null && deferred.Truncated,
    "unpublished slots share the action event memory bound");
Check(!deferred.Events.Any(e => (string)e["type"]! == "card_added"),
    "never-visible reserved identities are omitted");

bool Sample(string? reason, string state, bool motion, int ms) => settling.Sample(reason, state, motion, TimeSpan.FromMilliseconds(ms));
Check(!Sample("player_ready", "discard:0", true, 0) && !Sample("player_ready", "discard:0", true, 1000),
    "quiet JSON does not finish pending native card motion");
Check(!Sample("player_ready", "discard:1", false, 1100) && !Sample("player_ready", "discard:1", false, 1300)
    && Sample("player_ready", "discard:1", false, 1350), "quiet interval begins after card motion ends");
Check(!Sample("player_ready", "discard:2", false, 1400) && !Sample("player_ready", "discard:2", false, 1600)
    && Sample("player_ready", "discard:2", false, 1650), "visible state change restarts settling");
Check(!Sample(null, "discard:2", false, 1700) && !Sample("player_ready", "discard:2", false, 2000),
    "loss of interaction boundary resets settling");
Check(!Sample("choice_required", "choice", true, 2100) && Sample("choice_required", "choice", true, 2350),
    "choice returns without waiting for suspended parent card motion");
Check(!Sample("combat_won", "won", true, 2400) && !Sample("combat_won", "won", true, 2650)
    && !Sample("combat_won", "won", false, 2700) && Sample("combat_won", "won", false, 2950),
    "victory waits for postcombat card acquisition motion");
Check(!Sample("action_completed", "reward", true, 2700) && !Sample("action_completed", "reward", true, 3700),
    "noncombat potion completion waits for pending card motion");

Check(RewardBoundary.Decide(false, true, true, false) == "manual_input_required", "unsupported selection is manual input");
Check(RewardBoundary.Decide(false, true, false, false) == "manual_input_required", "unknown reward overlay does not time out");
Check(RewardBoundary.Decide(false, true, false, true) == "manual_input_required", "unsupported parent room does not authorize actions");
Check(RewardBoundary.Decide(true, true, false, false) == null, "transition is not a manual input screen");
Check(RewardBoundary.Decide(false, false, true, false) == "choice_required", "supported reward selection remains interactive");
Check(RewardBoundary.Decide(false, false, false, true) == "action_completed", "supported reward or map is a completion boundary");
Check(RewardBoundary.Decide(false, false, false, false) == null, "unready reward UI keeps settling");
Check(RewardBoundary.Decide(false, true, false, true, runLost: true) == "run_lost", "event death takes precedence over manual overlays");
Check(RewardBoundary.Decide(true, false, false, true, runLost: true) == null, "event death waits for room transition");

var settings = new TestScenarioSettings();
using (var config = System.Text.Json.JsonDocument.Parse("{\"play\":\"basic\",\"potion\":\"skill\"}"))
    settings.Configure(config.RootElement);
Check(settings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == "basic" && settings.Get("STS2_AGENT_TEST_REST_SCENARIO") == null,
    "per-run config replaces all scenario defaults");
try {
    using var invalid = System.Text.Json.JsonDocument.Parse("{\"rest\":\"bogus\"}");
    settings.Configure(invalid.RootElement);
    throw new Exception("Invalid configuration accepted");
} catch (ArgumentException) { }
Check(settings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == "basic", "invalid config is atomic");
using (var empty = System.Text.Json.JsonDocument.Parse("{}")) settings.Configure(empty.RootElement);
Check(settings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == null, "new config drops previous run scenario");
