using Sts2Agent;

internal static class PurchaseFeedbackChecks
{
    public static void Run(Action<bool, string> check)
    {
        var waiting = new TaskCompletionSource();
        check(PurchaseOutcome.AtBoundary("success", waiting.Task, true) == "success"
            && PurchaseOutcome.AtBoundary("failure_space", Task.CompletedTask, false) == "failure_space",
            "native purchase events retain their known outcome");
        check(PurchaseOutcome.AtBoundary(null, waiting.Task, true) == "pending",
            "unfinished purchase reports pending at a supported input boundary");
        check(PurchaseOutcome.AtBoundary(null, waiting.Task, false) == null,
            "unfinished purchase without input remains unknown");
        check(PurchaseOutcome.AtBoundary(null, Task.CompletedTask, false) == "canceled",
            "native completed purchase without a completion event is canceled");
        check(PurchaseOutcome.AtBoundary(null, Task.FromCanceled(new CancellationToken(true)), true) == null
            && PurchaseOutcome.AtBoundary(null, Task.FromException(new InvalidOperationException()), true) == null,
            "faulted and canceled native tasks do not invent purchase outcomes");

        var settling = new ActionSettling();
        check(!settling.Sample("choice_required", "gold:2099", true, TimeSpan.Zero, choiceMotionPending: true)
            && !settling.Sample("choice_required", "gold:2099", true, TimeSpan.FromMilliseconds(600), choiceMotionPending: true),
            "choice cannot finish in the quiet lead-in of a gold animation");
        check(!settling.Sample("choice_required", "gold:1999", true, TimeSpan.FromMilliseconds(1000))
            && settling.Sample("choice_required", "gold:1999", true, TimeSpan.FromMilliseconds(1250)),
            "choice returns after gold settles without waiting for its suspended parent task");
        var interrupted = new ActionSettling();
        check(!interrupted.Sample("interrupted", "ended", true, TimeSpan.Zero, choiceMotionPending: true)
            && interrupted.Sample("interrupted", "ended", true, TimeSpan.FromMilliseconds(250), choiceMotionPending: true),
            "interrupted boundaries do not wait for abandoned gold animations");
    }
}
