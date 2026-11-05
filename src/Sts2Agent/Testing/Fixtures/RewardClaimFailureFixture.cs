using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace Sts2Agent;

internal static class RewardClaimFailureFixture
{
    private const string Owner = "sts2_agent.test_reward_scroll_failure";
    private static NRewardsScreen? screen;
    private static NRewardButton? disabled;
    private static Vector2 target;
    private static Vector2 position;
    private static bool armed;

    public static void Arm(NRewardsScreen current)
    {
        Reset();
        screen = current;
        target = (Vector2)AccessTools.Field(typeof(NRewardsScreen), "_targetDragPos").GetValue(current)!;
        position = current.GetNode<Control>("%RewardsContainer").Position;
        armed = true;
        new Harmony(Owner).Patch(AccessTools.Method(typeof(NRewardsScreen), "UpdateScrollPosition"),
            postfix: new HarmonyMethod(typeof(RewardClaimFailureFixture), nameof(Scrolled)));
    }

    private static void Scrolled(NRewardsScreen __instance)
    {
        if (!armed || !ReferenceEquals(screen, __instance)
            || target == (Vector2)AccessTools.Field(typeof(NRewardsScreen), "_targetDragPos").GetValue(__instance)!) return;
        armed = false;
        disabled = RewardInspection.Buttons(__instance).First();
        disabled.Disable();
    }

    public static void Reset()
    {
        armed = false;
        new Harmony(Owner).UnpatchAll(Owner);
        if (screen != null && GodotObject.IsInstanceValid(screen) && ReferenceEquals(screen, RewardInspection.Current))
        {
            if (disabled != null && GodotObject.IsInstanceValid(disabled)) disabled.Enable();
            AccessTools.Field(typeof(NRewardsScreen), "_targetDragPos").SetValue(screen, target);
            screen.GetNode<Control>("%RewardsContainer").Position = position;
        }
        screen = null;
        disabled = null;
    }
}
