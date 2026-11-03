namespace Sts2Agent;

internal sealed class RequestExecution
{
    private bool uiStarted;
    private bool submitted;
    private bool captured;

    public void UiInteractionStarted() => uiStarted = true;
    public void ActionSubmitted() => submitted = true;
    public T RecordCapture<T>(Func<T> read)
    {
        T result = read();
        captured = true;
        return result;
    }

    // False means no positive evidence was recorded, never proof that an action did not run.
    public object Facts => new { ui_interaction_started = uiStarted,
        action_submission_observed = submitted, state_captured = captured };
}
