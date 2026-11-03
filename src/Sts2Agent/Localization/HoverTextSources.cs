namespace Sts2Agent;

internal sealed class HoverTextSources
{
    internal sealed record Tip(string? title, string description, string[] sources);
    private readonly Dictionary<(string? title, string description), List<string>> entries = [];

    public void Add(string? title, string description, IEnumerable<string> sources)
    {
        if (!entries.TryGetValue((title, description), out var found)) entries[(title, description)] = found = [];
        foreach (string source in sources)
            if (!found.Contains(source)) found.Add(source);
    }

    public Tip[] Items => entries.Select(pair => new Tip(pair.Key.title, pair.Key.description, pair.Value.ToArray())).ToArray();
}
