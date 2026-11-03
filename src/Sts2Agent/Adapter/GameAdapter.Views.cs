using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> InspectMap(Request request)
    {
        var run = RunManager.Instance.DebugOnlyGetState();
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (run == null || map == null || !CanInspectMap())
            return FileMailbox.Error(request.Id, "illegal_action", "Map viewing is unavailable in the current screen.");
        var graph = run.Map;
        int act = run.CurrentActIndex;
        bool cardOpen = MapView.CardPage != null;
        if (!map.IsOpen || cardOpen)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Map;
            if (!button.IsEnabled || !VisibleUi.OnScreen(button)
                || (!map.IsOpen && VisibleUi.Shown(map))
                || (CombatManager.Instance.IsInProgress && !CanInspectViews(allowPause: map.IsOpen || cardOpen)))
                return FileMailbox.Error(request.Id, "illegal_action", "The map button is unavailable.");
            capture.UiChanged();
            button.ForceClick();
        }
        bool closed = false;
        void Closed() => closed = true;
        bool SamePage() => !closed && ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(graph, run.Map) && act == run.CurrentActIndex && MapView.Current(map);
        map.Closed += Closed;
        try
        {
            await ObservationFrame();
            await WaitUntil(() => !SamePage() || MapView.Ready(map));
            if (!SamePage() || !MapView.Ready(map))
                return FileMailbox.Error(request.Id, "illegal_action", "The map changed while reading.");
            using var snapshot = JsonDocument.Parse(Observe());
            return InspectionSuccess(request.Id, snapshot.RootElement, MapInspection.Read(map, run,
                snapshot.RootElement.GetProperty("snapshot_id").GetString()!));
        }
        finally
        {
            if (GodotObject.IsInstanceValid(map)) map.Closed -= Closed;
        }
    }

    private async Task<string> InspectDeck(Request request, DeckOptions options)
    {
        var player = LocalPlayer;
        if (player == null || !CanInspectDeck())
            return FileMailbox.Error(request.Id, "illegal_action", "The local deck is unavailable in this screen.");
        var screen = DeckView.Current;
        if (screen == null)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Deck;
            if (!CanInspectDeck())
                return FileMailbox.Error(request.Id, "illegal_action", "The deck button is unavailable.");
            capture.UiChanged();
            button.ForceClick();
            screen = NCapstoneContainer.Instance?.CurrentCapstoneScreen as NDeckViewScreen;
            if (screen == null)
                return FileMailbox.Error(request.Id, "illegal_action", "The deck screen did not open.");
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(DeckView.Current, screen) || DeckView.Ready(screen));
        if (!ReferenceEquals(DeckView.Current, screen))
            return FileMailbox.Error(request.Id, "illegal_action", "The deck screen changed while opening.");
        if (options.ViewUpgrades.HasValue || options.SortBy != null)
            capture.UiChanged();
        try { DeckView.Apply(screen, options); }
        catch (InvalidOperationException)
        {
            return FileMailbox.Error(request.Id, "illegal_action", "The deck controls are unavailable.");
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(DeckView.Current, screen) || DeckView.Ready(screen));
        if (!ReferenceEquals(DeckView.Current, screen) || !ReferenceEquals(LocalPlayer, player))
            return FileMailbox.Error(request.Id, "illegal_action", "The deck screen changed while reading.");
        using var snapshot = JsonDocument.Parse(Observe());
        var inspection = deckInspection.Read(screen, player,
            snapshot.RootElement.GetProperty("snapshot_id").GetString()!);
        string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS");
        if (testMode && checks != null)
            DeckInspectionChecks.Run(checks, screen, player, deckInspection, inspection);
        return InspectionSuccess(request.Id, snapshot.RootElement, inspection);
    }

    private async Task<string> InspectPile(Request request, PileOptions options)
    {
        var player = LocalPlayer;
        var combat = CombatManager.Instance.DebugOnlyGetState();
        bool cardOpen = CardView.Current != null;
        if (!CanInspectPiles())
            return FileMailbox.Error(request.Id, "illegal_action", "Pile viewing is unavailable in the current screen.");
        var screen = PileInspection.Current(options);
        if (screen == null)
        {
            var ui = NCombatRoom.Instance!.Ui;
            NCombatCardPile button = SelectionPileButton(options) ?? (options.Pile switch
                { "draw" => ui.DrawPile, "discard" => ui.DiscardPile, _ => ui.ExhaustPile });
            if (VisibleUi.OnScreen(button) && CardView.Current is { } previous)
            {
                if (!CardView.CanClose(previous))
                    return FileMailbox.Error(request.Id, "illegal_action", "The current card page cannot be replaced.");
                // Native screen context disables combat pile buttons while any card page is open.
                capture.UiChanged();
                CardView.Close(previous);
                await ObservationFrame();
                if (CombatObservation.Status() != "visible" || !CanInspectViews() || !ReferenceEquals(player, LocalPlayer)
                    || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()))
                    return FileMailbox.Error(request.Id, "illegal_action", "The screen changed while switching piles.");
            }
            if (!VisibleUi.OnScreen(button) || !button.IsEnabled)
            {
                using var snapshot = JsonDocument.Parse(Observe());
                bool visible = VisibleUi.OnScreen(button);
                return InspectionSuccess(request.Id, snapshot.RootElement, PileInspection.Result(options, "unavailable",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!, visible
                        ? "The pile button is disabled." : "The pile button is not visible.", null,
                    visible ? "entry_disabled" : "entry_not_visible"));
            }
            var emptyTip = PileInspection.EmptyTip(button);
            if (VisibleUi.Number(button, "CountContainer/Count") == 0 && emptyTip == null)
                return FileMailbox.Error(request.Id, "illegal_action", "The empty pile has no native inspection feedback.");
            capture.UiChanged();
            button.ForceClick();
            screen = PileInspection.Current(options);
            if (screen == null)
            {
                await ObservationFrame();
                if (!ReferenceEquals(player, LocalPlayer) || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
                    || CombatObservation.Status() != "visible" || VisibleUi.Number(button, "CountContainer/Count") != 0 || emptyTip == null)
                    return FileMailbox.Error(request.Id, "illegal_action", "The pile screen did not open or the screen changed.");
                using var snapshot = JsonDocument.Parse(Observe());
                return InspectionSuccess(request.Id, snapshot.RootElement, PileInspection.Result(options, "empty",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!,
                    EnglishCardText.Read(() => EnglishCardText.Plain(emptyTip.GetFormattedText())), Array.Empty<object>()));
            }
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(PileInspection.Current(options), screen) || CardView.Ready(screen));
        if (!ReferenceEquals(PileInspection.Current(options), screen) || !ReferenceEquals(player, LocalPlayer)
            || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
            || CombatObservation.Status(allowCardView: true) != "visible" || !CanInspectViews(allowPause: true))
            return FileMailbox.Error(request.Id, "illegal_action", "The pile screen changed while reading.");
        using var observed = JsonDocument.Parse(Observe());
        var inspection = pileInspection.Read(screen, options, observed.RootElement.GetProperty("snapshot_id").GetString()!);
        return InspectionSuccess(request.Id, observed.RootElement, inspection);
    }

}
