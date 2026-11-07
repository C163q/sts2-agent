using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic;

namespace Sts2Agent;

internal static class PresentationMotion
{
    private static readonly ConditionalWeakTable<Node, List<Tween>> Tweens = new();
    public static void Initialize() => new Harmony("sts2_agent.run_result_motion").Patch(
        AccessTools.Method(typeof(Node), nameof(Node.CreateTween)),
        postfix: new HarmonyMethod(typeof(PresentationMotion), nameof(Created)));
    private static void Created(Node __instance, Tween __result)
    {
        if (__instance is NGameOverScreen or NTreasureRoomRelicCollection) Tweens.GetValue(__instance, _ => []).Add(__result);
    }
    public static bool Pending(Node screen)
    {
        if (!Tweens.TryGetValue(screen, out var values)) return false;
        values.RemoveAll(t => !GodotObject.IsInstanceValid(t) || !t.IsValid() || !t.IsRunning());
        return values.Count > 0;
    }
}
