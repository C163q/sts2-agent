using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
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
using MegaCrit.Sts2.Core.Saves;

namespace Sts2Agent;

internal sealed class GameAdapter(bool testMode)
{
    private readonly string session = Guid.NewGuid().ToString("N");
    private int combatGeneration;
    private CombatState? lastCombat;
    private readonly CombatObservation observation = new();

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
        observation.Synchronize(combat, player);
        string scene = CombatManager.Instance.IsInProgress ? "combat"
            : NGame.Instance?.MainMenu != null ? "main_menu" : "loading_or_noncombat";
        List<string> actions = [];
        if (CanEndTurn())
            actions.Add("end_turn");
        if (testMode && scene == "main_menu" && !RunManager.Instance.IsInProgress)
            actions.Add("start_test_combat");
        string visibility = scene == "combat" ? CombatObservation.Status() : "not_applicable";
        if (scene == "combat" && visibility != "visible")
            actions.Clear();
        string body = JsonSerializer.Serialize(new
        {
            schema_version = 3, language = "en", session, combat_generation = combatGeneration, scene,
            screen = new { status = visibility },
            turn = scene == "combat" ? observation.Turn() : null,
            player = scene == "combat" ? observation.Player(player) : null,
            enemies = scene == "combat" ? observation.Enemies() : null,
            top_bar = scene == "combat" ? observation.TopBar() : null,
            buttons = scene == "combat" ? observation.Buttons() : null,
            available_actions = actions
        });
        string snapshotId = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(body)));
        return "{\"snapshot_id\":\"" + snapshotId + "\"," + body[1..];
    }

    public async Task<string> Execute(Request request)
    {
        string before = Observe();
        if (request.Operation == "get_state")
        {
            string? capture = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_CAPTURE");
            if (testMode && capture != null && DisplayServer.GetName() != "headless")
                TestCapture.Save(capture);
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_CHECKS");
            if (testMode && checks != null)
                ObservationChecks.Run(checks);
            return Success(request.Id, before);
        }
        using JsonDocument document = JsonDocument.Parse(before);
        if (request.ExpectedState != document.RootElement.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before submitting an action.");
        if (!document.RootElement.GetProperty("available_actions").EnumerateArray()
                .Any(action => action.GetString() == request.Operation))
            return FileMailbox.Error(request.Id, "illegal_action", "Action is not available in this state.");

        if (request.Operation == "start_test_combat")
        {
            // Fixture setup is explicitly gated and is not a gameplay tool.
            SaveManager.Instance.SetFtuesEnabled(false);
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
        return Success(request.Id, await SettledObservation());
    }

    private async Task<string> SettledObservation()
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(2);
        DateTime stableSince = DateTime.UtcNow;
        string previous = Observe();
        while (DateTime.UtcNow < deadline)
        {
            await ObservationFrame();
            string current = Observe();
            if (current != previous)
                stableSince = DateTime.UtcNow;
            else if (DateTime.UtcNow - stableSince >= TimeSpan.FromMilliseconds(250))
                return current;
            previous = current;
        }
        return previous;
    }

    private static async Task ObservationFrame()
    {
        if (DisplayServer.GetName() == "headless")
        {
            await NGame.Instance!.ToSignal(NGame.Instance.GetTree(), SceneTree.SignalName.ProcessFrame);
            return;
        }
        var completion = new TaskCompletionSource();
        void Completed()
        {
            RenderingServer.FramePostDraw -= Completed;
            completion.SetResult();
        }
        RenderingServer.FramePostDraw += Completed;
        await completion.Task;
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
