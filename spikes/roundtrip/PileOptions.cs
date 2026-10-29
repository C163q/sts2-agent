using System.Text.Json;
using MegaCrit.Sts2.Core.Entities.Cards;

namespace Sts2Agent;

internal sealed record PileOptions(string Pile, string DetailLevel)
{
    public PileType Type => Pile switch { "draw" => PileType.Draw, "discard" => PileType.Discard, _ => PileType.Exhaust };

    public static PileOptions Parse(JsonElement? arguments)
    {
        string? pile = null;
        string level = "summary";
        HashSet<string> seen = [];
        if (arguments is not { ValueKind: JsonValueKind.Object } value)
            throw new JsonException("Pile arguments are required.");
        foreach (var field in value.EnumerateObject())
        {
            if (!seen.Add(field.Name)) throw new JsonException("Duplicate pile option.");
            switch (field.Name)
            {
                case "pile": pile = field.Value.GetString(); break;
                case "detail_level": level = field.Value.GetString() ?? ""; break;
                default: throw new JsonException("Unknown pile option.");
            }
        }
        if (pile is not ("draw" or "discard" or "exhaust") || level is not ("summary" or "full"))
            throw new JsonException("Invalid pile option.");
        return new PileOptions(pile, level);
    }
}
