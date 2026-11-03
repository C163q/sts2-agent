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

    private static bool CanInspectCombatants() => CombatObservation.Status() == "visible"
        && LocalPlayer != null && !NCombatRoom.Instance!.Ui.Hand.InCardPlay;

    private static bool CanInspectMap()
    {
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (RunManager.Instance.DebugOnlyGetState() == null || map == null
            || !MapView.Clear(allowCardView: true) || map.IsTraveling) return false;
        if (map.IsOpen && MapView.CardPage == null) return MapView.Ready(map);
        var button = NRun.Instance!.GlobalUi.TopBar.Map;
        bool cardOpen = MapView.CardPage != null;
        return button.IsEnabled && VisibleUi.OnScreen(button) && (map.IsOpen || !VisibleUi.Shown(map))
            && (!CombatManager.Instance.IsInProgress || CanInspectViews(allowPause: map.IsOpen || cardOpen));
    }

    private static bool CanInspectDeck()
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return false;
        if (DeckView.Current is { } current) return DeckView.Ready(current);
        var button = NRun.Instance!.GlobalUi.TopBar.Deck;
        bool cardOpen = CardView.Current != null;
        bool mapOpen = NRun.Instance.GlobalUi.MapScreen.IsOpen;
        bool exposed = CombatManager.Instance.IsInProgress
            ? CombatObservation.Status(allowCardView: cardOpen, allowMap: true) == "visible"
                && CanInspectViews(allowPause: mapOpen || cardOpen)
            : RunUi.NonCombatVisible(allowCardView: true);
        return exposed && VisibleUi.OnScreen(button) && button.IsEnabled;
    }

    private static bool CanInspectPiles()
    {
        bool cardOpen = CardView.Current != null;
        if (LocalPlayer == null || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer
            || CombatObservation.Status(allowCardView: cardOpen) != "visible" || !CanInspectViews(allowPause: cardOpen)) return false;
        var ui = NCombatRoom.Instance!.Ui;
        return new[] { "draw", "discard", "exhaust" }.Any(pile =>
        {
            var button = SelectionPileButton(new PileOptions(pile, "summary"))
                ?? (pile == "draw" ? ui.DrawPile : pile == "discard" ? ui.DiscardPile : ui.ExhaustPile);
            return VisibleUi.OnScreen(button) && (button.IsEnabled || cardOpen && CardView.CanClose(CardView.Current!));
        });
    }

    private (List<string> actions, string visibility) AvailableTools(string scene, object? map,
        EpilogueInspection.Context? epilogue, RunResultInspection.Context? ending, CardSelection? selection)
    {
        List<string> actions = [];
        if (CanEndTurn() && CanPlayCards() && STS2RitsuLib.RitsuLibFramework.IsActive)
            actions.Add("end_turn");
        if (CanPlayCards() && STS2RitsuLib.RitsuLibFramework.IsActive) actions.Add("play_card");
        if (testMode && scene == "main_menu" && !RunManager.Instance.IsInProgress)
            actions.Add("start_test_combat");
        string visibility = scene == "combat" ? CombatObservation.Status() : "not_applicable";
        if (scene == "combat" && visibility != "visible")
            actions.Clear();
        if (selection is { Status: "visible" } && RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
        {
            if (selection.CanSelect) actions.Add("select_card");
            if (selection.Options().Any(option => option.button.IsEnabled)) actions.Add("selection_option");
        }
        if (scene == "unrecognized" && RunUi.NonCombatVisible()) visibility = "visible";
        if (scene == "rewards") visibility = RewardInspection.Exposed(RewardInspection.Current!) ? "visible" : "covered";
        if (scene == "rest_site") visibility = RestSiteInspection.Exposed(RestSiteInspection.Current!) ? "visible" : "covered";
        if (scene == "treasure") visibility = TreasureInspection.Exposed(TreasureInspection.Current!) ? "visible" : "covered";
        if (scene == "shop") visibility = ShopInspection.Exposed(ShopInspection.Current!) ? "visible" : "covered";
        if (scene == "ancient") visibility = AncientInspection.Exposed(AncientInspection.Current!) ? "visible" : "covered";
        if (scene == "event") visibility = EventInspection.Exposed(EventInspection.Current!) ? "visible" : "covered";
        if (DivinationInspection.Current is { } divination && DivinationInspection.Exposed(divination))
        {
            visibility = "visible";
            if (DivinationInspection.Playing(divination)) { actions.Add("set_divination_tool"); actions.Add("divine"); }
            else if (DivinationInspection.Ready(divination) && DivinationInspection.Proceed(divination)?.IsEnabled == true) actions.Add("proceed");
        }
        if (EventInspection.Current is { } currentEvent && EventInspection.Ready(currentEvent))
        {
            if (currentEvent.Layout.OptionButtons.Any(b => !ReferenceEquals(b, EventInspection.Proceed(currentEvent)) && EventInspection.Clickable(b)))
                actions.Add("choose_event_option");
            if (EventInspection.Proceed(currentEvent) is { } button && EventInspection.Clickable(button)) actions.Add("proceed");
        }
        if (AncientInspection.Current is { } ancient && AncientInspection.Ready(ancient))
        {
            if (AncientInspection.Continue(ancient) != null) actions.Add("advance_dialogue");
            else
            {
                if (ancient.Layout.OptionButtons.Any(b => !b.Option.IsProceed && AncientInspection.Clickable(b))) actions.Add("choose_ancient_option");
                if (AncientInspection.Proceed(ancient) is { } button && AncientInspection.Clickable(button)) actions.Add("proceed");
            }
        }
        if (ShopInspection.Current is { } shop && ShopInspection.Ready(shop))
        {
            if (!shop.Inventory.IsOpen)
            {
                if (shop.Merchant.IsEnabled && ShopInspection.MerchantShown(shop)) actions.Add("open_shop");
                if (shop.Proceed.IsEnabled && VisibleUi.OnScreen(shop.Proceed)) actions.Add("proceed");
            }
            else
            {
                if (shop.Inventory.GetAllSlots().Any(ShopInspection.Purchasable)) actions.Add("buy_item");
                if (ShopInspection.Back(shop).IsEnabled) actions.Add("close_shop");
            }
        }
        if (TreasureInspection.Current is { } treasure && TreasureInspection.Ready(treasure))
        {
            if (TreasureInspection.CanLoot(treasure)) actions.Add("loot_treasure");
            if (TreasureInspection.Proceed(treasure)?.IsEnabled == true) actions.Add("proceed");
        }
        if (RestSiteInspection.Current is { } rest && RestSiteInspection.Ready(rest)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
        {
            if (RestSiteInspection.Buttons(rest).Any(RestSiteInspection.Clickable)) actions.Add("choose_rest_option");
            if (RestSiteInspection.Proceed(rest)?.IsEnabled == true) actions.Add("proceed");
        }
        if (RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
        {
            if (RewardInspection.Buttons(rewards).Any(b => RewardInspection.Type(b.Reward!) != "unsupported")) actions.Add("claim_reward");
            if (RewardInspection.Proceed(rewards)?.IsEnabled == true) actions.Add("proceed");
        }
        if (EventConfirmation.Current is { } dialog && EventConfirmation.Exposed(dialog))
        {
            visibility = "visible";
            actions.Clear();
            if (EventConfirmation.Ready(dialog)) actions.Add("respond_to_confirmation");
        }
        if (map != null)
        {
            visibility = "visible";
            actions.Clear();
            if (MapInspection.Choices(NRun.Instance!.GlobalUi.MapScreen).Length > 0) actions.Add("travel_to_node");
        }
        if (epilogue != null && map == null)
        {
            visibility = EpilogueInspection.Exposed(epilogue) ? "visible" : "covered";
            actions.Clear();
            if (EpilogueInspection.Ready(epilogue) && EpilogueInspection.Button(epilogue) is { } epilogueButton)
                actions.Add(EpilogueInspection.IsProceed(epilogueButton) ? "proceed" : "advance_dialogue");
        }
        if (ending != null)
        {
            visibility = RunResultInspection.Exposed(ending) ? "visible" : "covered";
            actions.Clear();
            if (runResultInspection.Ready(ending)) actions.Add("run_result_option");
        }

        if (ending != null)
        {
            if (runResultInspection.Ready(ending))
            {
                actions.Add("inspect_run_result");
            }
            if (PotionInspection.VisibleHolders() != null) actions.Add("inspect_potions");
            if (RelicInspection.VisibleHolders() != null) actions.Add("inspect_relics");
            return (actions.Distinct().ToList(), visibility);
        }
        if ((!CombatManager.Instance.IsInProgress || STS2RitsuLib.RitsuLibFramework.IsActive)
            && CanHandlePotions() && PotionInspection.VisibleHolders() is { } holders)
        {
            var visiblePotions = holders.Where(h => h.HasPotion && PotionActions.Type(h.Potion!.Model) != null).Select(h => h.Potion!.Model).ToArray();
            if (visiblePotions.Any(p => PotionActions.Reason(p) == null)) actions.Add("use_potion");
            if (visiblePotions.Any(PotionActions.Discardable)) actions.Add("discard_potion");
        }
        if (CanInspectHand()) actions.Add("inspect_hand");
        if (CombatObservation.Status() == "visible") actions.Add("inspect_ui");
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
            if (selection.CanPeek) actions.Add("set_selection_view");
        }
        if (CanPlayCards() && NPlayerHand.Instance!.ActiveHolders.Any(holder => CardSelection.Clickable(holder)
                && TargetInspection.Type(holder.CardModel!) != null)
            || CanHandlePotions() && PotionInspection.VisibleHolders() is { } targetHolders
                && targetHolders.Any(h => h.HasPotion && PotionActions.Type(h.Potion!.Model) != null)) actions.Add("inspect_targets");
        if (RewardInspection.Current is { } rewardPage && RewardInspection.Ready(rewardPage)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer) actions.Add("inspect_rewards");
        if (RestSiteInspection.Current is { } restPage && RestSiteInspection.Ready(restPage)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer) actions.Add("inspect_rest_site");
        if (TreasureInspection.Current is { } treasurePage && TreasureInspection.Exposed(treasurePage)) actions.Add("inspect_treasure");
        if (ShopInspection.Current is { } shopPage && ShopInspection.Exposed(shopPage) && TreasureInspection.Singleplayer
            && shopPage.Inventory.IsOpen && !ShopInspection.Animating(shopPage)) actions.Add("inspect_shop");
        if (AncientInspection.Current is { } ancientPage && AncientInspection.Exposed(ancientPage)
            && TreasureInspection.Singleplayer) actions.Add("inspect_ancient");
        if (DivinationInspection.Current is { } board ? DivinationInspection.Ready(board)
            : EventInspection.Current is { } eventPage && EventInspection.Exposed(eventPage) && TreasureInspection.Singleplayer)
            actions.Add("inspect_event");
        return (actions.Distinct().ToList(), visibility);
    }
}
