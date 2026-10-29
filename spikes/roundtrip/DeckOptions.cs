using System.Text.Json;

namespace Sts2Agent;

internal sealed record DeckOptions(string DetailLevel, bool? ViewUpgrades, string? SortBy, bool? Descending)
{
    public static DeckOptions Parse(JsonElement? arguments)
    {
        string level = "summary";
        string? sort = null;
        bool? upgrades = null, descending = null;
        if (arguments is { } value)
        {
            if (value.ValueKind != JsonValueKind.Object)
                throw new JsonException("Arguments must be an object.");
            HashSet<string> seen = [];
            foreach (var field in value.EnumerateObject())
            {
                if (!seen.Add(field.Name)) throw new JsonException("Duplicate deck option.");
                switch (field.Name)
                {
                    case "detail_level": level = field.Value.GetString() ?? ""; break;
                    case "sort_by": sort = field.Value.GetString() ?? ""; break;
                    case "view_upgrades": upgrades = field.Value.GetBoolean(); break;
                    case "descending": descending = field.Value.GetBoolean(); break;
                    default: throw new JsonException("Unknown deck option.");
                }
            }
        }
        if (level is not ("summary" or "full") || (sort != null && sort is not ("obtained" or "type" or "cost" or "name"))
            || (descending.HasValue && sort == null))
            throw new JsonException("Invalid deck option.");
        return new DeckOptions(level, upgrades, sort, descending);
    }
}
