namespace Sts2Agent;

internal static class DisplaySupportChecks
{
    private class Base { private readonly string? nullable = null; private readonly int value = 7; public int Value => value; public string? Nullable => nullable; }
    private sealed class Derived : Base { }
    public static void Run(Action<bool, string> check)
    {
        var instance = new Derived();
        check((int)PrivateFields.Read(instance, "value")! == 7, "required private fields include inherited bindings");
        check(PrivateFields.Read(instance, "nullable") == null, "required binding preserves legitimate null value");
        check(PrivateFields.Optional(instance, "absent") == null, "optional polymorphic field may be absent");
        try { PrivateFields.Read(instance, "absent"); throw new Exception("missing binding accepted"); }
        catch (MissingFieldException) { check(true, "required missing private binding fails explicitly"); }
        var tips = new HoverTextSources();
        tips.Add("Block", "A", ["player.powers.0", "player.powers.0"]);
        tips.Add("Block", "A", ["enemies.1.powers.0", "player.powers.0"]);
        tips.Add("Block", "B", ["enemies.0.powers.0"]);
        var result = tips.Items;
        check(result.Length == 2 && result[0].sources.SequenceEqual(new[] { "player.powers.0", "enemies.1.powers.0" })
            && result[1].description == "B", "shared hover help preserves text variants and canonical source order");
    }
}
