using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;

namespace Sts2Agent;

internal sealed class GameAdapter(bool testMode)
{
    private readonly string session = Guid.NewGuid().ToString("N");
    private int combatGeneration;
    private int uiGeneration;
    private CombatState? lastCombat;
    private readonly CombatObservation observation = new();
    private readonly DeckInspection deckInspection = new();

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
            schema_version = 3, language = "en", session, combat_generation = combatGeneration, ui_generation = uiGeneration, scene,
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
        if (request.Operation != "inspect_deck" && request.Arguments is { } arguments && arguments.EnumerateObject().Any())
            return FileMailbox.Error(request.Id, "invalid_request", "This operation does not accept arguments.");
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
        if (request.Operation == "check_test_deck_lifecycle" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") is { } deckChecks)
            return Success(request.Id, JsonSerializer.Serialize(await DeckInspectionChecks.Lifecycle(this, deckChecks)));
        if (request.Operation == "inspect_deck")
        {
            DeckOptions options;
            try { options = DeckOptions.Parse(request.Arguments); }
            catch (Exception error) when (error is JsonException or InvalidOperationException)
            {
                return FileMailbox.Error(request.Id, "invalid_request", "Invalid deck options.");
            }
            return await InspectDeck(request, options);
        }
        if (request.Operation == "close_deck")
        {
            var screen = DeckView.Current;
            if (screen == null || !DeckView.CanClose(screen))
                return FileMailbox.Error(request.Id, "illegal_action", "The current deck screen cannot be closed.");
            uiGeneration++;
            DeckView.Close(screen);
            return Success(request.Id, await SettledObservation());
        }
        if (request.Operation == "inspect_relics")
        {
            var holders = RelicInspection.VisibleHolders();
            if (holders == null)
                return FileMailbox.Error(request.Id, "illegal_action", "Relic details are unavailable in the current screen.");
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_RELIC_CHECKS");
            if (testMode && checks != null)
                RelicInspectionChecks.Run(checks);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                relics = RelicInspection.Read(holders)
            }));
        }
        if (request.Operation == "inspect_combatants")
        {
            if (CombatObservation.Status() != "visible" || LocalPlayer == null || NCombatRoom.Instance!.Ui.Hand.InCardPlay)
                return FileMailbox.Error(request.Id, "illegal_action", "Combatant details are unavailable in the current screen.");
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_COMBATANT_CHECKS");
            if (testMode && checks != null)
                CombatantInspectionChecks.Run(checks, LocalPlayer);
            var inspection = CombatantInspection.Read(LocalPlayer);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                inspection.scene, inspection.player, inspection.enemies, inspection.hover_tips
            }));
        }
        if (request.Operation == "inspect_potions")
        {
            var holders = PotionInspection.VisibleHolders();
            if (holders == null)
                return FileMailbox.Error(request.Id, "illegal_action", "Potion details are unavailable in the current screen.");
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_POTION_CHECKS");
            if (testMode && checks != null)
                PotionInspectionChecks.Run(checks);
            var inspection = PotionInspection.Read(holders);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                inspection.slot_tip, inspection.potion_slots
            }));
        }
        if (request.Operation == "inspect_ui")
        {
            if (CombatObservation.Status() != "visible")
                return FileMailbox.Error(request.Id, "illegal_action", "UI details are unavailable in the current screen.");
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_UI_CHECKS");
            if (testMode && checks != null)
                UiInspectionChecks.Run(checks);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                scene = "combat", hover_tips = UiInspection.Read()
            }));
        }
        if (request.Operation == "inspect_hand")
        {
            var hand = NCombatRoom.Instance?.Ui.Hand;
            if (CombatObservation.Status() != "visible" || hand == null || !VisibleUi.Shown(hand) || hand.InCardPlay)
                return FileMailbox.Error(request.Id, "illegal_action", "Hand details are unavailable in the current screen.");
            string? handChecks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_HAND_CHECKS");
            if (testMode && handChecks != null)
                HandInspectionChecks.Run(handChecks);
            var reader = new HandInspection(observation);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                hand = hand.ActiveHolders.Where(holder => VisibleUi.Shown(holder)
                    && CombatObservation.CardVisible(holder.CardNode)).Select(holder => reader.Card(holder.CardNode!)).ToArray()
            }));
        }
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
            if (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") != null)
            {
                var player = LocalPlayer!;
                for (int index = 0; index < 16; index++)
                    await CardPileCmd.Add(player.RunState.CreateCard<BodySlam>(player), PileType.Deck, skipVisuals: true);
                await CardPileCmd.Add(player.RunState.CreateCard<AscendersBane>(player), PileType.Deck, skipVisuals: true);
                var upgraded = player.RunState.CreateCard<BodySlam>(player);
                upgraded.UpgradeInternal();
                upgraded.FinalizeUpgradeInternal();
                await CardPileCmd.Add(upgraded, PileType.Deck, skipVisuals: true);
                // Fixture additions have no acquisition animation to emit the completion event.
                PileType.Deck.GetPile(player).InvokeCardAddFinished();
                await WaitUntil(() => VisibleUi.Number(NRun.Instance!.GlobalUi.TopBar.Deck, "DeckCardCount")
                    == PileType.Deck.GetPile(player).Cards.Count);
            }
            if (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_RELIC_CHECKS") != null)
            {
                await RelicCmd.Obtain<Anchor>(LocalPlayer!);
                await RelicCmd.Obtain<Lantern>(LocalPlayer!);
                await RelicCmd.Obtain<PenNib>(LocalPlayer!);
            }
            if (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_POTION_CHECKS") != null)
            {
                await PotionCmd.TryToProcure<SkillPotion>(LocalPlayer!);
                await PotionCmd.TryToProcure<BlockPotion>(LocalPlayer!);
                await PotionCmd.TryToProcure<BlockPotion>(LocalPlayer!);
            }
            if (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_COMBATANT_CHECKS") != null)
            {
                var player = LocalPlayer!.Creature;
                var enemies = CombatManager.Instance.DebugOnlyGetState()!.Enemies.ToArray();
                var choices = new ThrowingPlayerChoiceContext();
                await PowerCmd.Apply<StrengthPower>(choices, player, 2, player, null);
                await PowerCmd.Apply<VulnerablePower>(choices, player, 2, player, null);
                await PowerCmd.Apply<VulnerablePower>(choices, enemies, 2, player, null);
                await PowerCmd.Apply<ShrinkPower>(choices, player, -1, enemies[0], null);
            }
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

    private async Task<string> InspectDeck(Request request, DeckOptions options)
    {
        var player = LocalPlayer;
        if (player == null || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer || !CombatManager.Instance.IsInProgress)
            return FileMailbox.Error(request.Id, "illegal_action", "Deck viewing requires a single-player combat.");
        var screen = DeckView.Current;
        if (screen == null)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Deck;
            if (CombatObservation.Status() != "visible" || !CanEndTurn() || !VisibleUi.OnScreen(button) || !button.IsEnabled)
                return FileMailbox.Error(request.Id, "illegal_action", "The deck button is unavailable.");
            uiGeneration++;
            button.ForceClick();
            screen = NCapstoneContainer.Instance?.CurrentCapstoneScreen as NDeckViewScreen;
            if (screen == null)
                return FileMailbox.Error(request.Id, "illegal_action", "The deck screen did not open.");
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(DeckView.Current, screen) || DeckView.Ready(screen));
        if (!ReferenceEquals(DeckView.Current, screen))
            return FileMailbox.Error(request.Id, "illegal_action", "The deck screen changed while opening.");
        if (options.ViewUpgrades.HasValue || options.SortBy != null)
            uiGeneration++;
        try { DeckView.Apply(screen, options); }
        catch (InvalidOperationException)
        {
            return FileMailbox.Error(request.Id, "illegal_action", "The deck controls are unavailable.");
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(DeckView.Current, screen) || DeckView.Ready(screen));
        if (!ReferenceEquals(DeckView.Current, screen) || !ReferenceEquals(LocalPlayer, player))
            return FileMailbox.Error(request.Id, "illegal_action", "The deck screen changed while reading.");
        using var snapshot = JsonDocument.Parse(Observe());
        var inspection = deckInspection.Read(screen, player, options.DetailLevel,
            snapshot.RootElement.GetProperty("snapshot_id").GetString()!);
        string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS");
        if (testMode && checks != null)
            DeckInspectionChecks.Run(checks, screen, player, deckInspection, inspection, options.DetailLevel);
        return Success(request.Id, JsonSerializer.Serialize(inspection));
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
