using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;

namespace Sts2Agent;

internal static class RunResultMotion
{
    private static readonly ConditionalWeakTable<NGameOverScreen, List<Tween>> Tweens = new();
    public static void Initialize() => new Harmony("sts2_agent.run_result_motion").Patch(
        AccessTools.Method(typeof(Node), nameof(Node.CreateTween)),
        postfix: new HarmonyMethod(typeof(RunResultMotion), nameof(Created)));
    private static void Created(Node __instance, Tween __result)
    {
        if (__instance is NGameOverScreen screen) Tweens.GetValue(screen, _ => []).Add(__result);
    }
    public static bool Pending(NGameOverScreen screen)
    {
        if (!Tweens.TryGetValue(screen, out var values)) return false;
        values.RemoveAll(t => !GodotObject.IsInstanceValid(t) || !t.IsValid() || !t.IsRunning());
        return values.Count > 0;
    }
}
