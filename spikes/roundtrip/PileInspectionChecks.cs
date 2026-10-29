using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal static class PileInspectionChecks
{
    public static async Task<object> Run(GameAdapter adapter, string path)
    {
        var game = NGame.Instance!;
        var tree = game.GetTree();
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var player = LocalContext.GetMe(combat)!;
        var ui = NCombatRoom.Instance!.Ui;
        var draw = PileType.Draw.GetPile(player);
        var discard = PileType.Discard.GetPile(player);
        var exhaust = PileType.Exhaust.GetPile(player);
        var originalDraw = draw.Cards.ToArray();
        var originalDiscard = discard.Cards.ToArray();
        var originalExhaust = exhaust.Cards.ToArray();
        var exhaustVisible = ui.ExhaustPile.Visible;
        var exhaustEnabled = ui.ExhaustPile.IsEnabled;
        var exhaustPosition = ui.ExhaustPile.Position;
        List<CardModel> generated = [];
        List<object> results = [], calls = [];
        var buttons = new NCombatCardPile[] { ui.DrawPile, ui.DiscardPile, ui.ExhaustPile };
        var clicks = buttons.ToDictionary(button => button, _ => 0);
        var handlers = buttons.ToDictionary(button => button,
            button => Callable.From<NButton>(_ => clicks[button]++));
        foreach (var button in buttons) button.Connect(NClickableControl.SignalName.Released, handlers[button]);
        void Check(string name, bool passed) => results.Add(new { name, passed });
        string Token() => JsonSerializer.Deserialize<JsonElement>(adapter.Observe()).GetProperty("snapshot_id").GetString()!;
        async Task Wait(Func<bool> ready)
        {
            var deadline = DateTime.UtcNow.AddSeconds(4);
            while (!ready())
            {
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Pile test did not settle.");
                await game.ToSignal(tree, SceneTree.SignalName.ProcessFrame);
            }
        }
        async Task<JsonElement> Call(string operation, object? args = null)
        {
            using var response = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), operation,
                null, args == null ? null : JsonSerializer.SerializeToElement(args))));
            var result = response.RootElement.Clone();
            calls.Add(new { operation, arguments = args, response = result });
            return result;
        }
        async Task<JsonElement> Inspect(string pile, string level = "summary")
        {
            var response = await Call("inspect_pile", new { pile, detail_level = level });
            if (!response.GetProperty("ok").GetBoolean())
                throw new InvalidOperationException("Pile test inspection failed: " + response);
            return response.GetProperty("state");
        }
        async Task Close()
        {
            if (CardView.Current != null) await Call("close_card_view");
            await Wait(() => NCapstoneContainer.Instance?.CurrentCapstoneScreen == null
                && !VisibleUi.Shown(game.InspectCardScreen));
        }
        async Task Move(CardModel card, PileType target)
        {
            var old = card.Pile;
            await CardPileCmd.Add(card, target, skipVisuals: true);
            // No animation emits pile-completion notifications in this fixture.
            old?.InvokeCardRemoveFinished();
            old?.InvokeContentsChanged();
            target.GetPile(player).InvokeCardAddFinished();
        }
        void Capture(string name)
        {
            if (DisplayServer.GetName() != "headless")
                TestCapture.Save(Path.Combine(Path.GetDirectoryName(path)!, "piles-" + name + ".png"));
        }
        try
        {
            Check("fresh_empty_discard_and_hidden_exhaust", discard.IsEmpty && exhaust.IsEmpty && !VisibleUi.OnScreen(ui.ExhaustPile));
            string token = Token();
            foreach (var invalid in new object[] { new { }, new { pile = "deck" }, new { pile = "draw", sort_by = "cost" },
                new { pile = "draw", view_upgrades = true }, new { pile = "draw", detail_level = "brief" }, new { pile = 1 } })
            {
                var result = await Call("inspect_pile", invalid);
                Check("invalid_arguments_preserve_screen_and_token", !result.GetProperty("ok").GetBoolean()
                    && result.GetProperty("error").GetProperty("code").GetString() == "invalid_request" && Token() == token);
            }
            var hidden = await Inspect("exhaust", "full");
            Check("hidden_exhaust_not_clicked_or_read", hidden.GetProperty("status").GetString() == "unavailable"
                && hidden.GetProperty("cards").ValueKind == JsonValueKind.Null && clicks[ui.ExhaustPile] == 0 && Token() == token);

            await Call("inspect_deck");
            token = Token();
            int bubbles = VisibleUi.Descendants<NThoughtBubbleVfx>(NCombatRoom.Instance!).Count();
            var empty = await Inspect("discard", "full");
            Check("empty_discard_clicks_closes_deck_and_shows_bubble", empty.GetProperty("status").GetString() == "empty"
                && empty.GetProperty("cards").GetArrayLength() == 0 && clicks[ui.DiscardPile] == 1
                && NCapstoneContainer.Instance?.CurrentCapstoneScreen == null && Token() != token
                && VisibleUi.Descendants<NThoughtBubbleVfx>(NCombatRoom.Instance!).Count() > bubbles);
            Check("empty_discard_english_native_message", empty.GetProperty("message").GetString() ==
                EnglishCardText.Read(() => EnglishCardText.Plain(new LocString("combat_messages", "OPEN_EMPTY_DISCARD").GetFormattedText())));
            Capture("empty-discard");

            foreach (var card in originalDraw) await Move(card, PileType.Discard);
            await Wait(() => VisibleUi.Number(ui.DrawPile, "CountContainer/Count") == 0);
            bubbles = VisibleUi.Descendants<NThoughtBubbleVfx>(NCombatRoom.Instance!).Count();
            empty = await Inspect("draw");
            Check("empty_draw_clicks_and_shows_bubble", empty.GetProperty("status").GetString() == "empty"
                && empty.GetProperty("cards").GetArrayLength() == 0 && clicks[ui.DrawPile] == 1
                && VisibleUi.Descendants<NThoughtBubbleVfx>(NCombatRoom.Instance!).Count() > bubbles);
            Capture("empty-draw");
            foreach (var card in originalDraw) await Move(card, PileType.Draw);

            for (int index = 0; index < 20; index++)
            {
                CardModel card = index % 2 == 0 ? combat.CreateCard<DefendIronclad>(player) : combat.CreateCard<AscendersBane>(player);
                generated.Add(card);
                await Move(card, PileType.Draw);
            }
            var temporary = combat.CreateCard<StrikeIronclad>(player);
            temporary.EnergyCost.SetThisTurn(0);
            temporary.SetStarCostThisTurn(2);
            generated.Add(temporary);
            await Move(temporary, PileType.Draw);
            await PowerCmd.Apply<CorruptionPower>(new ThrowingPlayerChoiceContext(), player.Creature, 1, player.Creature, null);
            await Wait(() => VisibleUi.Number(ui.DrawPile, "CountContainer/Count") == draw.Cards.Count);
            string savedCards = JsonSerializer.Serialize(draw.Cards.Select(card => card.ToSerializable()));
            string savedRng = JsonSerializer.Serialize(player.RunState.Rng.ToSerializable());
            string language = LocManager.Instance.Language;
            var summary = await Inspect("draw");
            var screen = PileInspection.Current(new("draw", "summary"))!;
            var nativeCards = CardView.Cards(screen);
            var expected = draw.Cards.OrderBy(card => card.Rarity).ThenBy(card => card.Id.Entry, StringComparer.Ordinal).ToArray();
            Check("draw_uses_native_display_order_not_draw_order", nativeCards.Select(card => (card.Rarity, card.Id.Entry))
                .SequenceEqual(expected.Select(card => (card.Rarity, card.Id.Entry)))
                && !nativeCards.SequenceEqual(draw.Cards));
            Check("entire_pile_includes_offscreen_cards", summary.GetProperty("cards").GetArrayLength() == draw.Cards.Count
                && draw.Cards.Count > CardView.Grid(screen).CurrentlyDisplayedCardHolders.Count(holder => VisibleUi.OnScreen(holder.CardNode)));
            Check("summary_has_no_body_tips_or_page_controls", summary.GetProperty("cards").EnumerateArray().All(card =>
                !card.TryGetProperty("description", out _) && !card.TryGetProperty("hover_tips", out _))
                && !summary.TryGetProperty("sort", out _) && !summary.TryGetProperty("view_upgrades", out _));
            int clicked = clicks[ui.DrawPile];
            var full = await Inspect("draw", "full");
            Check("same_pile_reuses_page_without_toggle", ReferenceEquals(screen, CardView.Current) && clicks[ui.DrawPile] == clicked);
            Check("summary_full_ids_stable", summary.GetProperty("cards").EnumerateArray().Select(card => card.GetProperty("id").GetString())
                .SequenceEqual(full.GetProperty("cards").EnumerateArray().Select(card => card.GetProperty("id").GetString())));
            var cards = full.GetProperty("cards").EnumerateArray().ToArray();
            Check("combat_global_cost_hook_preserved_for_detached_clone", cards.Where((_, index) => nativeCards[index].Type == CardType.Skill)
                .All(card => card.GetProperty("energy_cost").GetString() == "0"));
            var temporaryResult = cards[Array.IndexOf(nativeCards, temporary)];
            Check("temporary_energy_and_star_costs_preserved", temporaryResult.GetProperty("energy_cost").GetString() == "0"
                && temporaryResult.GetProperty("star_cost").GetString() == "2"
                && temporary.EnergyCost.GetWithModifiers(CostModifiers.Local) == 0 && temporary.CurrentStarCost == 2);
            bool rendered = true;
            foreach (var holder in CardView.Grid(screen).CurrentlyDisplayedCardHolders.Where(holder => VisibleUi.OnScreen(holder.CardNode)))
            {
                int index = Array.IndexOf(nativeCards, holder.CardModel);
                var node = holder.CardNode!;
                rendered &= cards[index].GetProperty("name").GetString() == EnglishCardText.Read(() => EnglishCardText.Plain(node.Model!.Title));
                if (VisibleUi.Text(node, "%EnergyLabel") is { } cost)
                    rendered &= cards[index].GetProperty("energy_cost").GetString() == cost;
                rendered &= cards[index].GetProperty("description").GetString() == EnglishCardText.Read(() => HoverTipText.DescribeCard(node.Model!, PileType.Draw));
            }
            Check("full_matches_rendered_native_card_values", rendered);
            Check("english_body_and_native_bottom_message", !full.ToString().Any(character => character >= '\u4e00' && character <= '\u9fff')
                && full.GetProperty("message").GetString() == EnglishCardText.Read(() => EnglishCardText.Plain(new LocString("gameplay_ui", "DRAW_PILE_INFO").GetFormattedText())));
            Check("reading_preserves_owned_cards_rng_and_locale", savedCards == JsonSerializer.Serialize(draw.Cards.Select(card => card.ToSerializable()))
                && savedRng == JsonSerializer.Serialize(player.RunState.Rng.ToSerializable()) && language == LocManager.Instance.Language);
            Capture("draw");

            await Call("inspect_deck");
            Check("deck_replaces_pile", CardView.Current is NDeckViewScreen);
            await Inspect("draw");
            Check("pile_replaces_deck", PileInspection.Current(new("draw", "summary")) != null);
            var transferred = generated[0];
            string transferredId = cards[Array.IndexOf(nativeCards, transferred)].GetProperty("id").GetString()!;
            await Close();
            await Move(transferred, PileType.Discard);
            var discarded = await Inspect("discard", "full");
            Check("discard_context_and_identity_across_piles", discarded.GetProperty("cards").GetArrayLength() == discard.Cards.Count
                && discarded.GetProperty("cards")[0].GetProperty("id").GetString() == transferredId);
            Capture("discard");
            var exhausted = generated[1];
            await Move(exhausted, PileType.Exhaust);
            await Wait(() => VisibleUi.OnScreen(ui.ExhaustPile));
            var exhaustedResult = await Inspect("exhaust", "full");
            Check("nonempty_exhaust_click_replaces_discard", clicks[ui.ExhaustPile] == 1
                && PileInspection.Current(new("exhaust", "full")) != null && exhaustedResult.GetProperty("cards").GetArrayLength() == exhaust.Cards.Count);
            Capture("exhaust");
            await Close();

            NRun.Instance!.GlobalUi.MapScreen.Open(isOpenedFromTopBar: true);
            var blocked = await Call("inspect_pile", new { pile = "draw" });
            Check("map_blocks_pile_click_without_closing_map", !blocked.GetProperty("ok").GetBoolean()
                && NRun.Instance.GlobalUi.MapScreen.IsOpen && NCapstoneContainer.Instance?.CurrentCapstoneScreen == null);
            NRun.Instance.GlobalUi.MapScreen.Close(animateOut: false);

            foreach (string mode in new[] { "closed", "covered", "replaced" })
            {
                object? replacement = null;
                bool interrupted = false;
                void Interrupt()
                {
                    if (PileInspection.Current(new("draw", "summary")) is not { } current) return;
                    RenderingServer.FramePreDraw -= Interrupt;
                    interrupted = true;
                    if (mode == "closed") CardView.Close(current);
                    else if (mode == "covered") game.GetInspectCardScreen().Open(CardView.Cards(current).ToList(), 0);
                    else replacement = NCardPileScreen.ShowScreen(discard, []);
                }
                RenderingServer.FramePreDraw += Interrupt;
                try
                {
                    var response = await Call("inspect_pile", new { pile = "draw" });
                    bool preserved = mode == "closed" ? NCapstoneContainer.Instance?.CurrentCapstoneScreen == null
                        : mode == "covered" ? VisibleUi.Shown(game.InspectCardScreen)
                        : ReferenceEquals(NCapstoneContainer.Instance?.CurrentCapstoneScreen, replacement);
                    Check(mode + "_while_reading_is_rejected_without_cleanup", interrupted && !response.GetProperty("ok").GetBoolean()
                        && response.GetProperty("error").GetProperty("code").GetString() == "illegal_action" && preserved);
                }
                finally
                {
                    if (!interrupted) RenderingServer.FramePreDraw -= Interrupt;
                    if (VisibleUi.Shown(game.InspectCardScreen)) game.GetInspectCardScreen().Close();
                    NCapstoneContainer.Instance?.Close();
                    await Wait(() => !VisibleUi.Shown(game.InspectCardScreen));
                }
            }
        }
        finally
        {
            NCapstoneContainer.Instance?.Close();
            NRun.Instance!.GlobalUi.MapScreen.Close(animateOut: false);
            if (VisibleUi.Shown(game.InspectCardScreen)) game.GetInspectCardScreen().Close();
            foreach (var button in buttons) button.Disconnect(NClickableControl.SignalName.Released, handlers[button]);
            await PowerCmd.Remove<CorruptionPower>(player.Creature);
            foreach (var card in generated.Where(card => card.Pile?.IsCombatPile == true))
                await CardPileCmd.RemoveFromCombat(card, skipVisuals: true);
            foreach (var card in originalDraw) await Move(card, PileType.Draw);
            foreach (var card in originalDiscard) await Move(card, PileType.Discard);
            foreach (var card in originalExhaust) await Move(card, PileType.Exhaust);
            ui.ExhaustPile.Visible = exhaustVisible;
            ui.ExhaustPile.Position = exhaustPosition;
            if (exhaustEnabled) ui.ExhaustPile.Enable(); else ui.ExhaustPile.Disable();
            File.WriteAllText(path, JsonSerializer.Serialize(new { results, calls }, new JsonSerializerOptions { WriteIndented = true }));
        }
        Check("fixture_restores_original_piles", draw.Cards.SequenceEqual(originalDraw)
            && discard.Cards.SequenceEqual(originalDiscard) && exhaust.Cards.SequenceEqual(originalExhaust));
        File.WriteAllText(path, JsonSerializer.Serialize(new { results, calls }, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Pile checks failed; see the local report.");
        return new { results };
    }
}
