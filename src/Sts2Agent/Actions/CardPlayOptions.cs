using System.Text.Json;

namespace Sts2Agent;

internal sealed record CardPlayInput(int CardId, uint? TargetId);

internal static class CardPlayOptions
{
    public static CardPlayInput[] Parse(JsonElement? arguments, bool multiple)
    {
        if (arguments is not { ValueKind: JsonValueKind.Object } root)
            throw new JsonException("Expected card play arguments.");
        if (!multiple) return [ParseCard(root, "")];
        if (root.EnumerateObject().Count() != 1 || !root.TryGetProperty("cards", out var cards)
            || cards.ValueKind != JsonValueKind.Array || cards.GetArrayLength() == 0)
            throw new JsonException("cards must be a nonempty array of card play objects.");
        var results = new List<CardPlayInput>();
        var ids = new HashSet<int>();
        foreach (var card in cards.EnumerateArray())
        {
            var item = ParseCard(card, $"cards[{results.Count}].");
            if (!ids.Add(item.CardId)) throw new JsonException($"cards[{results.Count}].card_id duplicates an earlier card ID.");
            results.Add(item);
        }
        return results.ToArray();
    }

    private static CardPlayInput ParseCard(JsonElement card, string prefix)
    {
        if (card.ValueKind != JsonValueKind.Object) throw new JsonException(prefix + "Expected a card play object.");
        var names = card.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Distinct().Count() != names.Length || names.Any(n => n is not ("card_id" or "target_id")))
            throw new JsonException(prefix + "Only card_id and optional target_id are accepted, without duplicate fields.");
        if (!card.TryGetProperty("card_id", out var id) || id.ValueKind != JsonValueKind.Number
            || !id.TryGetInt32(out int cardId) || cardId < 0)
            throw new JsonException(prefix + "card_id must be an integer hand ID from 0 to 2147483647.");
        uint? targetId = null;
        if (card.TryGetProperty("target_id", out var target))
        {
            if (target.ValueKind != JsonValueKind.Number || !target.TryGetUInt32(out uint value))
                throw new JsonException(prefix + "target_id must be an integer object ID from 0 to 4294967295; omit it when not required.");
            targetId = value;
        }
        return new(cardId, targetId);
    }
}
