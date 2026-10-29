using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Sts2Agent;

internal static class TurnCapture
{
    internal sealed record Origin(AbstractModel? Model, Creature? Dealer, bool IsDamage);
    private static readonly AsyncLocal<Origin?> Context = new();
    [ThreadStatic] private static int hpLossDepth;
    public static TurnJournal? Journal { get; set; }
    public static Origin? Current => Context.Value;
    public static bool CapturingDamageHp => hpLossDepth > 0;

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.turn_capture");
        harmony.Patch(AccessTools.Method(typeof(CreatureCmd), nameof(CreatureCmd.Damage),
            [typeof(PlayerChoiceContext), typeof(IEnumerable<Creature>), typeof(decimal), typeof(ValueProp),
                typeof(Creature), typeof(CardModel)]),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(Damage)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(CardCmd), nameof(CardCmd.AutoPlay)),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(AutoPlay)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(DoomPower), nameof(DoomPower.DoomKill)),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(Doom)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(Creature), nameof(Creature.LoseHpInternal)),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(BeforeHpLoss)),
            postfix: new HarmonyMethod(typeof(TurnCapture), nameof(AfterHpLoss)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(RestoreHpLoss)));
    }

    private static void Damage(PlayerChoiceContext __0, Creature? __4, CardModel? __5, out Origin? __state)
    {
        __state = Context.Value;
        Context.Value = new Origin(__5 ?? __0.LastInvolvedModel, __4, true);
    }

    private static void AutoPlay(PlayerChoiceContext __0, CardModel __1, out Origin? __state)
    {
        __state = Context.Value;
        Journal?.AutoPlaySource(__1, __0.LastInvolvedModel);
        Context.Value = new Origin(__0.LastInvolvedModel, __1.Owner.Creature, false);
    }

    private static void Doom(IReadOnlyList<Creature> __0, out Origin? __state)
    {
        __state = Context.Value;
        Context.Value = new Origin(__0.FirstOrDefault()?.GetPower<DoomPower>(), null, false);
    }

    // Restore the caller immediately; the game's async method captures its own execution context.
    private static void Restore(Origin? __state) => Context.Value = __state;

    private static void BeforeHpLoss(out int __state)
    {
        __state = hpLossDepth;
        if (Current?.IsDamage == true) hpLossDepth++;
    }

    private static void AfterHpLoss(DamageResult __result)
    {
        if (Current?.IsDamage == true) Journal?.Damage(__result, Current);
    }

    private static void RestoreHpLoss(int __state) => hpLossDepth = __state;
}
