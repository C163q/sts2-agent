using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Sts2Agent;

internal static class TurnCapture
{
    internal sealed record Origin(AbstractModel? Model, Creature? Dealer, bool IsDamage)
    {
        public HashSet<Creature> LethalTargets { get; } = [];
        public HashSet<Creature> VisibleBlockTargets { get; } = [];
        public Creature? DeathTarget { get; init; }
        public IReadOnlyList<Creature>? DoomTargets { get; init; }
    }
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
                typeof(Creature), typeof(CardModel), typeof(CardPlay)]),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(Damage)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(CardCmd), nameof(CardCmd.AutoPlay)),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(AutoPlay)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(DoomPower), nameof(DoomPower.DoomKill)),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(Doom)),
            finalizer: new HarmonyMethod(typeof(TurnCapture), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(CreatureCmd), "KillWithoutCheckingWinCondition"),
            prefix: new HarmonyMethod(typeof(TurnCapture), nameof(Kill)),
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
        Journal?.BeforeDamage(Context.Value);
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
        Context.Value = new Origin(__0.FirstOrDefault()?.GetPower<DoomPower>(), null, false) { DoomTargets = __0 };
    }

    private static void Kill(Creature __0, out Origin? __state)
    {
        __state = Context.Value;
        AbstractModel? source = null;
        if (__state?.LethalTargets.Contains(__0) == true || ReferenceEquals(__state?.DeathTarget, __0))
            source = __state!.Model;
        else if (__state?.DoomTargets?.Contains(__0) == true)
            source = __0.GetPower<DoomPower>();
        // Native death cleanup can zero other creatures' HP; it is not another hit by the caller.
        Context.Value = new Origin(source, null, false) { DeathTarget = __0 };
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
        if (Current is not { IsDamage: true } origin) return;
        if (__result.WasTargetKilled) origin.LethalTargets.Add(__result.Receiver);
        Journal?.Damage(__result, origin);
    }

    private static void RestoreHpLoss(int __state) => hpLossDepth = __state;
}
