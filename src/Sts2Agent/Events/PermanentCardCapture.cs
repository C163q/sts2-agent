using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class PermanentCardCapture
{
    internal sealed record Change(CardModel Card, string Type, decimal Before);
    private sealed record EnchantmentChange(CardModel? Suppressed, EnchantmentModel? Before);
    [ThreadStatic] private static Dictionary<CardModel, int>? suppressed;

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.permanent_card_values");
        void Property(Type type, string name, string before, string after) => harmony.Patch(
            AccessTools.PropertySetter(type, name), prefix: new HarmonyMethod(typeof(PermanentCardCapture), before),
            postfix: new HarmonyMethod(typeof(PermanentCardCapture), after));
        Property(typeof(DynamicVar), nameof(DynamicVar.BaseValue), nameof(BeforeValue), nameof(AfterValue));
        Property(typeof(EnchantmentModel), nameof(EnchantmentModel.Amount), nameof(BeforeAmount), nameof(AfterAmount));
        harmony.Patch(AccessTools.Method(typeof(CardEnergyCost), nameof(CardEnergyCost.SetCustomBaseCost)),
            prefix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(BeforeCost)),
            postfix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(AfterCost)));
        foreach (string method in new[] { nameof(CardModel.UpgradeInternal), nameof(CardModel.FinalizeUpgradeInternal),
                nameof(CardModel.DowngradeInternal) })
            harmony.Patch(AccessTools.Method(typeof(CardModel), method),
                prefix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(BeforeCard)),
                finalizer: new HarmonyMethod(typeof(PermanentCardCapture), nameof(Restore)));
        foreach (string method in new[] { nameof(CardModel.EnchantInternal), nameof(CardModel.ClearEnchantmentInternal) })
            harmony.Patch(AccessTools.Method(typeof(CardModel), method),
                prefix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(BeforeEnchantment)),
                postfix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(AfterEnchantment)),
                finalizer: new HarmonyMethod(typeof(PermanentCardCapture), nameof(RestoreEnchantment)));
        harmony.Patch(AccessTools.Method(typeof(CardCmd), nameof(CardCmd.Enchant), [typeof(EnchantmentModel), typeof(CardModel), typeof(decimal)]),
            prefix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(BeforeEnchant)),
            finalizer: new HarmonyMethod(typeof(PermanentCardCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(EnchantmentModel), nameof(EnchantmentModel.ModifyCard)),
            prefix: new HarmonyMethod(typeof(PermanentCardCapture), nameof(BeforeModify)),
            finalizer: new HarmonyMethod(typeof(PermanentCardCapture), nameof(Restore)));
    }

    private static bool Tracking(CardModel? card) => NGame.IsMainThread() && card != null
        && suppressed?.ContainsKey(card) != true && RunInventoryJournal.Current?.TracksPermanent(card) == true;

    private static void BeforeValue(DynamicVar __instance, out Change? __state)
    {
        __state = null;
        if (RunInventoryJournal.Current == null || !NGame.IsMainThread()) return;
        var owner = PrivateFields.Read(__instance, "_owner");
        CardModel? card = owner as CardModel;
        string type = "card_stats_changed";
        if (owner is EnchantmentModel { IsMutable: true, HasCard: true } enchantment)
        { card = enchantment.Card; type = "card_enchantment_changed"; }
        if (Tracking(card)) __state = new(card!, type, __instance.BaseValue);
    }

    private static void AfterValue(DynamicVar __instance, Change? __state) => Changed(__state, __instance.BaseValue);
    private static void BeforeAmount(EnchantmentModel __instance, out Change? __state)
    {
        __state = __instance is { IsMutable: true, HasCard: true } && Tracking(__instance.Card)
            ? new(__instance.Card, "card_enchantment_changed", __instance.Amount) : null;
    }
    private static void AfterAmount(EnchantmentModel __instance, Change? __state) => Changed(__state, __instance.Amount);
    private static void BeforeCost(CardEnergyCost __instance, out Change? __state)
    {
        __state = null;
        if (RunInventoryJournal.Current == null || !NGame.IsMainThread()) return;
        if (PrivateFields.Read(__instance, "_card") is CardModel card && Tracking(card))
            __state = new(card, "card_energy_cost_changed", __instance.GetWithModifiers(CostModifiers.None));
    }
    private static void AfterCost(CardEnergyCost __instance, Change? __state) =>
        Changed(__state, __instance.GetWithModifiers(CostModifiers.None));
    private static void Changed(Change? change, decimal after)
    {
        if (change != null && change.Before != after)
            RunInventoryJournal.Current?.NumericChanged(change.Card, change.Type);
    }

    private static void Enter(CardModel? card, out CardModel? state)
    {
        state = null;
        if (RunInventoryJournal.Current == null || card == null || !NGame.IsMainThread()) return;
        suppressed ??= [];
        suppressed[card] = suppressed.GetValueOrDefault(card) + 1;
        state = card;
    }
    private static void BeforeCard(CardModel __instance, out CardModel? __state) => Enter(__instance, out __state);
    private static void BeforeEnchantment(CardModel __instance, out EnchantmentChange __state)
    {
        Enter(__instance, out var card);
        __state = new(card, __instance.Enchantment);
    }
    private static void AfterEnchantment(CardModel __instance, EnchantmentChange __state)
    {
        // DeepCloneFields fires copied callbacks before AfterCloned clears their subscriptions.
        if (__state.Suppressed != null && !ReferenceEquals(__state.Before, __instance.Enchantment))
            RunInventoryJournal.Current?.EnchantmentChanged(__instance);
    }
    private static void RestoreEnchantment(EnchantmentChange __state) => Restore(__state.Suppressed);
    private static void BeforeEnchant(CardModel __1, out CardModel? __state) => Enter(__1, out __state);
    private static void BeforeModify(EnchantmentModel __instance, out CardModel? __state) =>
        Enter(__instance is { IsMutable: true, HasCard: true } ? __instance.Card : null, out __state);
    private static void Restore(CardModel? __state)
    {
        if (__state == null || suppressed == null) return;
        if (--suppressed[__state] == 0) suppressed.Remove(__state);
    }
}
