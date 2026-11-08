namespace Sts2Agent;

internal sealed class RoomResourceChange(string type, TurnEventBuffer buffer, Func<object> target)
{
    private int? known;
    private int before;
    private int expected;
    private TurnEventBuffer.Reservation? pending;
    public bool Pending => pending != null;

    public void Sample(int? displayed, bool crossingRoom = false)
    {
        if (displayed is not >= 0)
        {
            if (!crossingRoom) { known = null; pending = null; }
            return;
        }
        if (pending != null)
        {
            if (displayed != expected) return;
            if (before != displayed)
                pending.Publish(new() { ["target"] = target(), ["before"] = before, ["after"] = displayed.Value });
            pending = null;
        }
        known = displayed;
    }

    public void Changed(int oldValue, int newValue)
    {
        if (oldValue == newValue) return;
        if (newValue < 0 || (pending != null ? expected : known) != oldValue)
        {
            known = null; pending = null;
            return;
        }
        if (pending == null)
        {
            before = oldValue;
            pending = buffer.Reserve(type);
        }
        // Only the visible endpoints of one covered interval are public.
        expected = newValue;
    }
}
