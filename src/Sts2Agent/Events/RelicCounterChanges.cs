namespace Sts2Agent;

internal sealed class RelicCounterChanges<TKey>(TurnEventBuffer buffer) where TKey : notnull
{
    private readonly Dictionary<TKey, int?> known = [];

    public void Sample(TKey key, string name, int? counter)
    {
        if (known.TryGetValue(key, out int? before) && before != counter)
            buffer.Add("relic_counter_changed", new()
            {
                ["relic"] = new { name }, ["before"] = before, ["after"] = counter
            });
        known[key] = counter;
    }

    public void ForgetExcept(IEnumerable<TKey> visible)
    {
        var keep = visible.ToHashSet();
        foreach (var key in known.Keys.Where(key => !keep.Contains(key)).ToArray()) known.Remove(key);
    }

    public void Clear() => known.Clear();
}
