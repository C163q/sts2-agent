namespace Sts2Agent;

internal static class PresentationState
{
    public static string Status(bool exposed, bool complete) => !exposed ? "covered" : complete ? "visible" : "not_ready";
}
