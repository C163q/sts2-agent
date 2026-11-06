namespace Sts2Agent;

internal sealed record DivinationPatch(int X, int Y, string Appearance, bool Complete);

internal static class DivinationBoard
{
    internal sealed record Fragment(int x, int y, string appearance);
    internal sealed record Result(string[] cell_rows, Fragment[] visible_fragments);

    public static Result Build(bool[,] hidden, IEnumerable<DivinationPatch> patches)
    {
        if (hidden.GetLength(0) != 11 || hidden.GetLength(1) != 11)
            throw new ArgumentException("Unexpected divination grid.");
        var visible = patches.Where(p => p.X is >= 0 and < 11 && p.Y is >= 0 and < 11
                && Math.Min(p.X, 10 - p.X) + Math.Min(p.Y, 10 - p.Y) >= 3 && !hidden[p.X, p.Y])
            .GroupBy(p => (p.X, p.Y)).ToDictionary(group => group.Key, group =>
            {
                var values = group.Distinct().ToArray();
                return values.Length == 1 ? values[0] : new DivinationPatch(group.Key.X, group.Key.Y, "unrecognized", false);
            });
        var rows = Enumerable.Range(0, 11).Select(y => new string(Enumerable.Range(0, 11).Select(x =>
            hidden[x, y] ? '#' : visible.TryGetValue((x, y), out var patch) ? patch.Complete ? 'S' : 's' : '.').ToArray())).ToArray();
        var fragments = visible.Values.OrderBy(p => p.Y).ThenBy(p => p.X)
            .Select(p => new Fragment(p.X, p.Y, p.Appearance)).ToArray();
        return new(rows, fragments);
    }
}
