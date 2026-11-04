namespace Sts2Agent;

internal sealed class CardPlayProgress
{
    private bool submitted, executing, finished, started, witnessed, uncertain;
    public bool Canceled { get; private set; }
    public bool Pending => submitted && !finished && !uncertain;
    public string Status => !submitted ? "not_submitted" : uncertain ? "unknown"
        : !finished ? executing ? "resolving" : "queued"
        : witnessed ? "played" : started ? "unknown" : "not_played";

    public void Submit() => submitted = true;
    public void Begin() => executing = true;
    public void Play(bool visible) { started = true; witnessed |= visible; }
    public void Cancel() { Canceled = true; finished = true; }
    public void Finish(bool failed) { finished = true; uncertain |= failed; }
    public void Abandon() { if (Pending) uncertain = true; }
}
