namespace Sts2Agent;

internal sealed class TurnEventBuffer(int limit = 512)
{
    private readonly List<Reservation> entries = [];
    public List<Dictionary<string, object?>> Events
    {
        get
        {
            var published = entries.Where(entry => entry.Fields != null).Select(entry => entry.Fields!).ToList();
            for (int i = 0; i < published.Count; i++) published[i]["sequence"] = i + 1;
            return published;
        }
    }
    public bool Truncated { get; private set; }

    public Dictionary<string, object?>? Add(string type, Dictionary<string, object?> fields)
    {
        var slot = Reserve(type);
        return slot?.Publish(fields);
    }

    public Reservation? Reserve(string type)
    {
        if (entries.Count >= limit)
        {
            Truncated = true;
            return null;
        }
        var entry = new Reservation(type);
        entries.Add(entry);
        return entry;
    }

    internal sealed class Reservation(string type)
    {
        public Dictionary<string, object?>? Fields { get; private set; }
        public Dictionary<string, object?> Publish(Dictionary<string, object?> fields)
        {
            // Native notifications may precede their UI animation; publication must not reorder them.
            return Fields ??= new(fields) { ["type"] = type };
        }
    }
}
