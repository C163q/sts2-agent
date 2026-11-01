namespace Sts2Agent;

internal sealed class VisibleResourceChange(string type, TurnEventBuffer buffer, Func<object> target)
{
    private int? known;
    private int? before;
    private int expected;
    private TurnEventBuffer.Reservation? pending;
    public bool Pending => pending != null;
    public bool HasBaseline => known.HasValue;
    public bool PendingReveal { get; private set; }

    public void SampleChange(int? displayed)
    {
        if (known.HasValue && displayed is >= 0 && known != displayed) Changed(displayed.Value, displayed);
        else Sample(displayed);
    }

    public void Sample(int? displayed)
    {
        if (displayed is not >= 0)
        {
            known = null;
            pending = null;
            PendingReveal = false;
            return;
        }
        if (pending != null)
        {
            if (displayed != expected) return;
            if (before != displayed)
                pending.Publish(new() { ["target"] = target(), ["before"] = before, ["after"] = displayed.Value });
            pending = null;
            PendingReveal = false;
        }
        known = displayed;
    }

    public void Changed(int after, int? displayed)
    {
        if (after < 0 || displayed is not >= 0) { Sample(null); return; }
        // Preserve an already rendered earlier change before accepting the next native notification.
        if (pending != null) Sample(displayed);
        if (pending == null)
        {
            before = known ?? displayed.Value;
            pending = buffer.Reserve(type);
        }
        expected = after;
        Sample(displayed);
    }

    public void Revealed(int after, int? displayed = null)
    {
        if (after < 0) { Sample(null); return; }
        if (pending != null && displayed.HasValue) Sample(displayed);
        if (pending == null)
        {
            before = known;
            pending = buffer.Reserve(type);
        }
        expected = after;
        PendingReveal = pending != null;
        if (displayed.HasValue) Sample(displayed);
    }
}
