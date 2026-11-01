using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal sealed class CombatEntryCapture(Player player, Func<CardModel, int> cardId) : IDisposable
{
    private readonly Player player = player;
    private readonly Func<CardModel, int> cardId = cardId;
    private static CombatEntryCapture? active;
    private CombatState? combat;
    private TurnJournal? journal;
    public static CombatEntryCapture? Current => active;
    public bool Capturing => journal != null;

    public static void Initialize() => new Harmony("sts2_agent.combat_entry").Patch(
        AccessTools.Method(typeof(CombatManager), nameof(CombatManager.StartCombatInternal)),
        prefix: new HarmonyMethod(typeof(CombatEntryCapture), nameof(Starting)));

    public static CombatEntryCapture Begin(Player player, Func<CardModel, int> cardId)
    {
        if (active != null) throw new InvalidOperationException("A combat entry is already being observed.");
        return active = new(player, cardId);
    }

    private static void Starting()
    {
        if (active is not { journal: null } capture || CombatManager.Instance.DebugOnlyGetState() is not { } state) return;
        // The native combat UI now exists; attach before BeforeCombatStart and automatic first-turn effects.
        capture.combat = state;
        capture.journal = new TurnJournal(state, capture.player, capture.cardId);
    }

    public string? StopReason(bool ready) => journal?.StopReason(
        ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()), ready, requireTurnStarted: false);

    public object Result(string reason) => journal?.Result(reason) ?? new {
        stop_reason = reason, complete = reason is not ("timeout" or "interrupted"), events = Array.Empty<object>() };

    public void Flush() => journal?.Flush();

    public void Dispose()
    {
        journal?.Dispose();
        if (ReferenceEquals(active, this)) active = null;
    }
}
