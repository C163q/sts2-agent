using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class CombatJournalScope : IDisposable
{
    private sealed class RoomChange
    {
        public Task? Task;
        public bool Failed;
    }
    public static CombatJournalScope? Current { get; private set; }
    private readonly Player player;
    private readonly IRunState run;
    private readonly CombatObservation observation;
    private readonly TurnEventBuffer buffer;
    private readonly List<TurnJournal> journals = [];
    private readonly List<RoomChange> rooms = [];
    private CombatState? combat;
    private TurnJournal? journal;
    private TurnEventBuffer.Reservation? marker;
    private ulong markerFrame;
    private bool hadCombat;
    private string? lastReason;
    public bool Capturing => journal != null;
    public bool StartedCombat { get; private set; }
    private bool SameRun => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState());
    public bool Pending
    {
        get
        {
            rooms.RemoveAll(room => room.Failed || room.Task?.IsCompleted == true);
            return SameRun && (rooms.Count > 0 || CombatManager.Instance.IsStarting);
        }
    }

    private CombatJournalScope(Player player, CombatObservation observation)
    {
        this.player = player;
        this.observation = observation;
        run = player.RunState;
        buffer = ActionEventScope.Current!.Buffer;
    }

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.combat_journal_scope");
        harmony.Patch(AccessTools.Method(typeof(CombatManager), nameof(CombatManager.StartCombatInternal)),
            prefix: new HarmonyMethod(typeof(CombatJournalScope), nameof(Starting)));
        harmony.Patch(AccessTools.Method(typeof(CombatManager), nameof(CombatManager.Reset)),
            prefix: new HarmonyMethod(typeof(CombatJournalScope), nameof(Resetting)));
        foreach (string method in new[] { nameof(RunManager.EnterRoom), nameof(RunManager.EnterRoomWithoutExitingCurrentRoom) })
            harmony.Patch(AccessTools.Method(typeof(RunManager), method),
                prefix: new HarmonyMethod(typeof(CombatJournalScope), nameof(Entering)),
                postfix: new HarmonyMethod(typeof(CombatJournalScope), nameof(Entered)),
                finalizer: new HarmonyMethod(typeof(CombatJournalScope), nameof(EnterFailed)));
    }

    public static CombatJournalScope Begin(Player player, CombatObservation observation)
    {
        if (Current != null) throw new InvalidOperationException("Combat journals are already owned by an action.");
        var scope = Current = new CombatJournalScope(player, observation);
        try
        {
            if (CombatManager.Instance.IsInProgress && CombatManager.Instance.DebugOnlyGetState() is { } state)
                scope.Attach(state, starting: false);
            return scope;
        }
        catch { scope.Dispose(); throw; }
    }

    private static void Starting()
    {
        if (NGame.IsMainThread() && Current is { } scope && CombatManager.Instance.DebugOnlyGetState() is { } state)
            scope.Attach(state, starting: true);
    }
    private static void Resetting()
    {
        if (NGame.IsMainThread()) Current?.Detach();
    }
    private static void Entering(out RoomChange? __state)
    {
        __state = null;
        if (!NGame.IsMainThread() || Current is not { SameRun: true } scope) return;
        __state = new();
        scope.rooms.Add(__state);
    }
    private static void Entered(Task __result, RoomChange? __state)
    {
        if (__state != null) __state.Task = __result;
    }
    private static void EnterFailed(Exception? __exception, RoomChange? __state)
    {
        if (__exception != null && __state != null) __state.Failed = true;
    }

    private void Attach(CombatState state, bool starting)
    {
        if (!SameRun || !ReferenceEquals(state.RunState, run) || !state.Players.Contains(player)
            || journal != null && ReferenceEquals(state, combat)) return;
        Detach();
        // Draw callbacks can assign IDs before the next observation synchronizes the new combat.
        observation.Synchronize(state, player);
        combat = state;
        if (hadCombat)
        {
            marker = buffer.Reserve("combat_started");
            markerFrame = VisibleUi.FrameNumber;
        }
        journal = new TurnJournal(state, player, observation.CardId, observation.KnownCardName, observation.RememberCardName);
        journals.Add(journal);
        hadCombat = true;
        lastReason = null;
        StartedCombat |= starting;
    }

    private void Detach()
    {
        SampleVisibility();
        marker = null;
        if (journal == null) return;
        string? reason = journal.StopReason(ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()), false, false);
        lastReason = reason is "combat_won" or "combat_lost" ? reason : "interrupted";
        journal.Flush();
        journal.Dispose();
        journal = null;
        combat = null;
    }

    public void SampleVisibility()
    {
        if (marker == null) return;
        if (!SameRun || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())) { marker = null; return; }
        if (VisibleUi.FrameNumber > markerFrame && CombatObservation.Status() == "visible")
        {
            marker.Publish(new());
            marker = null;
        }
    }

    public string? StopReason(bool ready, bool requireTurnStarted = false)
    {
        SampleVisibility();
        if (!SameRun) return "interrupted";
        if (!hadCombat) return null;
        if (CardSelection.AwaitingInput) return "choice_required";
        if (Pending) return null;
        return journal?.StopReason(ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()), ready,
            requireTurnStarted && !StartedCombat) ?? lastReason;
    }

    public void Flush()
    {
        foreach (var captured in journals) captured.Flush();
    }
    public object Result(string reason)
    {
        Flush();
        return TransitionResult.Create(reason, buffer);
    }
    public void Dispose()
    {
        Flush();
        journal?.Dispose();
        journal = null;
        marker = null;
        rooms.Clear();
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
