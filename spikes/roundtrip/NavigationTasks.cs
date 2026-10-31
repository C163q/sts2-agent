using HarmonyLib;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class NavigationTasks
{
    private static readonly List<(IRunState? run, Task task)> Acts = [];

    public static bool ChangingAct
    {
        get
        {
            Acts.RemoveAll(t => t.task.IsCompleted || !ReferenceEquals(t.run, RunManager.Instance.DebugOnlyGetState()));
            return Acts.Count > 0;
        }
    }

    public static void Initialize() => new Harmony("sts2_agent.navigation").Patch(
        AccessTools.Method(typeof(RunManager), nameof(RunManager.EnterNextAct)),
        postfix: new HarmonyMethod(typeof(NavigationTasks), nameof(Started)));

    private static void Started(Task __result)
    {
        if (!__result.IsCompleted) Acts.Add((RunManager.Instance.DebugOnlyGetState(), __result));
    }
}
