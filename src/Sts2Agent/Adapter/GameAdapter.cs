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
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;

namespace Sts2Agent;

internal sealed partial class GameAdapter(bool testMode)
{
    private readonly string session = Guid.NewGuid().ToString("N");
    private int combatGeneration;
    private int uiGeneration;
    private CombatState? lastCombat;
    private readonly CombatObservation observation = new();
    private readonly DeckInspection deckInspection = new();
    private readonly PileInspection pileInspection = new();
    private object? lastSelection;
    private int selectionGeneration;
    private PotionModel?[] lastPotions = [];
    private int potionGeneration;
    private object? lastRestSite;
    private int restSiteGeneration;
    private object? lastTreasure;
    private int treasureGeneration;

    private static Player? LocalPlayer => LocalContext.GetMe(CombatManager.Instance.DebugOnlyGetState())
        ?? LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState());

    private static bool CanEndTurn(bool allowMapPause = false)
    {
        CombatManager combat = CombatManager.Instance;
        Player? player = LocalPlayer;
        NCombatRoom? room = NCombatRoom.Instance;
        return RunManager.Instance.IsInProgress
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer
            && combat.IsInProgress && (!combat.IsPaused || allowMapPause) && !combat.IsOverOrEnding
            && !combat.PlayerActionsDisabled
            && player?.PlayerCombatState?.Phase == PlayerTurnPhase.Play
            && player.Creature.IsAlive && !combat.IsPlayerReadyToEndTurn(player)
            && (combat.PlayersTakingExtraTurn.Count == 0 || combat.PlayersTakingExtraTurn.Contains(player))
            && room?.Ui?.Hand != null && !room.Ui.Hand.InCardPlay
            && room.Ui.Hand.CurrentMode == NPlayerHand.Mode.Play && CardSelection.Current == null;
    }

    private static bool CanInspectViews(bool allowPause = false) => CanEndTurn(allowPause)
        || CardSelection.Current is { Peeking: true, Supported: true } && LocalPlayer?.Creature.IsAlive == true;

    public string Observe()
    {
        if (!NGame.IsMainThread())
            throw new InvalidOperationException("Game access requires the main thread.");
        CombatJournalScope.Current?.SampleVisibility();
        RunResourceJournal.Current?.SampleVisibility();
        RunInventoryJournal.Current?.SampleVisibility();
        PotionJournal.Current?.SampleVisibility();
        CombatResourceJournal.Current?.SampleVisibility();
        OrbJournal.Current?.SampleVisibility();
        TurnCapture.Journal?.SampleVisibility();
        CombatState? combat = CombatManager.Instance.DebugOnlyGetState();
        if (!ReferenceEquals(combat, lastCombat))
        {
            lastCombat = combat;
            combatGeneration++;
        }
        Player? player = LocalPlayer;
        var potions = player?.PotionSlots.ToArray() ?? [];
        if (!potions.SequenceEqual(lastPotions, ReferenceEqualityComparer.Instance))
        {
            lastPotions = potions;
            potionGeneration++;
        }
        observation.Synchronize(combat, player);
        rewardInspection.Synchronize();
        shopInspection.Synchronize();
        ancientInspection.Synchronize();
        eventInspection.Synchronize();
        var confirmation = MegaCrit.Sts2.Core.Nodes.CommonUi.NModalContainer.Instance?.OpenModal;
        if (!ReferenceEquals(confirmation, lastConfirmation))
        {
            lastConfirmation = confirmation;
            confirmationGeneration++;
        }
        if (!ReferenceEquals(RestSiteInspection.Current, lastRestSite))
        {
            lastRestSite = RestSiteInspection.Current;
            restSiteGeneration++;
        }
        if (!ReferenceEquals(TreasureInspection.Current, lastTreasure))
        {
            lastTreasure = TreasureInspection.Current;
            treasureGeneration++;
        }
        var run = RunManager.Instance.DebugOnlyGetState();
        if (!ReferenceEquals(run, lastRun) || !ReferenceEquals(run?.Map, lastMap))
        {
            lastRun = run; lastMap = run?.Map; mapGeneration++;
        }
        runResultInspection.Synchronize();
        var ending = runResultInspection.Current;
        var epilogue = EpilogueInspection.Current;
        var map = ending == null ? MapInspection.Summary(run) : null;
        var selection = CardSelection.Current;
        if (!ReferenceEquals(selection?.Key, lastSelection))
        {
            lastSelection = selection?.Key;
            selectionGeneration++;
        }
        string scene = ObservationContext.Scene(ending, epilogue);
        var actions = AvailableTools(scene, map, epilogue, ending, selection);
        string visibility = ObservationContext.Visibility(scene, map, epilogue, ending);
        if (ending != null) selection = null;
        var screen = ObservationContext.Screen(scene, visibility, map != null);
        var combatants = scene == "combat" && CombatObservation.Status() == "visible"
            ? observation.Combatants(player) : null;
        string body = JsonSerializer.Serialize(new
        {
            schema_version = 34, language = "en", session, combat_generation = combatGeneration, ui_generation = uiGeneration, potion_generation = potionGeneration,
            rest_site_generation = restSiteGeneration, treasure_generation = treasureGeneration,
            reward_generation = rewardInspection.Generation, shop_generation = shopInspection.Generation, ancient_generation = ancientInspection.Generation,
            event_generation = eventInspection.Generation,
            confirmation_generation = confirmationGeneration,
            run_result_generation = runResultInspection.Generation, selection_generation = selectionGeneration, map_generation = mapGeneration, scene, map,
            screen,
            turn = scene == "combat" ? observation.Turn() : null,
            player = scene == "combat" ? observation.Player(player, combatants) : null,
            enemies = scene == "combat" ? observation.Enemies(combatants) : null,
            allies = scene == "combat" ? observation.Allies(combatants) : null,
            top_bar = observation.TopBar(),
            buttons = scene == "combat" ? observation.Buttons() : null,
            selection = new SelectionInspection(observation).Read(selection),
            rewards = ending == null ? rewardInspection.Read() : null,
            rest_site = ending == null ? RestSiteInspection.Read() : null,
            treasure = ending == null ? TreasureInspection.Read() : null,
            shop = ending == null ? shopInspection.Read() : null,
            ancient = ending == null ? ancientInspection.Read() : null,
            @event = ending == null ? eventInspection.Read() : null,
            divination = ending == null ? DivinationInspection.Read() : null,
            confirmation = ending == null ? EventConfirmation.Read() : null,
            epilogue = ending == null ? EpilogueInspection.Read() : null,
            run_result = runResultInspection.Read(),
            available_actions = actions
        });
        string permissionState = body;
        if (DivinationInspection.Current != null)
        {
            var logical = System.Text.Json.Nodes.JsonNode.Parse(body)!;
            if (logical["divination"] is System.Text.Json.Nodes.JsonObject sphere) sphere["dialogue"] = null;
            permissionState = logical.ToJsonString();
        }
        string snapshotId = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(permissionState)));
        return "{\"snapshot_id\":\"" + snapshotId + "\"," + body[1..];
    }

    private async Task<string> ExecuteCore(Request request)
    {
        if (await TestRequestBeforeCapture(request) is { } early) return early;
        string before = Observe();
        if (request.Operation is not ("inspect_combatants" or "inspect_deck" or "inspect_pile" or "inspect_selection" or "select_card" or "selection_option" or "set_selection_view" or "inspect_targets" or "play_card" or "use_potion" or "discard_potion" or "claim_reward" or "choose_rest_option" or "loot_treasure" or "buy_item" or "choose_ancient_option" or "choose_event_option" or "set_divination_tool" or "divine" or "respond_to_confirmation" or "travel_to_node" or "run_result_option")
            && request.Arguments is { } arguments && arguments.EnumerateObject().Any())
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
        if (request.Operation == "capture_screenshot")
        {
            if (ViewportCapture.Read() is not { } capture)
                return FileMailbox.Error(request.Id, "screenshot_unavailable", "A rendered game viewport is required.");
            using JsonDocument captured = JsonDocument.Parse(before);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = captured.RootElement.GetProperty("snapshot_id").GetString(),
                capture.width, capture.height, png_base64 = Convert.ToBase64String(capture.png)
            }));
        }
        using JsonDocument document = JsonDocument.Parse(before);
        if (await TestRequestAfterCapture(request, document.RootElement) is { } testResponse) return testResponse;
        if (request.Operation == "respond_to_confirmation")
            return await ConfirmationRequest(request, document.RootElement);
        if (request.Operation is "inspect_run_result" or "run_result_option") return await RunResultRequest(request, document.RootElement);
        if (request.Operation is "advance_dialogue" or "proceed" && EpilogueInspection.Current != null)
            return await EpilogueRequest(request, document.RootElement);
        if (request.Operation == "travel_to_node") return await TravelRequest(request, document.RootElement);
        if (request.Operation is "use_potion" or "discard_potion" || request.Operation == "inspect_targets"
            && request.Arguments is { } targetArguments && targetArguments.TryGetProperty("potion_slot", out _))
            return await PotionRequest(request, document.RootElement);
        if (request.Operation is "inspect_ancient" or "choose_ancient_option" or "advance_dialogue"
            || request.Operation == "proceed" && RewardInspection.Current == null && AncientInspection.Current != null)
            return await AncientRequest(request, document.RootElement);
        if (request.Operation is "set_divination_tool" or "divine"
            || request.Operation is "inspect_event" or "proceed" && RewardInspection.Current == null && DivinationInspection.Current != null)
            return await DivinationRequest(request, document.RootElement);
        if (request.Operation is "inspect_event" or "choose_event_option"
            || request.Operation == "proceed" && RewardInspection.Current == null && EventInspection.Current != null)
            return await EventRequest(request, document.RootElement);
        if (request.Operation is "open_shop" or "close_shop" or "inspect_shop" or "buy_item"
            || request.Operation == "proceed" && RewardInspection.Current == null && ShopInspection.Current != null)
            return await ShopRequest(request, document.RootElement);
        if (request.Operation is "loot_treasure" or "inspect_treasure"
            || request.Operation == "proceed" && RewardInspection.Current == null && TreasureInspection.Current != null)
            return await TreasureRequest(request, document.RootElement);
        if (request.Operation is "inspect_rest_site" or "choose_rest_option"
            || request.Operation == "proceed" && RewardInspection.Current == null && RestSiteInspection.Current != null)
            return await RestSiteRequest(request, document.RootElement);
        if (request.Operation is "inspect_rewards" or "claim_reward" or "proceed")
            return await RewardRequest(request, document.RootElement);
        if (request.Operation is "inspect_targets" or "play_card")
            return await CardPlayRequest(request, document.RootElement);
        if (request.Operation is "inspect_selection" or "set_selection_view" or "select_card" or "selection_option")
            return await SelectionRequest(request, document.RootElement);
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
        if (request.Operation == "inspect_pile")
        {
            PileOptions options;
            try { options = PileOptions.Parse(request.Arguments); }
            catch (Exception error) when (error is JsonException or InvalidOperationException)
            {
                return FileMailbox.Error(request.Id, "invalid_request", "Invalid pile options.");
            }
            return await InspectPile(request, options);
        }
        if (request.Operation == "inspect_map")
            return await InspectMap(request);
        if (request.Operation == "close_map")
        {
            var map = NRun.Instance?.GlobalUi.MapScreen;
            if (map == null || !MapView.CanClose(map))
                return FileMailbox.Error(request.Id, "illegal_action", "The current map cannot be closed.");
            var run = RunManager.Instance.DebugOnlyGetState();
            var graph = run?.Map;
            int? act = run?.CurrentActIndex;
            var underlyingOverlay = NRun.Instance!.GlobalUi.Overlays.Peek();
            bool reopened = false;
            void Opened() => reopened = true;
            uiGeneration++;
            bool SameMap() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
                && ReferenceEquals(graph, run?.Map) && act == run?.CurrentActIndex && GodotObject.IsInstanceValid(map)
                && ReferenceEquals(underlyingOverlay, NRun.Instance?.GlobalUi.Overlays.Peek())
                && ReferenceEquals(NRun.Instance?.GlobalUi.MapScreen, map);
            map.Opened += Opened;
            try
            {
                MapView.Back(map)!.ForceClick();
                await ObservationFrame();
                await WaitUntil(() => !SameMap() || reopened || map.IsOpen || !MapView.Clear() || !VisibleUi.Shown(map));
                if (!SameMap() || reopened || map.IsOpen || !MapView.Clear())
                    return FileMailbox.Error(request.Id, "illegal_action", "The map changed while closing.");
                string after = await SettledObservation();
                if (!SameMap() || reopened || map.IsOpen || !MapView.Clear())
                    return FileMailbox.Error(request.Id, "illegal_action", "The map changed while closing.");
                return Success(request.Id, after);
            }
            finally
            {
                if (GodotObject.IsInstanceValid(map)) map.Opened -= Opened;
            }
        }
        if (request.Operation == "close_card_view")
        {
            var screen = CardView.Current;
            if (screen == null || !CardView.CanClose(screen))
                return FileMailbox.Error(request.Id, "illegal_action", "The current card view cannot be closed.");
            uiGeneration++;
            CardView.Close(screen);
            return Success(request.Id, await SettledObservation());
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
            return CombatantsRequest(request, document.RootElement);
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
            if (!UiInspection.CanRead())
                return FileMailbox.Error(request.Id, "illegal_action", "UI details are unavailable in the current screen.", publicMessage: true);
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_UI_CHECKS");
            if (testMode && checks != null)
                UiInspectionChecks.Run(checks);
            return InspectionSuccess(request.Id, document.RootElement, new { hover_tips = UiInspection.Read() });
        }
        if (request.Operation == "inspect_hand")
        {
            var hand = NCombatRoom.Instance?.Ui.Hand;
            if (hand == null || !CanInspectHand())
                return FileMailbox.Error(request.Id, "illegal_action", "Hand details are unavailable in the current screen.", publicMessage: true);
            string? handChecks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_HAND_CHECKS");
            if (testMode && handChecks != null)
                HandInspectionChecks.Run(handChecks);
            var reader = new HandInspection(observation);
            var resources = CombatResources.Read();
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                energy = resources.Energy, max_energy = resources.Maximum, stars = resources.Stars,
                hand = CombatObservation.HandCards(hand).Select(reader.Card).ToArray()
            }));
        }
        if (request.ExpectedState != document.RootElement.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before submitting an action.");
        if (!document.RootElement.GetProperty("available_actions").EnumerateArray()
                .Any(action => action.GetString() == request.Operation))
            return FileMailbox.Error(request.Id, "illegal_action", "Action is not available in this state.");


        if (request.Operation == "end_turn")
        {
            Player player = LocalPlayer!;
            int turn = player.PlayerCombatState!.TurnNumber;
            if (!STS2RitsuLib.RitsuLibFramework.IsActive)
                return FileMailbox.Error(request.Id, "illegal_action", "RitsuLib is unavailable; no action was submitted.");
            var journal = CombatJournalScope.Current!;
            RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new EndPlayerTurnAction(player, turn));
            var (state, reason) = await ActionObservation(() =>
            {
                return journal.StopReason(player.PlayerCombatState?.TurnNumber > turn && CanEndTurn()
                    && RunManager.Instance.ActionQueueSet.IsEmpty, requireTurnStarted: true);
            });
            return Success(request.Id, state[..^1] + ",\"transition\":" + JsonSerializer.Serialize(journal.Result(reason)) + "}");
        }
        return Success(request.Id, await SettledObservation());
    }

    private async Task<string> InspectMap(Request request)
    {
        var run = RunManager.Instance.DebugOnlyGetState();
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (run == null || map == null || !CanInspectMap())
            return FileMailbox.Error(request.Id, "illegal_action", "Map viewing is unavailable in the current screen.");
        var graph = run.Map;
        int act = run.CurrentActIndex;
        bool cardOpen = MapView.CardPage != null;
        if (!map.IsOpen || cardOpen)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Map;
            if (!button.IsEnabled || !VisibleUi.OnScreen(button)
                || (!map.IsOpen && VisibleUi.Shown(map))
                || (CombatManager.Instance.IsInProgress && !CanInspectViews(allowPause: map.IsOpen || cardOpen)))
                return FileMailbox.Error(request.Id, "illegal_action", "The map button is unavailable.");
            uiGeneration++;
            button.ForceClick();
        }
        bool closed = false;
        void Closed() => closed = true;
        bool SamePage() => !closed && ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(graph, run.Map) && act == run.CurrentActIndex && MapView.Current(map);
        map.Closed += Closed;
        try
        {
            await ObservationFrame();
            await WaitUntil(() => !SamePage() || MapView.Ready(map));
            if (!SamePage() || !MapView.Ready(map))
                return FileMailbox.Error(request.Id, "illegal_action", "The map changed while reading.");
            using var snapshot = JsonDocument.Parse(Observe());
            return InspectionSuccess(request.Id, snapshot.RootElement, MapInspection.Read(map, run,
                snapshot.RootElement.GetProperty("snapshot_id").GetString()!));
        }
        finally
        {
            if (GodotObject.IsInstanceValid(map)) map.Closed -= Closed;
        }
    }

    private async Task<string> InspectDeck(Request request, DeckOptions options)
    {
        var player = LocalPlayer;
        if (player == null || !CanInspectDeck())
            return FileMailbox.Error(request.Id, "illegal_action", "The local deck is unavailable in this screen.");
        var screen = DeckView.Current;
        if (screen == null)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Deck;
            if (!CanInspectDeck())
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
        var inspection = deckInspection.Read(screen, player,
            snapshot.RootElement.GetProperty("snapshot_id").GetString()!);
        string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS");
        if (testMode && checks != null)
            DeckInspectionChecks.Run(checks, screen, player, deckInspection, inspection);
        return InspectionSuccess(request.Id, snapshot.RootElement, inspection);
    }

    private async Task<string> InspectPile(Request request, PileOptions options)
    {
        var player = LocalPlayer;
        var combat = CombatManager.Instance.DebugOnlyGetState();
        bool cardOpen = CardView.Current != null;
        if (!CanInspectPiles())
            return FileMailbox.Error(request.Id, "illegal_action", "Pile viewing is unavailable in the current screen.");
        var screen = PileInspection.Current(options);
        if (screen == null)
        {
            var ui = NCombatRoom.Instance!.Ui;
            NCombatCardPile button = SelectionPileButton(options) ?? (options.Pile switch
                { "draw" => ui.DrawPile, "discard" => ui.DiscardPile, _ => ui.ExhaustPile });
            if (VisibleUi.OnScreen(button) && CardView.Current is { } previous)
            {
                if (!CardView.CanClose(previous))
                    return FileMailbox.Error(request.Id, "illegal_action", "The current card page cannot be replaced.");
                // Native screen context disables combat pile buttons while any card page is open.
                uiGeneration++;
                CardView.Close(previous);
                await ObservationFrame();
                if (CombatObservation.Status() != "visible" || !CanInspectViews() || !ReferenceEquals(player, LocalPlayer)
                    || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()))
                    return FileMailbox.Error(request.Id, "illegal_action", "The screen changed while switching piles.");
            }
            if (!VisibleUi.OnScreen(button) || !button.IsEnabled)
            {
                using var snapshot = JsonDocument.Parse(Observe());
                bool visible = VisibleUi.OnScreen(button);
                return InspectionSuccess(request.Id, snapshot.RootElement, PileInspection.Result(options, "unavailable",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!, visible
                        ? "The pile button is disabled." : "The pile button is not visible.", null,
                    visible ? "entry_disabled" : "entry_not_visible"));
            }
            var emptyTip = PileInspection.EmptyTip(button);
            if (VisibleUi.Number(button, "CountContainer/Count") == 0 && emptyTip == null)
                return FileMailbox.Error(request.Id, "illegal_action", "The empty pile has no native inspection feedback.");
            uiGeneration++;
            button.ForceClick();
            screen = PileInspection.Current(options);
            if (screen == null)
            {
                await ObservationFrame();
                if (!ReferenceEquals(player, LocalPlayer) || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
                    || CombatObservation.Status() != "visible" || VisibleUi.Number(button, "CountContainer/Count") != 0 || emptyTip == null)
                    return FileMailbox.Error(request.Id, "illegal_action", "The pile screen did not open or the screen changed.");
                using var snapshot = JsonDocument.Parse(Observe());
                return InspectionSuccess(request.Id, snapshot.RootElement, PileInspection.Result(options, "empty",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!,
                    EnglishCardText.Read(() => EnglishCardText.Plain(emptyTip.GetFormattedText())), Array.Empty<object>()));
            }
        }
        await ObservationFrame();
        await WaitUntil(() => !ReferenceEquals(PileInspection.Current(options), screen) || CardView.Ready(screen));
        if (!ReferenceEquals(PileInspection.Current(options), screen) || !ReferenceEquals(player, LocalPlayer)
            || !ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
            || CombatObservation.Status(allowCardView: true) != "visible" || !CanInspectViews(allowPause: true))
            return FileMailbox.Error(request.Id, "illegal_action", "The pile screen changed while reading.");
        using var observed = JsonDocument.Parse(Observe());
        var inspection = pileInspection.Read(screen, options, observed.RootElement.GetProperty("snapshot_id").GetString()!);
        return InspectionSuccess(request.Id, observed.RootElement, inspection);
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

    private static string Success(string id, string state)
    {
        using var document = JsonDocument.Parse(state);
        if (document.RootElement.TryGetProperty("divination", out var divination) && divination.ValueKind == JsonValueKind.Object
            && divination.GetProperty("status").GetString() == "visible")
        {
            var screen = DivinationInspection.Current;
            var capture = screen == null ? null : ViewportCapture.Read(DivinationInspection.Bounds(screen));
            if (capture == null) return FileMailbox.Error(id, "screenshot_unavailable", "A rendered divination board image is required.");
            var (width, height, png) = capture.Value;
            state = state[..^1] + ",\"divination_image\":" + JsonSerializer.Serialize(new { width, height, png_base64 = Convert.ToBase64String(png) }) + "}";
        }
        if (CardSelection.Current is { } selection)
            state = state[..^1] + ",\"selection_view\":\"" + selection.Status + "\"}";
        return "{\"id\":\"" + id + "\",\"ok\":true,\"state\":" + state + "}";
    }
}
