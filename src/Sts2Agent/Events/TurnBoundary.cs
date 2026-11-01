namespace Sts2Agent;

internal static class TurnBoundary
{
    public static string? Decide(bool sameCombat, bool ended, bool choiceReady, bool playerReady, bool won)
    {
        if (ended) return won ? "combat_won" : "combat_lost";
        if (!sameCombat) return "interrupted";
        if (choiceReady) return "choice_required";
        return playerReady ? "player_ready" : null;
    }
}
