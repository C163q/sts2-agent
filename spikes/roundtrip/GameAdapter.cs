using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class GameAdapter(bool testMode)
{
    private readonly string session = Guid.NewGuid().ToString("N");
    private int combatGeneration;
    private CombatState? lastCombat;

    private static Player? LocalPlayer => LocalContext.GetMe(CombatManager.Instance.DebugOnlyGetState());

    private static bool CanEndTurn()
    {
        CombatManager combat = CombatManager.Instance;
        Player? player = LocalPlayer;
        NCombatRoom? room = NCombatRoom.Instance;
        return RunManager.Instance.IsInProgress
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer
            && combat.IsInProgress && !combat.IsPaused && !combat.IsOverOrEnding
            && !combat.PlayerActionsDisabled
            && player?.PlayerCombatState?.Phase == PlayerTurnPhase.Play
            && player.Creature.IsAlive && !combat.IsPlayerReadyToEndTurn(player)
            && (combat.PlayersTakingExtraTurn.Count == 0 || combat.PlayersTakingExtraTurn.Contains(player))
            && room?.Ui?.Hand != null && !room.Ui.Hand.InCardPlay
            && room.Ui.Hand.CurrentMode == NPlayerHand.Mode.Play;
    }

    public string Observe()
    {
        if (!NGame.IsMainThread())
            throw new InvalidOperationException("Game access requires the main thread.");
        CombatState? combat = CombatManager.Instance.DebugOnlyGetState();
        if (!ReferenceEquals(combat, lastCombat))
        {
            lastCombat = combat;
            combatGeneration++;
        }
        Player? player = LocalPlayer;
        PlayerCombatState? state = player?.PlayerCombatState;
        string scene = CombatManager.Instance.IsInProgress ? "combat"
            : NGame.Instance?.MainMenu != null ? "main_menu" : "loading_or_noncombat";
        List<string> actions = [];
        if (CanEndTurn())
            actions.Add("end_turn");
        if (testMode && scene == "main_menu" && !RunManager.Instance.IsInProgress)
            actions.Add("start_test_combat");
        string body = JsonSerializer.Serialize(new
        {
            session, combat_generation = combatGeneration, scene,
            round = combat?.RoundNumber, turn = state?.TurnNumber,
            phase = state?.Phase.ToString(), side = combat?.CurrentSide.ToString(),
            player = player == null ? null : new
            {
                character = player.Character.Id.Entry, hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp, block = player.Creature.Block,
                energy = state?.Energy,
                hand = state?.Hand.Cards.Select(card => card.Id.Entry).ToArray(),
                draw_count = state?.DrawPile.Cards.Count,
                discard_count = state?.DiscardPile.Cards.Count
            },
            enemies = combat?.Enemies.Select(EnemyObservation).ToArray(),
            available_actions = actions
        });
        string snapshotId = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(body)));
        return "{\"snapshot_id\":\"" + snapshotId + "\"," + body[1..];
    }

    private static object EnemyObservation(Creature enemy) => new
    {
        id = enemy.CombatId, model = enemy.ModelId.Entry,
        hp = enemy.CurrentHp, block = enemy.Block
    };

    public async Task<string> Execute(Request request)
    {
        string before = Observe();
        if (request.Operation == "get_state")
            return Success(request.Id, before);
        using JsonDocument document = JsonDocument.Parse(before);
        if (request.ExpectedState != document.RootElement.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before submitting an action.");
        if (!document.RootElement.GetProperty("available_actions").EnumerateArray()
                .Any(action => action.GetString() == request.Operation))
            return FileMailbox.Error(request.Id, "illegal_action", "Action is not available in this state.");

        if (request.Operation == "start_test_combat")
        {
            // Fixture setup is explicitly gated and is not a gameplay tool.
            NGame game = NGame.Instance!;
            await game.StartNewSingleplayerRun(ModelDb.Character<Ironclad>(), false,
                ModelDb.ActsByIndex.Select(acts => acts[0]).ToArray(),
                Array.Empty<ModifierModel>(), "STS2AGENTROUNDTRIP", GameMode.Standard);
            await RunManager.Instance.EnterRoomDebug(RoomType.Monster,
                model: ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: false);
            await WaitUntil(CanEndTurn);
        }
        else if (request.Operation == "end_turn")
        {
            Player player = LocalPlayer!;
            int turn = player.PlayerCombatState!.TurnNumber;
            CombatState combat = CombatManager.Instance.DebugOnlyGetState()!;
            RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new EndPlayerTurnAction(player, turn));
            await WaitUntil(() => !CombatManager.Instance.IsInProgress
                || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
                || (player.PlayerCombatState!.TurnNumber > turn && CanEndTurn()));
        }
        return Success(request.Id, Observe());
    }

    private static async Task WaitUntil(Func<bool> condition)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(25);
        while (!condition())
        {
            if (DateTime.UtcNow >= deadline)
                throw new TimeoutException("Action was submitted but did not settle; do not retry automatically.");
            NGame game = NGame.Instance!;
            await game.ToSignal(game.GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }

    private static string Success(string id, string state) =>
        "{\"id\":\"" + id + "\",\"ok\":true,\"state\":" + state + "}";
}
