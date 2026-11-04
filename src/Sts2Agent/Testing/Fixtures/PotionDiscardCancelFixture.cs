using HarmonyLib;
using MegaCrit.Sts2.Core.GameActions;

namespace Sts2Agent;

internal static class PotionDiscardCancelFixture
{
    private const string Owner = "sts2_agent.test_potion_discard_cancel";
    private static ulong? playerId;

    public static void Arm(ulong ownerId)
    {
        Reset();
        playerId = ownerId;
        new Harmony(Owner).Patch(AccessTools.Method(typeof(DiscardPotionGameAction), "ExecuteAction"),
            prefix: new HarmonyMethod(typeof(PotionDiscardCancelFixture), nameof(Execute)));
    }

    private static bool Execute(DiscardPotionGameAction __instance, ref Task __result)
    {
        if (playerId != __instance.OwnerId) return true;
        playerId = null;
        // Cancel after execution starts so the native finally block completes queue cleanup.
        __instance.Cancel();
        __result = Task.CompletedTask;
        return false;
    }

    public static void Reset()
    {
        playerId = null;
        new Harmony(Owner).UnpatchAll(Owner);
    }
}
