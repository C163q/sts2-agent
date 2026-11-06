namespace Sts2Agent;

internal static class PurchaseOutcome
{
    public static string? AtBoundary(string? reported, Task submitted, bool awaitingInput)
    {
        if (reported != null) return reported;
        if (submitted.IsCompletedSuccessfully) return "canceled";
        return !submitted.IsCompleted && awaitingInput ? "pending" : null;
    }
}
