using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;
using STS2RitsuLib;

namespace Sts2Agent;

internal sealed class ManualPlayBatch : IDisposable, ILifecycleObserver
{
    internal sealed class Item(CardPlayInput input, CardModel card, Creature? target)
    {
        public CardPlayInput Input { get; } = input;
        public CardModel Card { get; } = card;
        public Creature? Target { get; } = target;
        public CardPlayProgress Progress { get; } = new();
        public PlayCardAction? Action;
        public string? Rejection;
        public Action<GameAction>? Began, Canceled, Finished;
    }

    private readonly Player player;
    private readonly CombatState combat;
    private readonly ActionQueueSet queue;
    private readonly int turn;
    private readonly Action? submitted;
    private readonly string id = Guid.NewGuid().ToString("N");
    private readonly IDisposable lifecycle;
    private Item? submitting;
    private bool disposed;
    public Item[] Items { get; }
    public bool SubmissionUncertain { get; private set; }
    public bool SameRun => ReferenceEquals(player.RunState, RunManager.Instance.DebugOnlyGetState());
    public bool SameContext => SameRun && ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
        && player.PlayerCombatState?.TurnNumber == turn;
    public bool Pending { get { Sample(); return Items.Any(i => i.Progress.Pending); } }
    public bool Uncertain { get { Sample(); return Items.Any(i => i.Progress.Status == "unknown"); } }
    public bool Faulted => Items.Any(i => i.Action?.Exception != null);

    public ManualPlayBatch(Player player, Item[] items, Action? submitted)
    {
        this.player = player;
        this.submitted = submitted;
        Items = items;
        combat = CombatManager.Instance.DebugOnlyGetState()!;
        queue = RunManager.Instance.ActionQueueSet;
        turn = player.PlayerCombatState!.TurnNumber;
        lifecycle = RitsuLibFramework.SubscribeLifecycle(this, replayCurrentState: false);
        queue.ActionEnqueued += Enqueued;
    }

    public bool Submit(Item item)
    {
        submitting = item;
        try
        {
            if (!item.Card.TryManualPlay(item.Target))
            {
                item.Rejection = TargetInspection.Reason(item.Card, TargetInspection.Targets(item.Card))
                    ?? "The game rejected this card play before submission.";
                return false;
            }
            if (item.Action == null)
            {
                // A true return can also defer an action; it is not enqueue evidence.
                item.Progress.Submit(); item.Progress.Abandon();
                SubmissionUncertain = true;
                return true;
            }
            if (NCombatRoom.Instance is { } room)
            {
                if (item.Target != null) room.LastTargetedCreature = item.Target;
                else if (item.Card.TargetType is TargetType.AllEnemies or TargetType.AllAllies)
                    room.LastTargetedCreature = null;
            }
            return true;
        }
        finally { submitting = null; }
    }

    private void Enqueued(GameAction action)
    {
        if (submitting is not { Action: null } item || action is not PlayCardAction play || play.Player != player
            || !ReferenceEquals(play.NetCombatCard.ToCardModelOrNull(), item.Card)) return;
        item.Action = play;
        item.Progress.Submit();
        submitted?.Invoke();
        item.Began = _ => item.Progress.Begin();
        item.Canceled = _ => item.Progress.Cancel();
        item.Finished = _ => item.Progress.Finish(play.Exception != null);
        play.BeforeExecuted += item.Began;
        play.BeforeCancelled += item.Canceled;
        play.AfterFinished += item.Finished;
    }

    public void OnEvent(IFrameworkLifecycleEvent evt)
    {
        if (disposed || evt is not CardPlayingEvent e || !ReferenceEquals(e.CombatState, combat)
            || e.CardPlay.IsAutoPlay) return;
        var item = Items.FirstOrDefault(i => ReferenceEquals(i.Card, e.CardPlay.Card)
            && ReferenceEquals(i.Action, RunManager.Instance.ActionExecutor.CurrentlyRunningAction));
        item?.Progress.Play(CombatObservation.Status() == "visible");
    }

    private void Sample()
    {
        foreach (var item in Items)
        {
            if (item.Action?.State == GameActionState.Canceled) item.Progress.Cancel();
            if (item.Action?.State == GameActionState.Finished) item.Progress.Finish(item.Action.Exception != null);
            if (!SameContext) item.Progress.Abandon();
        }
    }

    public void StopRemaining(string reason)
    {
        foreach (var item in Items.Where(i => i.Action == null && i.Rejection == null
            && i.Progress.Status == "not_submitted")) item.Rejection = reason;
    }

    public object Read()
    {
        Sample();
        return new { batch_id = id, results = Items.Select((item, index) => new {
            index, card_id = item.Input.CardId, target_id = item.Input.TargetId,
            status = item.Progress.Status,
            reason = item.Progress.Status switch {
                "not_submitted" => item.Rejection ?? "Submission stopped before this card.",
                "not_played" => item.Progress.Canceled ? "The native card play was canceled."
                    : "The native action ended without playing this card.",
                "unknown" => "The card play result could not be confirmed.",
                _ => (string?)null }
        }).ToArray() };
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        queue.ActionEnqueued -= Enqueued;
        lifecycle.Dispose();
        foreach (var item in Items)
            if (item.Action is { } action)
            {
                action.BeforeExecuted -= item.Began;
                action.BeforeCancelled -= item.Canceled;
                action.AfterFinished -= item.Finished;
            }
    }
}
