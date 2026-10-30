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

var settling = new ActionSettling();
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
Check(!Sample("combat_won", "won", true, 2400) && Sample("combat_won", "won", true, 2650),
    "combat outcome does not wait for gameplay card motion");
Check(!Sample("action_completed", "reward", true, 2700) && !Sample("action_completed", "reward", true, 3700),
    "noncombat potion completion waits for pending card motion");
