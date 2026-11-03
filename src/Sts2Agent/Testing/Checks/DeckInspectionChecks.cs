using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;

namespace Sts2Agent;

internal static class DeckInspectionChecks
{
    private static readonly List<object> Runs = [];

    public static async Task<object> CardViews(GameAdapter adapter, string path)
    {
        List<object> results = [];
        var game = NGame.Instance!;
        var player = MegaCrit.Sts2.Core.Context.LocalContext.GetMe(CombatManager.Instance.DebugOnlyGetState())!;
        async Task<JsonElement> Call(string operation)
        {
            using var response = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), operation, null)));
            return response.RootElement.Clone();
        }
        foreach (var pile in new[] { PileType.Draw, PileType.Discard, PileType.Exhaust })
        {
            NCardPileScreen.ShowScreen(pile.GetPile(player), []);
            var deadline = DateTime.UtcNow.AddSeconds(3);
            while (CardView.Current is not { } current || !CardView.CanClose(current))
            {
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Test card view controls did not become ready.");
                await game.ToSignal(game.GetTree(), SceneTree.SignalName.ProcessFrame);
            }
            var observation = await Call("get_state");
            bool identified = observation.GetProperty("state").GetProperty("screen").GetProperty("view").GetString()
                == pile.ToString().ToLowerInvariant() + "_pile";
            var closed = await Call("close_card_view");
            results.Add(new { name = "close_" + pile.ToString().ToLowerInvariant(), passed = identified
                && closed.GetProperty("ok").GetBoolean() && NCapstoneContainer.Instance?.CurrentCapstoneScreen == null });
        }
        var map = NRun.Instance!.GlobalUi.MapScreen;
        try
        {
            map.Open(isOpenedFromTopBar: true);
            await game.ToSignal(game.GetTree(), SceneTree.SignalName.ProcessFrame);
            var before = await Call("get_state");
            results.Add(new { name = "map_is_covered_and_identified", passed =
                before.GetProperty("state").GetProperty("screen").GetProperty("status").GetString() == "covered"
                && before.GetProperty("state").GetProperty("screen").GetProperty("view").GetString() == "map"
                && before.GetProperty("state").GetProperty("player").ValueKind == JsonValueKind.Null });
            var refused = await Call("close_card_view");
            results.Add(new { name = "map_alone_is_not_closed", passed = !refused.GetProperty("ok").GetBoolean() && map.IsOpen });
            var deck = await Call("inspect_deck");
            results.Add(new { name = "deck_opens_above_map", passed = deck.GetProperty("ok").GetBoolean()
                && NCapstoneContainer.Instance?.CurrentCapstoneScreen is NDeckViewScreen && map.IsOpen });
            var closed = await Call("close_card_view");
            results.Add(new { name = "card_close_preserves_map", passed = closed.GetProperty("ok").GetBoolean()
                && NCapstoneContainer.Instance?.CurrentCapstoneScreen == null && map.IsOpen && VisibleUi.Shown(map)
                && closed.GetProperty("state").GetProperty("screen").GetProperty("view").GetString() == "map" });
        }
        finally
        {
            NCapstoneContainer.Instance?.Close();
            map.Close(animateOut: false);
        }
        var report = new { results };
        File.WriteAllText(Path.Combine(Path.GetDirectoryName(path)!, "card-view-checks.json"),
            JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Card view checks failed; see the local report.");
        return report;
    }

    public static async Task<object> Lifecycle(GameAdapter adapter, string path)
    {
        List<object> results = [];
        var game = NGame.Instance!;
        var tree = game.GetTree();
        foreach (string mode in new[] { "closed", "covered", "replaced" })
        {
            bool interrupted = false;
            Exception? callbackError = null;
            object? replacement = null;
            void Interrupt()
            {
                if (NCapstoneContainer.Instance?.CurrentCapstoneScreen is not NDeckViewScreen screen)
                    return;
                tree.ProcessFrame -= Interrupt;
                try
                {
                    interrupted = true;
                    if (mode == "closed") DeckView.Close(screen);
                    else if (mode == "covered") game.GetInspectCardScreen().Open(DeckView.Cards(screen).ToList(), 0);
                    else replacement = NCardPileScreen.ShowScreen(PileType.Discard.GetPile(
                        MegaCrit.Sts2.Core.Context.LocalContext.GetMe(CombatManager.Instance.DebugOnlyGetState())!), []);
                }
                catch (Exception error) { callbackError = error; }
            }
            tree.ProcessFrame += Interrupt;
            try
            {
                using var response = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), "inspect_deck", null)));
                bool rejected = !response.RootElement.GetProperty("ok").GetBoolean()
                    && response.RootElement.GetProperty("error").GetProperty("code").GetString() == "illegal_action";
                bool preserved = mode switch
                {
                    "closed" => NCapstoneContainer.Instance?.CurrentCapstoneScreen == null,
                    "covered" => VisibleUi.Shown(game.InspectCardScreen)
                        && NCapstoneContainer.Instance?.CurrentCapstoneScreen is NDeckViewScreen,
                    _ => ReferenceEquals(NCapstoneContainer.Instance?.CurrentCapstoneScreen, replacement)
                };
                results.Add(new { name = mode + "_during_wait_is_rejected_without_changing_new_screen",
                    passed = interrupted && callbackError == null && rejected && preserved });
                if (mode != "closed")
                {
                    using var closed = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), "close_deck", null)));
                    bool untouched = mode == "covered" ? VisibleUi.Shown(game.InspectCardScreen)
                        && NCapstoneContainer.Instance?.CurrentCapstoneScreen is NDeckViewScreen
                        : ReferenceEquals(NCapstoneContainer.Instance?.CurrentCapstoneScreen, replacement);
                    results.Add(new { name = mode + "_blocks_close_deck", passed = !closed.RootElement.GetProperty("ok").GetBoolean()
                        && closed.RootElement.GetProperty("error").GetProperty("code").GetString() == "illegal_action" && untouched });
                }
            }
            finally
            {
                tree.ProcessFrame -= Interrupt;
                if (VisibleUi.Shown(game.InspectCardScreen)) game.GetInspectCardScreen().Close();
                NCapstoneContainer.Instance?.Close();
            }
            var deadline = DateTime.UtcNow.AddSeconds(3);
            while (VisibleUi.Shown(game.InspectCardScreen) || NCapstoneContainer.Instance?.CurrentCapstoneScreen != null)
            {
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Test screen cleanup did not settle.");
                await game.ToSignal(tree, SceneTree.SignalName.ProcessFrame);
            }
        }
        var report = new { results };
        File.WriteAllText(Path.Combine(Path.GetDirectoryName(path)!, "deck-lifecycle-checks.json"),
            JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Deck lifecycle checks failed; see the local report.");
        return report;
    }

    public static void Run(string path, NDeckViewScreen screen, Player player, DeckInspection reader, object inspection)
    {
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        var original = DeckView.Cards(screen);
        string saved = JsonSerializer.Serialize(original.Select(card => card.ToSerializable()));
        var prefixes = original.SelectMany(card => card.DynamicVars.Values.OfType<EnergyVar>()).Select(value => (value, value.ColorPrefix)).ToArray();
        string language = LocManager.Instance.Language;
        var keyword = new LocString("card_keywords", "EXHAUST.title");
        string localized = keyword.GetFormattedText();
        var data = JsonSerializer.SerializeToElement(inspection);
        var cards = data.GetProperty("deck").EnumerateArray().ToArray();
        Check("native_full_deck_count", cards.Length == PileType.Deck.GetPile(player).Cards.Count);
        Check("includes_cards_outside_viewport", cards.Length > DeckView.Grid(screen).CurrentlyDisplayedCardHolders
            .Count(holder => VisibleUi.OnScreen(holder.CardNode)));
        Check("deck_is_open_and_combat_paused", ReferenceEquals(DeckView.Current, screen) && CombatManager.Instance.IsPaused);
        Check("unique_deck_ids", cards.Select(card => card.GetProperty("id").GetString()).Distinct().Count() == cards.Length);
        string text = string.Concat(cards.Select(card => card.GetProperty("name").GetString()
            + (card.TryGetProperty("description", out var description) ? description.GetString() : "")
            + (card.TryGetProperty("hover_tips", out var tips) ? string.Concat(tips.EnumerateArray()
                .Select(tip => tip.GetProperty("title").GetString() + tip.GetProperty("description").GetString())) : "")));
        Check("english_text", !text.Any(character => character >= '\u4e00' && character <= '\u9fff'));
        bool renderedMatch = true;
        foreach (var holder in DeckView.Grid(screen).CurrentlyDisplayedCardHolders.Where(holder => VisibleUi.OnScreen(holder.CardNode)))
        {
            int index = Array.FindIndex(original, card => ReferenceEquals(card, holder.CardModel));
            if (index < 0) { renderedMatch = false; break; }
            var rendered = holder.CardNode!;
            string? name = EnglishCardText.Read(() => EnglishCardText.Plain(rendered.Model!.Title));
            renderedMatch &= cards[index].GetProperty("name").GetString() == name;
            if (VisibleUi.Text(rendered, "%EnergyLabel") is { } cost)
                renderedMatch &= cards[index].GetProperty("energy_cost").GetString() == cost;
        }
        Check("rendered_cards_match_projected_names_and_costs", renderedMatch);
        Check("complete_descriptions_and_tips", cards.All(card =>
            card.GetProperty("description").ValueKind == JsonValueKind.String && card.GetProperty("hover_tips").ValueKind == JsonValueKind.Array));
        var repeated = reader.Read(screen, player, data.GetProperty("snapshot_id").GetString()!);
        Check("repeatable", JsonSerializer.Serialize(inspection) == JsonSerializer.Serialize(repeated));
        Check("owned_cards_unchanged", saved == JsonSerializer.Serialize(original.Select(card => card.ToSerializable())));
        Check("owned_energy_prefixes_unchanged", prefixes.All(entry => entry.value.ColorPrefix == entry.ColorPrefix));
        Check("locale_unchanged", LocManager.Instance.Language == language && keyword.GetFormattedText() == localized);
        Runs.Add(new { view_upgrades = DeckView.Grid(screen).IsShowingUpgrades, results });
        File.WriteAllText(path, JsonSerializer.Serialize(new { language, runs = Runs }, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Deck inspection checks failed; see the local report.");
    }
}
