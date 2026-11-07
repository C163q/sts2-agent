using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline;

namespace Sts2Agent;

internal static class ResultOptionFixture
{
    private const string Owner = "sts2_agent.test_result_scroll";
    private static NSlotsContainer? armed;
    private static NEpochSlot? target;
    private static Vector2 position;
    private static bool enabled;

    public static object Arm(RunResultInspection results)
    {
        Reset();
        if (results.Current is not { Root: NTimelineScreen timeline } context || !results.Ready(context))
            throw new InvalidOperationException("An active result timeline is required.");
        var option = results.Options(context).First(o => o.button is NEpochSlot && RunResultInspection.Clickable(o.button));
        target = (NEpochSlot)option.button;
        position = target.Position;
        enabled = target.IsEnabled;
        target.Position += new Vector2(10000, 0);
        armed = timeline.GetNode<NSlotsContainer>("%SlotsContainer");
        new Harmony(Owner).Patch(AccessTools.Method(typeof(NSlotsContainer), nameof(NSlotsContainer.LerpToSlot)),
            postfix: new HarmonyMethod(typeof(ResultOptionFixture), nameof(Scrolling)));
        return new { option_id = option.id };
    }

    private static void Scrolling(NSlotsContainer __instance)
    {
        if (!ReferenceEquals(armed, __instance)) return;
        armed = null;
        target!.Disable();
    }

    public static object Reset()
    {
        armed = null;
        new Harmony(Owner).UnpatchAll(Owner);
        if (GodotObject.IsInstanceValid(target))
        {
            target!.Position = position;
            target.SetEnabled(enabled);
        }
        target = null;
        return new { reset = true };
    }
}
