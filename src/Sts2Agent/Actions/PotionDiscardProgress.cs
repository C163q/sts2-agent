namespace Sts2Agent;

internal sealed class PotionDiscardProgress
{
    private bool submitted, observed, canceled, finished, uncertain;
    public string Status => observed ? "discarded" : uncertain || !submitted ? "unknown"
        : canceled ? "not_discarded" : finished ? "unknown" : "queued";

    public void Submit() => submitted = true;
    public void ObserveDiscard() => observed = true;
    public void Cancel() { canceled = true; finished = true; }
    public void Finish(bool failed) { finished = true; uncertain |= failed; }
    public void Abandon() => uncertain = true;
}
