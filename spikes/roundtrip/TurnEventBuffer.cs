namespace Sts2Agent;

internal sealed class TurnEventBuffer(int limit = 512)
{
    public List<Dictionary<string, object?>> Events { get; } = [];
    public bool Truncated { get; private set; }

    public Dictionary<string, object?>? Add(string type, Dictionary<string, object?> fields)
    {
        if (Events.Count >= limit)
        {
            Truncated = true;
            return null;
        }
        var entry = new Dictionary<string, object?>(fields)
        {
            ["sequence"] = Events.Count + 1, ["type"] = type
        };
        Events.Add(entry);
        return entry;
    }
}
