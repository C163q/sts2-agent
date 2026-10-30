namespace Sts2Agent;

internal static class RewardBoundary
{
    public static string? Decide(bool transitioning, bool manualInput, bool choiceReady, bool ready)
    {
        if (transitioning) return null;
        if (manualInput) return "manual_input_required";
        if (choiceReady) return "choice_required";
        return ready ? "action_completed" : null;
    }
}
