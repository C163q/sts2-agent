using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class RelicObtainTracker
{
    private static readonly List<(IRunState run, Task task)> Tasks = [];

    public static bool Pending
    {
        get
        {
            Prune();
            return Tasks.Count > 0;
        }
    }

    private static void Prune() => Tasks.RemoveAll(t => t.task.IsCompleted
        || !ReferenceEquals(t.run, RunManager.Instance.DebugOnlyGetState()));

    public static void Initialize() => new Harmony("sts2_agent.relic_obtain_tracker").Patch(
        AccessTools.Method(typeof(RelicCmd), nameof(RelicCmd.Obtain), [typeof(RelicModel), typeof(Player), typeof(int)]),
        postfix: new HarmonyMethod(typeof(RelicObtainTracker), nameof(Obtaining)));

    // Treasure UI starts this task without awaiting it; observe completion without replacing its flow.
    private static void Obtaining(Player __1, Task<RelicModel> __result)
    {
        Prune();
        if (!__result.IsCompleted) Tasks.Add((__1.RunState, __result));
    }
}
