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
