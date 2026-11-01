using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Orbs;

namespace Sts2Agent;

internal static class OrbCapture
{
    private static ulong renderedFrames;
    internal static ulong FrameNumber => DisplayServer.GetName() == "headless" ? Engine.GetProcessFrames() : renderedFrames;

    public static void Initialize()
    {
        // Process-frame numbers can remain unchanged through the post-draw signal.
        RenderingServer.FramePostDraw += Rendered;
        var harmony = new Harmony("sts2_agent.orb_events");
        foreach (var (method, after) in new[] {
            (nameof(NOrbManager.AddOrbAnim), nameof(Channeled)),
            (nameof(NOrbManager.EvokeOrbAnim), nameof(Removed)),
            (nameof(NOrbManager.AddSlotAnim), nameof(SlotsChanged)),
            (nameof(NOrbManager.RemoveSlotAnim), nameof(SlotsChanged)) })
            harmony.Patch(AccessTools.Method(typeof(NOrbManager), method),
                prefix: new HarmonyMethod(typeof(OrbCapture), nameof(Before)),
                postfix: new HarmonyMethod(typeof(OrbCapture), after));
        harmony.Patch(AccessTools.Method(typeof(OrbCmd), "Evoke"),
            prefix: new HarmonyMethod(typeof(OrbCapture), nameof(Evoking)));
    }

    private static void Rendered() => renderedFrames++;

    private static void Before(NOrbManager __instance, out OrbJournal.Change? __state)
        => __state = NGame.IsMainThread() ? OrbJournal.Current?.Before(__instance) : null;
    private static void Channeled(OrbJournal.Change? __state)
    {
        if (__state != null) __state.Journal.Channeled(__state);
    }
    private static void Removed(OrbJournal.Change? __state)
    {
        if (__state != null) __state.Journal.Removed(__state);
    }
    private static void SlotsChanged(OrbJournal.Change? __state)
    {
        if (__state != null) __state.Journal.SlotsChanged(__state);
    }
    private static void Evoking(Player __1, OrbModel __2)
    {
        if (NGame.IsMainThread()) OrbJournal.Current?.Evoking(__1, __2);
    }
}
