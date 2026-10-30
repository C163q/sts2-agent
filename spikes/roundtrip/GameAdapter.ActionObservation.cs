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
            state = Observe();
            // Logical actions finish before independent card flights update visible pile counters.
            if (settling.Sample(reason, state, CardMotionPending(), timer.Elapsed))
                return (state, reason!);
        }
        return (state, "timeout");
    }
}
