using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private sealed record ProceedTarget(NButton Button, Func<bool>? SameContext = null, bool EventCombat = false);

    private string? ProceedUnavailableReason(out ProceedTarget? target)
    {
        target = null;
        if (runResultInspection.Current != null)
            return "Use run_result_option for the current run result; inspect_run_result shows its buttons.";
        if (!RunManager.Instance.IsInProgress)
            return "No local run is available for proceeding.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Proceeding requires a local single-player run.";
        if (VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen))
            return NRun.Instance!.GlobalUi.MapScreen.IsOpen
                ? "Close the map with close_map before proceeding."
                : "Wait for the map to finish closing before proceeding.";
        if (CardView.Current != null)
            return "Close the card browsing page with close_card_view before proceeding.";
        if (CardSelection.Current != null)
            return "Resolve the current card selection with select_card or selection_option before proceeding; inspect_selection shows its choices.";
        if (NModalContainer.Instance?.OpenModal != null)
            return EventConfirmation.Current != null
                ? "Resolve the confirmation with respond_to_confirmation before proceeding."
                : "A dialog covers the current screen. Resolve it before proceeding.";
        if (RunUi.Transitioning()) return "Wait for the screen transition before proceeding.";

        NButton? button;
        if (EpilogueInspection.Current is { } epilogue)
        {
            if (!EpilogueInspection.Exposed(epilogue)) return "The Architect dialogue is covered by another screen.";
            var option = EpilogueInspection.Button(epilogue);
            button = option;
            if (option != null && !EpilogueInspection.IsProceed(option))
                return "Finish the Architect dialogue with advance_dialogue before proceeding.";
            if (!EpilogueInspection.Ready(epilogue)) return "Wait for the Architect dialogue and its button to finish appearing.";
        }
        else if (RewardInspection.Current is { } rewards)
        {
            if (RewardInspection.InspectionUnavailableReason(rewards) is { } reason) return reason;
            button = RewardInspection.Proceed(rewards);
        }
        else if (AncientInspection.Current is { } ancient)
        {
            if (!AncientInspection.Exposed(ancient)) return "The ancient is covered by another screen.";
            if (!AncientInspection.Ready(ancient)) return "Wait for the ancient's dialogue or gift effects to finish.";
            if (AncientInspection.Continue(ancient) != null)
                return "Finish the ancient's dialogue with advance_dialogue before proceeding.";
            var option = AncientInspection.Proceed(ancient);
            if (option == null) return "Choose an ancient's gift with choose_ancient_option before proceeding.";
            if (!AncientInspection.Clickable(option)) return "The ancient's Proceed option is still disabled or animating.";
            target = new(option, () => ReferenceEquals(ancient.Model, AncientInspection.Current?.Model));
            return null;
        }
        else if (DivinationInspection.Current is { } divination)
        {
            if (!DivinationInspection.Exposed(divination)) return "The divination board is covered by another screen.";
            if (!DivinationInspection.Ready(divination)) return "Wait for the current divination reveal or reward effects to finish.";
            if (DivinationInspection.Playing(divination)) return "Finish divination with divine before proceeding.";
            button = DivinationInspection.Proceed(divination);
        }
        else if (EventInspection.Current is { } currentEvent)
        {
            if (!EventInspection.Exposed(currentEvent)) return "The event is covered by another screen.";
            if (!EventInspection.Ready(currentEvent)) return "Wait for the event text, options or current effects to finish.";
            var option = EventInspection.Proceed(currentEvent);
            if (option == null) return "Resolve the event with choose_event_option before proceeding; inspect_event shows its options.";
            if (!EventInspection.Clickable(option)) return "The event's Proceed option is still disabled or animating.";
            target = new(option, EventCombat: true);
            return null;
        }
        else if (ShopInspection.Current is { } shop)
        {
            if (!ShopInspection.Exposed(shop)) return "The shop is covered by another screen.";
            if (shop.Inventory.IsOpen) return "Close the shop inventory with close_shop before proceeding.";
            if (!ShopInspection.Ready(shop)) return "Wait for the current shop interaction to finish before proceeding.";
            button = VisibleUi.OnScreen(shop.Proceed) ? shop.Proceed : null;
        }
        else if (TreasureInspection.Current is { } treasure)
        {
            if (!TreasureInspection.Exposed(treasure)) return "The treasure room is covered by another screen.";
            if (!TreasureInspection.Opened(treasure)) return "Open the chest with loot_treasure before proceeding.";
            if (!TreasureInspection.Ready(treasure)) return "Wait for the chest opening or relic effects to finish before proceeding.";
            button = TreasureInspection.Proceed(treasure);
            if (button?.IsEnabled != true) return "The treasure room's Skip/Proceed button is not available yet.";
            target = new(button, () => ReferenceEquals(treasure, TreasureInspection.Current));
            return null;
        }
        else if (RestSiteInspection.Current is { } rest)
        {
            if (!RestSiteInspection.Exposed(rest)) return "The rest site is covered by another screen.";
            if (!RestSiteInspection.Ready(rest)) return "Wait for the current rest site interaction to finish before proceeding.";
            button = RestSiteInspection.Proceed(rest);
            if (button?.IsEnabled != true) return "Use choose_rest_option to complete a rest site activity before proceeding.";
        }
        else if (CombatManager.Instance.IsInProgress)
            return "Proceed is unavailable during combat. Use the available combat actions.";
        else
            return "No Skip/Proceed button is available on the current screen.";

        if (button?.IsEnabled != true) return "The current Skip/Proceed button is not available yet.";
        target = new(button);
        return null;
    }

    private async Task<string> ProceedRequest(Request request, JsonElement before)
    {
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current screen before proceeding.");
        if (ProceedUnavailableReason(out var target) is { } reason)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", reason);
        var run = RunManager.Instance.DebugOnlyGetState();
        var combat = target!.EventCombat ? CombatJournalScope.Current : null;
        UiChanged();
        target.Button.ForceClick();
        var (after, stop) = await ActionObservation(() =>
            !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) || target.SameContext?.Invoke() == false
                ? "interrupted" : combat?.StopReason(CanPlayCards()) ?? NonCombatBoundary());
        return combat != null ? Success(request, ResponseBuilder.WithTransition(after, combat.Result(stop)))
            : TransitionSuccess(request, after, stop);
    }
}
