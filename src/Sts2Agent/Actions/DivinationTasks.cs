using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;

namespace Sts2Agent;

internal static class DivinationTasks
{
    private sealed class State { public Task? Click; public LocString? Dialogue; }
    private static readonly ConditionalWeakTable<object, State> States = new();

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.divination");
        harmony.Patch(AccessTools.Method(typeof(NCrystalSphereScreen), "OnCellClicked"),
            postfix: new HarmonyMethod(typeof(DivinationTasks), nameof(Clicked)));
        harmony.Patch(AccessTools.Method(typeof(NCrystalSphereDialogue), "Play"),
            postfix: new HarmonyMethod(typeof(DivinationTasks), nameof(Spoken)));
    }

    private static void Clicked(NCrystalSphereScreen __instance, Task __result) => States.GetOrCreateValue(__instance).Click = __result;
    private static void Spoken(NCrystalSphereDialogue __instance, LocString __0) => States.GetOrCreateValue(__instance).Dialogue = __0;
    public static bool Pending(NCrystalSphereScreen screen) => States.TryGetValue(screen, out var state) && state.Click is { IsCompleted: false };
    public static LocString? Dialogue(NCrystalSphereDialogue dialogue) => States.TryGetValue(dialogue, out var state) ? state.Dialogue : null;
}
