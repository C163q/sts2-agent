using System.Diagnostics;
using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CardMotionPending() => NGame.Instance is { } game
        && VisibleUi.Descendants<Node>(game).Any(node => !node.IsQueuedForDeletion()
            && node is NCardFlyVfx or NCardFlyShuffleVfx or NCardFlyPowerVfx);

    private async Task<(string state, string reason)> ActionObservation(Func<string?> stopReason, TimeSpan? timeout = null)
    {
        var timer = Stopwatch.StartNew();
        var settling = new ActionSettling();
        string state = Observe();
        while (timer.Elapsed < (timeout ?? TimeSpan.FromSeconds(25)))
        {
            await ObservationFrame();
            string? reason = stopReason();
            if (CombatJournalScope.Current?.Pending == true
                && reason is not ("interrupted" or "manual_input_required" or "choice_required")) reason = null;
            if (CombatJournalScope.Current is { StartedCombat: true } entering
                && reason is not ("interrupted" or "manual_input_required"))
                reason = entering.StopReason(CanPlayCards());
            if (reason == "combat_won" && NonCombatBoundary(includeRunOutcome: false) == null)
                reason = null;
            state = Observe();
            // Logical actions finish before independent UI motion stops changing the observation.
            if (settling.Sample(reason, state, CardMotionPending() || RunUi.CardPreviewsPending()
                || CombatMotion.Pending() || RunUi.ResourceMotionPending()
                || CombatResourceJournal.Current?.Pending == true || OrbJournal.Current?.Pending == true
                || RunResourceJournal.Current?.Pending == true
                || TurnCapture.Journal?.Pending == true, timer.Elapsed,
                choiceMotionPending: RunUi.GoldMotionPending() || RunResourceJournal.Current?.Pending == true))
                return (state, reason!);
        }
        return (state, "timeout");
    }
}
