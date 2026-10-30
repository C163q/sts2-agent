namespace Sts2Agent;

internal sealed class ActionSettling
{
    private string? previousReason;
    private string? previousState;
    private TimeSpan stableSince;

    public bool Sample(string? reason, string state, bool cardMotionPending, TimeSpan now)
    {
        bool waitsForMotion = reason is "player_ready" or "action_completed" or "action_canceled";
        if (reason == null || waitsForMotion && cardMotionPending)
        {
            previousReason = previousState = null;
            return false;
        }
        if (reason != previousReason || state != previousState)
        {
            previousReason = reason;
            previousState = state;
            stableSince = now;
            return false;
        }
        return now - stableSince >= TimeSpan.FromMilliseconds(250);
    }
}
