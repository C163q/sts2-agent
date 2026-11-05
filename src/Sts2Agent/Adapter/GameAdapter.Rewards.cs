using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Rewards;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private string? NonCombatBoundary(bool includeRunOutcome = true)
    {
        if (runResultInspection.Current is { } result)
            return runResultInspection.Ready(result)
                ? includeRunOutcome ? RunResultInspection.Outcome(result) : "action_completed" : null;
        if (runResultInspection.ReturningToMenu && NGame.Instance?.MainMenu is { } menu
            && !menu.SubmenuStack.SubmenusOpen && VisibleUi.Shown(menu) && !RunUi.Transitioning()) return "action_completed";
        if (EpilogueInspection.Current is { } epilogue) return EpilogueInspection.Ready(epilogue) ? "action_completed" : null;
        if (CombatManager.Instance.IsStarting) return null;
        if (NavigationTasks.ChangingAct && !CardSelection.AwaitingInput) return null;
        if (EventConfirmation.Current is { } popup && EventConfirmation.Exposed(popup))
            return EventConfirmation.Ready(popup) ? "action_completed" : null;
        var selection = CardSelection.Current;
        var rewards = RewardInspection.Current;
        var rest = RestSiteInspection.Current;
        var treasure = TreasureInspection.Current;
        var shop = ShopInspection.Current;
        var ancient = AncientInspection.Current;
        var currentEvent = EventInspection.Current;
        var global = NRun.Instance?.GlobalUi;
        bool mapReady = global != null && MapView.Ready(global.MapScreen);
        bool mapOpening = global != null && MapView.Current(global.MapScreen);
        bool manual = NModalContainer.Instance?.OpenModal != null || global?.CapstoneContainer.InUse == true && selection?.Kind != "view_cards"
            || selection is { Supported: false, Exposed: true }
            || global?.Overlays.ScreenCount > 0 && !RunUi.OnlyRewardOverlays() && !DivinationInspection.OnlyOverlay
                && (selection == null || !ReferenceEquals(global.Overlays.Peek(), selection.Owner))
            || rewards == null && rest == null && treasure == null && shop == null && ancient == null && currentEvent == null && selection == null && !mapOpening && RunUi.NonCombatVisible()
            || (treasure != null || shop != null || ancient != null || currentEvent != null) && !RunContext.Singleplayer
            || NGame.Instance?.MainMenu != null;
        bool ready = DivinationInspection.Current is { } divination && DivinationInspection.Ready(divination)
            || rewards != null && RewardInspection.Ready(rewards)
            || rest != null && RestSiteInspection.Ready(rest)
            || treasure != null && TreasureInspection.Ready(treasure)
            || shop != null && ShopInspection.Ready(shop)
            || ancient != null && AncientInspection.Ready(ancient)
            || currentEvent != null && EventInspection.Ready(currentEvent)
            || mapReady && (treasure == null || !RelicObtainTracker.Pending) && !ShopInspection.Busy && !AncientInspection.Busy && !EventTaskTracker.Pending;
        var boundary = RewardBoundary.Decide(RunUi.Transitioning(), manual, CardSelection.AwaitingInput, ready,
            runLost: includeRunOutcome && !CombatManager.Instance.IsInProgress && EventTaskTracker.RunLost);
        return boundary ?? (CanPlayCards() ? "player_ready" : null);
    }

    private async Task<string> RewardRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_rewards";
        bool claim = request.Operation == "claim_reward";
        bool interacted = false;
        void BeginInteraction()
        {
            if (!interacted) UiChanged();
            interacted = true;
        }
        string RejectClaim(string message) => interacted
            ? ResponseBuilder.Error(request.Id, "illegal_action", message, publicMessage: true)
            : FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", message);
        int rewardId = -1;
        if (claim)
        {
            if (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
                || !args.TryGetProperty("reward_id", out var id) || id.ValueKind != JsonValueKind.Number
                || !id.TryGetInt32(out rewardId) || rewardId < 0)
                return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "A nonnegative reward_id is required.");
        }
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current rewards before acting.");
        var screen = RewardInspection.Current;
        if (inspect)
        {
            if (RewardInspection.InspectionUnavailableReason(screen) is { } reason)
                return ResponseBuilder.Error(request.Id, "illegal_action", reason, publicMessage: true);
            return InspectionSuccess(request, before, new { rewards = rewardInspection.Read(full: true) });
        }
        var run = RunManager.Instance.DebugOnlyGetState();
        NRewardButton? row = null;
        NButton? button;
        if (claim)
        {
            if (rewardInspection.ClaimUnavailableReason(screen, rewardId, out row) is { } reason) return RejectClaim(reason);
            button = row;
        }
        else
        {
            if (screen == null || !RewardInspection.Ready(screen) || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
                return FileMailbox.Error(request.Id, "illegal_action", "Return to an available local rewards screen.");
            button = RewardInspection.Proceed(screen);
            if (button?.IsEnabled != true)
                return FileMailbox.Error(request.Id, "illegal_action", "The requested reward or proceed button is unavailable.");
        }
        bool finished = row == null;
        bool? claimed = null;
        var potionReward = row?.Reward as PotionReward;
        bool potionObtained = false;
        void Procured(PotionModel potion) { if (ReferenceEquals(potion, potionReward?.Potion)) potionObtained = true; }
        void Claimed(NRewardButton _) { finished = true; claimed = true; }
        void Skipped(NRewardButton _) { finished = true; claimed = false; }
        if (row != null)
        {
            var originalRows = RewardInspection.Buttons(screen!).Select(b => b.Reward).ToArray();
            bool Unchanged() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
                && RewardInspection.Ready(screen!) && originalRows.SequenceEqual(RewardInspection.Buttons(screen!).Select(b => b.Reward));
            try { await RewardInspection.Reveal(screen!, row, ObservationFrame, Unchanged, BeginInteraction); }
            catch (InvalidOperationException)
            {
                return RejectClaim("The reward list changed or the row could not be revealed while preparing the claim. Read current rewards before continuing.");
            }
            if (!Unchanged()) return RejectClaim("The rewards changed before clicking. Read current rewards before continuing.");
        }
        try
        {
            BeginInteraction();
            if (row != null)
            {
                RewardCompatibility.AdaptLinkedClaim(row);
                row.RewardClaimed += Claimed;
                row.RewardSkipped += Skipped;
                if (potionReward != null) potionReward.Player.PotionProcured += Procured;
            }
            button!.ForceClick();
            var (after, reason) = await ActionObservation(() =>
            {
                if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())) return "interrupted";
                var boundary = NonCombatBoundary();
                // A choice suspends GetReward; claim/skip signals mark ordinary reward resolution.
                bool nestedReward = RewardInspection.Current is { } current && !ReferenceEquals(current, screen)
                    && RewardInspection.Ready(current);
                return boundary is "choice_required" or "manual_input_required" || finished || nestedReward ? boundary : null;
            });
            object? rewardResult = row == null ? null : new
            {
                reward_id = rewardId, status = claimed == true ? potionReward != null && !potionObtained ? "not_obtained" : "claimed"
                    : claimed == false ? "not_claimed" : "pending"
            };
            return TransitionSuccess(request, after, reason, rewardResult: rewardResult);
        }
        finally
        {
            if (potionReward != null) potionReward.Player.PotionProcured -= Procured;
            if (row != null && GodotObject.IsInstanceValid(row))
            {
                row.RewardClaimed -= Claimed;
                row.RewardSkipped -= Skipped;
            }
        }
    }
}
