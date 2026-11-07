using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CanInspectHand() => CombatObservation.Status() == "visible"
        && NCombatRoom.Instance?.Ui.Hand is { } hand && VisibleUi.Shown(hand) && !hand.InCardPlay;

    private static bool CanInspectCombatants() => LocalPlayer != null
        && CombatantInspection.UnavailableReason(CombatantInspection.Level.Summary) == null;

    private static bool CanInspectMap() => MapUnavailableReason() == null;

    private static string? MapUnavailableReason()
    {
        if (RunManager.Instance.DebugOnlyGetState() == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for map viewing.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Map viewing requires a local single-player run.";
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (map == null) return "The map entry is not ready.";
        if (map.IsTraveling) return "Wait for map travel to finish before viewing the map.";
        if (!MapView.Clear(allowCardView: true))
        {
            if (RunUi.Transitioning()) return "Wait for the screen transition before opening the map.";
            if (CardSelection.Current is { Status: "visible" })
                return "Return from the card selection before opening the map.";
            return "The map entry is covered by a dialog, selection or another detail page.";
        }
        if (map.IsOpen && MapView.CardPage == null)
            return MapView.Ready(map) ? null : "The map is still preparing. Wait before viewing it.";
        var button = NRun.Instance!.GlobalUi.TopBar.Map;
        if (!VisibleUi.OnScreen(button)) return "The map button is not visible.";
        if (!button.IsEnabled) return "The map button is disabled.";
        if (!map.IsOpen && VisibleUi.Shown(map)) return "Wait for the map to finish closing before reopening it.";
        bool cardOpen = MapView.CardPage != null;
        if (CombatManager.Instance.IsInProgress && !CanInspectViews(allowPause: map.IsOpen || cardOpen))
            return "Combat is not ready for map browsing. Wait for the current action to finish.";
        return null;
    }

    private static bool CanInspectDeck() => DeckUnavailableReason() == null;

    private static string? DeckUnavailableReason()
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for deck browsing.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Deck browsing requires a local single-player run.";
        if (DeckView.Current is { } current)
            return DeckView.Ready(current) ? null : "The deck page is still preparing.";
        var button = NRun.Instance?.GlobalUi.TopBar.Deck;
        if (button == null) return "The deck entry is not ready.";
        bool cardOpen = CardView.Current != null;
        bool mapOpen = NRun.Instance!.GlobalUi.MapScreen.IsOpen;
        bool exposed = CombatManager.Instance.IsInProgress
            ? CombatObservation.Status(allowCardView: cardOpen, allowMap: true) == "visible"
                && CanInspectViews(allowPause: mapOpen || cardOpen)
            : RunUi.NonCombatVisible(allowCardView: true);
        if (!exposed)
        {
            if (CardSelection.Current is { Status: "visible" })
                return "Return from the card selection before opening the deck.";
            if (RunUi.Transitioning()) return "Wait for the screen transition before opening the deck.";
            return "The deck entry is covered or combat is not ready for browsing.";
        }
        if (!VisibleUi.OnScreen(button)) return "The deck button is not visible.";
        return button.IsEnabled ? null : "The deck button is disabled.";
    }

    private static bool CanInspectPiles() => PileUnavailableReason() == null;

    private static string? PileUnavailableReason()
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for combat pile browsing.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Combat pile browsing requires a local single-player run.";
        bool cardOpen = CardView.Current != null;
        if (CombatObservation.Status(allowCardView: cardOpen) != "visible" || !CanInspectViews(allowPause: cardOpen))
        {
            if (CardSelection.Current is { Status: "visible" })
                return "Return from the card selection before opening a combat pile.";
            if (NRun.Instance?.GlobalUi.MapScreen.IsOpen == true)
                return "Close the map before opening a combat pile.";
            if (!CombatManager.Instance.IsInProgress)
                return "Combat piles are available only during combat.";
            if (RunUi.Transitioning()) return "Wait for the screen transition before opening a combat pile.";
            return "Combat pile entries are covered or combat is not ready for browsing.";
        }
        // An exposed pile page remains readable when the pending choice hides its entry buttons.
        if (CardView.Current is MegaCrit.Sts2.Core.Nodes.Screens.NCardPileScreen current && CardView.Ready(current))
            return null;
        var ui = NCombatRoom.Instance!.Ui;
        bool available = new[] { "draw", "discard", "exhaust" }.Any(pile =>
        {
            var button = SelectionPileButton(new PileOptions(pile))
                ?? (pile == "draw" ? ui.DrawPile : pile == "discard" ? ui.DiscardPile : ui.ExhaustPile);
            return VisibleUi.OnScreen(button) && (button.IsEnabled || cardOpen && CardView.CanClose(CardView.Current!));
        });
        return available ? null : "No combat pile entry is visible and enabled for browsing.";
    }

    private List<string> AvailableTools(string scene, object? map,
        EpilogueInspection.Context? epilogue, RunResultInspection.Context? ending, CardSelection? selection)
    {
        List<string> actions = [];
        if (EndTurnUnavailableReason() == null)
            actions.Add("end_turn");
        if (CanPlayCards() && STS2RitsuLib.RitsuLibFramework.IsActive)
        { actions.Add("play_card"); actions.Add("play_cards"); }
        if (testMode && scene == "main_menu" && !RunManager.Instance.IsInProgress)
            actions.Add("start_test_combat");
        if (scene == "combat" && CombatObservation.Status() != "visible")
            actions.Clear();
        if (selection is { Status: "visible" } && RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
        {
            if (selection.CanSelect) actions.Add("select_card");
            if (selection.Options().Any(option => option.button.IsEnabled)) actions.Add("selection_option");
        }
        if (DivinationInspection.Current is { } divination && DivinationInspection.Exposed(divination))
        {
            if (new[] { "big", "small" }.Any(tool => DivinationInspection.ToolUnavailableReason(divination, tool) == null))
                actions.Add("set_divination_tool");
            if (DivinationInspection.Playing(divination)) actions.Add("divine");
        }
        if (EventInspection.Current is { } currentEvent && EventInspection.ActionUnavailableReason(currentEvent) == null)
        {
            if (currentEvent.Layout.OptionButtons.Any(b => !ReferenceEquals(b, EventInspection.Proceed(currentEvent)) && EventInspection.Clickable(b)))
                actions.Add("choose_event_option");
        }
        if (AncientInspection.Current is { } ancient && AncientInspection.Ready(ancient))
        {
            if (AncientInspection.Continue(ancient) != null) actions.Add("advance_dialogue");
            else
            {
                if (ancient.Layout.OptionButtons.Any(b => !b.Option.IsProceed && AncientInspection.Clickable(b))) actions.Add("choose_ancient_option");
            }
        }
        if (ShopInspection.Current is { } shop)
        {
            if (ShopInspection.OpenUnavailableReason(shop) == null) actions.Add("open_shop");
            if (ShopInspection.PurchaseUnavailableReason(shop) == null)
            {
                if (shop.Inventory.GetAllSlots().Any(ShopInspection.Purchasable)) actions.Add("buy_item");
            }
            if (ShopInspection.CloseUnavailableReason(shop) == null) actions.Add("close_shop");
        }
        if (TreasureInspection.Current is { } treasure)
        {
            if (TreasureInspection.CanLoot(treasure)) actions.Add("loot_treasure");
        }
        if (RestSiteInspection.Current is { } rest && RestSiteInspection.ActionUnavailableReason(rest) == null)
        {
            if (RestSiteInspection.Buttons(rest).Any(RestSiteInspection.Clickable)) actions.Add("choose_rest_option");
        }
        if (RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
        {
            if (RewardInspection.Buttons(rewards).Any(RewardInspection.Claimable)) actions.Add("claim_reward");
        }
        if (EventConfirmation.Current is { } dialog && EventConfirmation.Exposed(dialog))
        {
            actions.Clear();
            if (EventConfirmation.Ready(dialog)) actions.Add("respond_to_confirmation");
        }
        if (map != null)
        {
            actions.Clear();
            if (MapInspection.Choices(NRun.Instance!.GlobalUi.MapScreen).Length > 0) actions.Add("travel_to_node");
        }
        if (epilogue != null && map == null)
        {
            actions.Clear();
            if (EpilogueInspection.Ready(epilogue) && EpilogueInspection.Button(epilogue) is { } epilogueButton)
                if (!EpilogueInspection.IsProceed(epilogueButton)) actions.Add("advance_dialogue");
        }
        if (ending != null)
        {
            actions.Clear();
            if (runResultInspection.Ready(ending)) actions.Add("run_result_option");
        }

        if (ProceedUnavailableReason(out _) == null) actions.Add("proceed");

        if (ending != null)
        {
            if (UiInspection.CanRead()) actions.Add("inspect_ui");
            if (runResultInspection.Ready(ending))
            {
                actions.Add("inspect_run_result");
            }
            if (PotionInspection.VisibleHolders() != null) actions.Add("inspect_potions");
            if (RelicInspection.VisibleHolders() != null) actions.Add("inspect_relics");
            return actions.Distinct().ToList();
        }
        if ((!CombatManager.Instance.IsInProgress || STS2RitsuLib.RitsuLibFramework.IsActive)
            && PotionInspection.ExposedHolders() is { } holders)
        {
            var visiblePotions = holders.Where(h => PotionInspection.Displayed(h) && h.HasPotion && PotionActions.Type(h.Potion!.Model) != null).Select(h => h.Potion!.Model).ToArray();
            if (CanHandlePotions() && visiblePotions.Any(p => PotionActions.Reason(p) == null)) actions.Add("use_potion");
            if (CanDiscardPotions() && visiblePotions.Any(PotionActions.Discardable)) actions.Add("discard_potion");
        }
        if (CanInspectHand()) actions.Add("inspect_hand");
        if (UiInspection.CanRead()) actions.Add("inspect_ui");
        if (CanInspectCombatants()) actions.Add("inspect_combatants");
        if (PotionInspection.VisibleHolders() != null) actions.Add("inspect_potions");
        if (RelicInspection.VisibleHolders() != null) actions.Add("inspect_relics");
        if (CanInspectDeck()) actions.Add("inspect_deck");
        if (CanInspectPiles()) actions.Add("inspect_pile");
        if (CardView.Current is { } cardPage && CardView.CanClose(cardPage)) actions.Add("close_card_view");
        if (CanInspectMap()) actions.Add("inspect_map");
        if (NRun.Instance?.GlobalUi.MapScreen is { } mapPage && MapView.CanClose(mapPage)) actions.Add("close_map");
        if (RunManager.Instance.IsSingleplayerOrFakeMultiplayer && selection is { Supported: true })
        {
            if (selection.Status == "visible") actions.Add("inspect_selection");
            if (SelectionAvailability.ViewUnavailableReason(selection) == null) actions.Add("set_selection_view");
        }
        if (CanPlayCards() && NPlayerHand.Instance!.ActiveHolders.Any(holder => CardSelection.Clickable(holder)
                && TargetInspection.Type(holder.CardModel!) != null)
            || (CanHandlePotions() || CanDiscardPotions()) && PotionInspection.ExposedHolders() is { } targetHolders
                && targetHolders.Any(h => PotionInspection.Displayed(h) && h.HasPotion && PotionActions.Type(h.Potion!.Model) != null)) actions.Add("inspect_targets");
        if (RewardInspection.InspectionUnavailableReason(RewardInspection.Current) == null) actions.Add("inspect_rewards");
        if (RestSiteInspection.InspectionUnavailableReason(RestSiteInspection.Current) == null) actions.Add("inspect_rest_site");
        if (TreasureInspection.InspectionUnavailableReason(TreasureInspection.Current) == null) actions.Add("inspect_treasure");
        if (ShopInspection.InspectionUnavailableReason(ShopInspection.Current) == null) actions.Add("inspect_shop");
        if (AncientInspection.Current is { } ancientPage && AncientInspection.Exposed(ancientPage)
            && RunContext.Singleplayer) actions.Add("inspect_ancient");
        if (DivinationInspection.Current is { } board ? DivinationInspection.InspectionUnavailableReason(board) == null
            : EventInspection.InspectionUnavailableReason(EventInspection.Current) == null)
            actions.Add("inspect_event");
        return actions.Distinct().ToList();
    }
}
