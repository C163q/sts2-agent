using HarmonyLib;
using MegaCrit.Sts2.Core.GameActions;

namespace Sts2Agent;

internal static class PotionDiscardFaultFixture
{
    private const string Owner = "sts2_agent.test_potion_discard_fault";
    private static ulong? playerId;

    public static void Arm(ulong ownerId)
    {
        Reset();
        playerId = ownerId;
        new Harmony(Owner).Patch(AccessTools.Method(typeof(DiscardPotionGameAction), "ExecuteAction"),
            postfix: new HarmonyMethod(typeof(PotionDiscardFaultFixture), nameof(AfterExecute)));
    }

    private static void AfterExecute(DiscardPotionGameAction __instance, ref Task __result)
    {
        if (playerId != __instance.OwnerId) return;
        playerId = null;
        __result = FailAfter(__result);
    }

    private static async Task FailAfter(Task original)
    {
        await original;
        throw new InvalidOperationException("Injected failure after the native potion discard.");
    }

    public static void Reset()
    {
        playerId = null;
        new Harmony(Owner).UnpatchAll(Owner);
    }
}
