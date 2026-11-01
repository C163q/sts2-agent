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
            if (CombatEntryCapture.Current != null && MegaCrit.Sts2.Core.Combat.CombatManager.Instance.IsStarting
                && reason is not ("interrupted" or "manual_input_required")) reason = null;
            if (CombatEntryCapture.Current is { Capturing: true } entering
                && reason is not ("interrupted" or "manual_input_required"))
                reason = entering.StopReason(CanPlayCards());
            state = Observe();
            // Logical actions finish before independent UI motion stops changing the observation.
            if (settling.Sample(reason, state, CardMotionPending() || RunUi.CardPreviewsPending()
                || CombatMotion.Pending() || RunUi.ResourceMotionPending()
                || CombatResourceJournal.Current?.Pending == true || OrbJournal.Current?.Pending == true, timer.Elapsed))
                return (state, reason!);
        }
        return (state, "timeout");
    }
}
