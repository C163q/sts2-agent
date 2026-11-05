using System.Text.Json;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal static class SelectionInputJournal
{
    public static void Record(CardSelection selection, CardModel? clicked, JsonElement snapshot,
        Func<CardModel, int> cardId, Action input)
    {
        if (ActionEventScope.Current is not { } scope || selection.Status != "visible"
            || selection.Kind is "bundle" or "view_cards" || !selection.Supported)
        { input(); return; }

        var before = selection.Selected;
        var identities = before.Concat(clicked == null ? [] : new[] { clicked }).Distinct()
            .ToDictionary(card => card, card => (id: cardId(card), name: Name(snapshot, cardId(card))));
        var completion = selection.Key.GetType().GetProperty("Task")?.GetValue(selection.Key) as Task;
        int candidateIndex = clicked == null ? -1 : Array.IndexOf(selection.Cards, clicked);
        // A native completion may run the parent effect synchronously; keep input changes before it.
        var removals = before.Select(card => (card, slot: scope.Buffer.Reserve("card_deselected"))).ToArray();
        var addition = clicked != null && !before.Contains(clicked) ? scope.Buffer.Reserve("card_selected") : null;
        input();

        CardModel[] after;
        if (clicked != null && completion?.IsCompletedSuccessfully == true)
        {
            // Inspect only the accepted result of this original selection, never a later page.
            object? accepted = completion.GetType().GetProperty("Result")?.GetValue(completion);
            if (accepted is IEnumerable<CardModel> cards) after = cards.ToArray();
            else if (selection.Kind == "reward" && accepted is int index && index == candidateIndex)
                after = [clicked];
            else return;
        }
        else if (SelectionActions.Same(selection) && selection.Status == "visible") after = selection.Selected;
        else return;

        foreach (var (card, slot) in removals)
            if (!after.Contains(card)) Publish(slot, identities[card]);
        if (clicked != null && after.Contains(clicked)) Publish(addition, identities[clicked]);
    }

    private static void Publish(TurnEventBuffer.Reservation? slot, (int id, string? name) card) =>
        slot?.Publish(new() { ["card"] = new { card.id, card.name } });

    private static string? Name(JsonElement snapshot, int id)
    {
        if (!snapshot.TryGetProperty("selection", out var selection) || selection.ValueKind != JsonValueKind.Object)
            return null;
        bool Match(JsonElement card) => card.ValueKind == JsonValueKind.Object
            && card.TryGetProperty("id", out var value) && value.GetInt32() == id;
        string? Read(JsonElement card) => card.TryGetProperty("name", out var name) && name.ValueKind == JsonValueKind.String
            ? name.GetString() : null;
        if (selection.TryGetProperty("cards", out var candidates) && candidates.ValueKind == JsonValueKind.Array)
            foreach (var card in candidates.EnumerateArray()) if (Match(card)) return Read(card);
        if (selection.TryGetProperty("upgrade_preview", out var single) && single.ValueKind == JsonValueKind.Object
            && single.TryGetProperty("before", out var original) && Match(original)) return Read(original);
        foreach (string key in new[] { "upgrade_previews", "enchant_previews", "transform_previews" })
            if (selection.TryGetProperty(key, out var pairs) && pairs.ValueKind == JsonValueKind.Array)
                foreach (var pair in pairs.EnumerateArray())
                    if (pair.TryGetProperty("before", out var card) && Match(card)) return Read(card);
        return null;
    }
}
