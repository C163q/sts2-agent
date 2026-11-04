using HarmonyLib;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal static class CardPlayRejectionFixture
{
    private const string Owner = "sts2_agent.test_card_rejection";
    private static CardModel? blocked;

    public static void Arm(CardModel card)
    {
        Reset();
        blocked = card;
        new Harmony(Owner).Patch(AccessTools.Method(typeof(CardModel), nameof(CardModel.TryManualPlay)),
            prefix: new HarmonyMethod(typeof(CardPlayRejectionFixture), nameof(TryPlay)));
    }

    private static bool TryPlay(CardModel __instance, ref bool __result)
    {
        if (!ReferenceEquals(__instance, blocked)) return true;
        blocked = null;
        __result = false;
        return false;
    }

    public static void Reset()
    {
        blocked = null;
        new Harmony(Owner).UnpatchAll(Owner);
    }
}
