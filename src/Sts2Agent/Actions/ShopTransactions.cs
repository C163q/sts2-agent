using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class ShopTransactions
{
    private static readonly List<(IRunState run, Task task)> Tasks = [];
    public static bool Pending
    {
        get
        {
            Tasks.RemoveAll(item => item.task.IsCompleted || !ReferenceEquals(item.run, RunManager.Instance.DebugOnlyGetState()));
            return Tasks.Count > 0;
        }
    }

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.shop_transactions");
        foreach (var method in new[] {
            AccessTools.Method(typeof(MerchantEntry), nameof(MerchantEntry.OnTryPurchaseWrapper)),
            AccessTools.DeclaredMethod(typeof(MerchantCardRemovalEntry), nameof(MerchantCardRemovalEntry.OnTryPurchaseWrapper)),
            AccessTools.Method(typeof(LordsParasol), "PurchaseEverything") })
            harmony.Patch(method, postfix: new HarmonyMethod(typeof(ShopTransactions), nameof(Started)));
    }

    // Native UI and relics run purchases asynchronously; retain the original tasks without replacing them.
    private static void Started(Task __result)
    {
        if (!__result.IsCompleted && RunManager.Instance.DebugOnlyGetState() is { } run) Tasks.Add((run, __result));
    }
}
