namespace Sts2Agent;

internal sealed class CardIdentityMap<T> where T : class
{
    private readonly Dictionary<T, int> ids = new(ReferenceEqualityComparer.Instance);

    public int Get(T instance)
    {
        if (!ids.TryGetValue(instance, out int id))
        {
            id = ids.Count;
            ids.Add(instance, id);
        }
        return id;
    }

    public void Clear() => ids.Clear();
}
