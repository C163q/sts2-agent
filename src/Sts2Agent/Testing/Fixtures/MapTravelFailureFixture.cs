using HarmonyLib;
using Godot;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;

namespace Sts2Agent;

internal static class MapTravelFailureFixture
{
    private const string Owner = "sts2_agent.test_map_scroll_failure";
    private static NMapScreen? armed;
    private static NMapScreen? restore;
    private static bool wasEnabled;

    public static void Arm(NMapScreen screen)
    {
        Reset();
        armed = screen;
        restore = screen;
        wasEnabled = screen.IsTravelEnabled;
        new Harmony(Owner).Patch(AccessTools.Method(typeof(NMapScreen), "ProcessScrollEvent"),
            postfix: new HarmonyMethod(typeof(MapTravelFailureFixture), nameof(Scrolled)));
    }

    private static void Scrolled(NMapScreen __instance)
    {
        if (!ReferenceEquals(armed, __instance)) return;
        armed = null;
        __instance.SetTravelEnabled(false);
    }

    public static void Reset()
    {
        armed = null;
        new Harmony(Owner).UnpatchAll(Owner);
        if (restore != null && GodotObject.IsInstanceValid(restore) && ReferenceEquals(restore, NMapScreen.Instance))
            restore.SetTravelEnabled(wasEnabled);
        restore = null;
    }
}
