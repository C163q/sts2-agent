using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class CombatHandoffFixture
{
    public static Task? Pending { get; private set; }
    private static Action? unsubscribe;

    public static void Configure(Player player, bool endTurn = false)
    {
        Reset();
        if (endTurn)
        {
            var initial = CombatManager.Instance.DebugOnlyGetState();
            void Started(CombatState state)
            {
                if (ReferenceEquals(initial, state) && player.PlayerCombatState!.TurnNumber > 1) Trigger();
            }
            CombatManager.Instance.TurnStarted += Started;
            unsubscribe = () => CombatManager.Instance.TurnStarted -= Started;
        }
        else
        {
            PlayCardAction? submitted = null;
            void Enqueued(GameAction action)
            {
                if (action is PlayCardAction play && play.Player == player) submitted ??= play;
            }
            void Blocked(int _, int __) => Trigger(submitted);
            RunManager.Instance.ActionQueueSet.ActionEnqueued += Enqueued;
            player.Creature.BlockChanged += Blocked;
            unsubscribe = () =>
            {
                player.Creature.BlockChanged -= Blocked;
                RunManager.Instance.ActionQueueSet.ActionEnqueued -= Enqueued;
            };
        }
    }

    private static void Trigger(GameAction? submitted = null)
    {
        unsubscribe?.Invoke();
        unsubscribe = null;
        Pending = Replace(submitted);
    }

    private static async Task Replace(GameAction? submitted)
    {
        var manager = RunManager.Instance;
        var run = manager.DebugOnlyGetState();
        // The executor can pause for a choice before the submitted action has finished.
        while (submitted != null && submitted.State is not (GameActionState.Finished or GameActionState.Canceled))
        {
            if (!ReferenceEquals(run, manager.DebugOnlyGetState())) throw new OperationCanceledException();
            await Cmd.Wait(0.05f);
        }
        await manager.ActionExecutor.FinishedExecutingActions();
        await manager.EnterRoomDebug(RoomType.Monster, model: ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: true);
    }

    public static void Reset()
    {
        unsubscribe?.Invoke();
        unsubscribe = null;
        Pending = null;
    }
}
