using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private readonly RewardInspection rewardInspection = new();

    private static string? NonCombatBoundary()
    {
        var selection = CardSelection.Current;
        var rewards = RewardInspection.Current;
        var rest = RestSiteInspection.Current;
        var global = NRun.Instance?.GlobalUi;
        bool mapReady = global != null && MapView.Ready(global.MapScreen);
        bool manual = NModalContainer.Instance?.OpenModal != null || global?.CapstoneContainer.InUse == true
            || selection is { Supported: false, Exposed: true }
            || global?.Overlays.ScreenCount > 0 && !RunUi.OnlyRewardOverlays()
                && (selection == null || !ReferenceEquals(global.Overlays.Peek(), selection.Owner))
            || rewards == null && rest == null && selection == null && !mapReady && RunUi.NonCombatVisible()
            || NGame.Instance?.MainMenu != null;
        bool ready = rewards != null && RewardInspection.Ready(rewards)
            || rest != null && RestSiteInspection.Ready(rest)
            || mapReady;
        return RewardBoundary.Decide(RunUi.Transitioning(), manual, CardSelection.AwaitingInput, ready);
    }

    private async Task<string> RewardRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_rewards";
        int rewardId = -1;
        if (request.Operation == "claim_reward")
        {
            if (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
                || !args.TryGetProperty("reward_id", out var id) || id.ValueKind != JsonValueKind.Number
                || !id.TryGetInt32(out rewardId) || rewardId < 0)
                return FileMailbox.Error(request.Id, "invalid_request", "A nonnegative reward_id is required.");
        }
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current rewards before acting.");
        var screen = RewardInspection.Current;
        if (screen == null || !RewardInspection.Ready(screen) || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available local rewards screen.");
        if (inspect) return Success(request.Id, JsonSerializer.Serialize(new
        {
            snapshot_id = before.GetProperty("snapshot_id").GetString(), scene = "rewards", rewards = rewardInspection.Read(full: true)
        }));

        var run = RunManager.Instance.DebugOnlyGetState();
        NRewardButton? row = request.Operation == "claim_reward" ? rewardInspection.Find(screen, rewardId) : null;
        NButton? button = request.Operation == "proceed" ? RewardInspection.Proceed(screen) : row;
        if (button?.IsEnabled != true || row != null && RewardInspection.Type(row.Reward!) == "unsupported")
            return FileMailbox.Error(request.Id, "illegal_action", "The requested reward or proceed button is unavailable.");
        bool finished = row == null;
        bool? claimed = null;
        void Claimed(NRewardButton _) { finished = true; claimed = true; }
        void Skipped(NRewardButton _) { finished = true; claimed = false; }
        if (row != null)
        {
            var originalRows = RewardInspection.Buttons(screen).Select(b => b.Reward).ToArray();
            bool Unchanged() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
                && RewardInspection.Ready(screen) && originalRows.SequenceEqual(RewardInspection.Buttons(screen).Select(b => b.Reward));
            try { await RewardInspection.Reveal(screen, row, ObservationFrame, Unchanged); }
            catch (InvalidOperationException error) { return FileMailbox.Error(request.Id, "illegal_action", error.Message); }
            if (!Unchanged()) return FileMailbox.Error(request.Id, "illegal_action", "Rewards changed before clicking.");
            RewardCompatibility.AdaptLinkedClaim(row);
            row.RewardClaimed += Claimed;
            row.RewardSkipped += Skipped;
        }
        try
        {
            uiGeneration++;
            button.ForceClick();
            var (after, reason) = await ActionObservation(() =>
            {
                if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())) return "interrupted";
                var boundary = NonCombatBoundary();
                // A choice suspends GetReward; claim/skip signals mark ordinary reward resolution.
                bool nestedReward = RewardInspection.Current is { } current && !ReferenceEquals(current, screen)
                    && RewardInspection.Ready(current);
                return boundary is "choice_required" or "manual_input_required" || finished || nestedReward ? boundary : null;
            });
            string rewardResult = row == null ? "" : ",\"reward_result\":" + JsonSerializer.Serialize(new
            {
                reward_id = rewardId, status = claimed == true ? "claimed" : claimed == false ? "not_claimed" : "pending"
            });
            return Success(request.Id, after[..^1] + rewardResult + ",\"transition\":" + JsonSerializer.Serialize(new
            {
                stop_reason = reason, complete = reason is not ("timeout" or "interrupted"), events = Array.Empty<object>()
            }) + "}");
        }
        finally
        {
            if (row != null && GodotObject.IsInstanceValid(row))
            {
                row.RewardClaimed -= Claimed;
                row.RewardSkipped -= Skipped;
            }
        }
    }
}
