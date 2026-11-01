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
        string scene = ending != null ? "run_result" : epilogue != null ? "epilogue" : CombatManager.Instance.IsInProgress ? "combat"
            : RewardInspection.Current != null ? "rewards"
            : RestSiteInspection.Current != null ? "rest_site"
            : TreasureInspection.Current != null ? "treasure"
            : AncientInspection.Current != null ? "ancient"
            : ShopInspection.Current != null ? "shop"
            : EventInspection.Current != null ? "event"
            : NGame.Instance?.MainMenu != null ? "main_menu" : "loading_or_noncombat";
        var (actions, visibility) = AvailableTools(scene, map, epilogue, ending, selection);
        if (ending != null) selection = null;
        var screen = CardView.Screen(visibility);
        if (ending != null || epilogue != null && map == null && CardView.Current == null)
            screen["view"] = ending != null ? "run_result" : "epilogue";
        string body = JsonSerializer.Serialize(new
        {
            schema_version = 25, language = "en", session, combat_generation = combatGeneration, ui_generation = uiGeneration, potion_generation = potionGeneration,
            rest_site_generation = restSiteGeneration, treasure_generation = treasureGeneration,
            reward_generation = rewardInspection.Generation, shop_generation = shopInspection.Generation, ancient_generation = ancientInspection.Generation,
            event_generation = eventInspection.Generation,
            confirmation_generation = confirmationGeneration,
            run_result_generation = runResultInspection.Generation, selection_generation = selectionGeneration, map_generation = mapGeneration, scene, map,
            screen,
            turn = scene == "combat" ? observation.Turn() : null,
            player = scene == "combat" ? observation.Player(player) : null,
            enemies = scene == "combat" ? observation.Enemies() : null,
            allies = scene == "combat" ? observation.Allies() : null,
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
        if (request.Operation is "configure_test_run" or "reset_test_run" or "get_test_session")
            return await TestRunRequest(request);
        string before = Observe();
        if (request.Operation is not ("inspect_deck" or "inspect_pile" or "select_card" or "selection_option" or "set_selection_view" or "inspect_targets" or "play_card" or "use_potion" or "discard_potion" or "claim_reward" or "choose_rest_option" or "loot_treasure" or "buy_item" or "choose_ancient_option" or "choose_event_option" or "set_divination_tool" or "divine" or "respond_to_confirmation" or "travel_to_node" or "run_result_option")
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
        if (request.Operation == "check_test_permanent_cards" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } permanentPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await PermanentCardChecks.Run(permanentPlayer, Frame, observation.CardId)));
        }
        if (request.Operation == "check_test_combat_handoff" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } handoffPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await CombatHandoffChecks.Run(handoffPlayer, observation, Frame, Observe)));
        }
        if (request.Operation == "check_test_death_notifications" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } deathPlayer)
            return Success(request.Id, JsonSerializer.Serialize(await DeathNotificationChecks.Run(deathPlayer, observation.CardId)));
        if (request.Operation == "check_test_orb_events" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } orbEventPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await OrbEventChecks.Run(orbEventPlayer, Frame, observation.CardId)));
        }
        if (request.Operation == "check_test_companions" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } companionPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await CompanionChecks.Run(companionPlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation == "check_test_blades" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } bladePlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await SovereignBladeChecks.Run(bladePlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation == "check_test_orb_visibility" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } orbPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await OrbVisibilityChecks.Run(orbPlayer, Frame, Observe)));
        }
        if (request.Operation == "check_test_capacity" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } capacityPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request.Id, JsonSerializer.Serialize(await CapacityChecks.Run(capacityPlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation is "check_test_combat_resources" or "check_test_star_reveal" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } combatResourcePlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            var checks = request.Operation == "check_test_star_reveal"
                ? await CombatResourceChecks.FirstReveal(combatResourcePlayer, Frame, observation.CardId)
                : await CombatResourceChecks.Run(combatResourcePlayer, Frame, observation.CardId);
            return Success(request.Id, JsonSerializer.Serialize(checks));
        }
        if (request.Operation == "check_test_inventory" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } inventoryPlayer)
            return Success(request.Id, JsonSerializer.Serialize(await RunInventoryChecks.Run(inventoryPlayer, ObservationFrame, observation.CardId)));
        if (request.Operation == "check_test_resources" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } resourcePlayer)
            return Success(request.Id, JsonSerializer.Serialize(await RunResourceChecks.Run(resourcePlayer, ObservationFrame)));
        if (request.Operation == "check_test_resource_masks" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "deck" && LocalPlayer is { } maskedPlayer)
            return Success(request.Id, JsonSerializer.Serialize(await RunResourceChecks.Covered(maskedPlayer, ObservationFrame)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_ENDING_SCENARIO") != null
            && request.Operation is "external_back_test_result" or "reopen_test_timeline" or "close_test_timeline")
        {
            if (request.Operation == "reopen_test_timeline")
                NGame.Instance!.MainMenu!.SubmenuStack.PushSubmenuType<MegaCrit.Sts2.Core.Nodes.Screens.Timeline.NTimelineScreen>();
            else if (request.Operation == "external_back_test_result")
                NGame.Instance!.MainMenu!.SubmenuStack.Peek()!.GetNode<NButton>("BackButton").ForceClick();
            else NGame.Instance!.MainMenu!.SubmenuStack.Peek()!.GetNode<NButton>("BackButton").ForceClick();
            for (int i = 0; i < 100; i++) await ObservationFrame();
            return Success(request.Id, await SettledObservation());
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
        if (testMode && testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == "enchantments"
            && request.Operation == "check_test_enchantments")
            return Success(request.Id, JsonSerializer.Serialize(EnchantmentObservationChecks.Run()));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_TURN_SCENARIO") == "thieving_hopper"
            && request.Operation == "capture_test_power_tips")
            return Success(request.Id, JsonSerializer.Serialize(await PowerTextChecks.CaptureHopper(ObservationFrame)));
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && request.Operation == "capture_test_gas_bomb_intent")
            return Success(request.Id, JsonSerializer.Serialize(await IntentTextChecks.CaptureGasBomb(ObservationFrame)));
        if (request.Operation == "respond_to_confirmation")
            return await ConfirmationRequest(request, document.RootElement);
        if (testMode && testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") != null && LocalPlayer != null)
        {
            if (testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") == "trial")
            {
                if (request.Operation == "check_test_confirmation")
                    return Success(request.Id, JsonSerializer.Serialize(ConfirmationFixture.Read()));
                if (request.Operation is "open_test_unowned_confirmation" or "cancel_test_confirmation" or "reopen_test_confirmation")
                {
                    if (request.Operation == "open_test_unowned_confirmation") ConfirmationFixture.OpenUnowned();
                    else if (request.Operation == "cancel_test_confirmation") ConfirmationFixture.Cancel();
                    else ConfirmationFixture.Reopen();
                    await WaitUntil(() => !EventConfirmation.BackdropAnimating
                        && (EventConfirmation.Current is not { } popup || EventConfirmation.Ready(popup)));
                    return Success(request.Id, await SettledObservation());
                }
            }
            if (request.Operation == "check_test_divination" && DivinationInspection.Current != null)
                return Success(request.Id, JsonSerializer.Serialize(DivinationFixture.Read(LocalPlayer)));
            if (request.Operation == "check_test_event") return Success(request.Id, JsonSerializer.Serialize(EventFixture.Read(LocalPlayer)));
            if (request.Operation == "check_test_event_english") return Success(request.Id, JsonSerializer.Serialize(EventTextChecks.Run(
                testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") == "tea")));
            if (request.Operation == "prepare_test_event_victory")
            {
                await EventFixture.PrepareVictory(LocalPlayer);
                return Success(request.Id, await SettledObservation());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_ANCIENT_SCENARIO") is { } ancientScenario && LocalPlayer != null)
        {
            if (request.Operation == "check_test_ancient") return Success(request.Id, JsonSerializer.Serialize(AncientFixture.Read(LocalPlayer)));
            if (request.Operation == "start_test_ancient_combat")
            {
                await AncientFixture.EnterCombat(ancientScenario, LocalPlayer, ObservationFrame);
                return Success(request.Id, await SettledObservation());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_NAVIGATION_SCENARIO") != null && LocalPlayer != null)
        {
            if (request.Operation == "check_test_navigation")
                return Success(request.Id, JsonSerializer.Serialize(NavigationFixture.Read(LocalPlayer)));
            if (request.Operation == "finish_test_navigation_boss")
            {
                await NavigationFixture.FinishBoss(ObservationFrame);
                return Success(request.Id, await SettledObservation());
            }
            if (request.Operation is "set_test_navigation_drawing" or "clear_test_navigation_drawing")
            {
                NRun.Instance!.GlobalUi.MapScreen.Drawings.SetDrawingModeLocal(request.Operation.StartsWith("set_")
                    ? MegaCrit.Sts2.Core.Nodes.Screens.Map.DrawingMode.Drawing : MegaCrit.Sts2.Core.Nodes.Screens.Map.DrawingMode.None);
                return Success(request.Id, Observe());
            }
            if (request.Operation == "scroll_test_navigation")
            {
                using var scroll = new InputEventPanGesture { Delta = new Vector2(0, -30) };
                NRun.Instance!.GlobalUi.MapScreen.Call("ProcessScrollEvent", scroll);
                for (int i = 0; i < 30; i++) await ObservationFrame();
                return Success(request.Id, Observe());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_SHOP_SCENARIO") == "targeting"
            && request.Operation == "cancel_test_shop_targeting")
        {
            await ShopFixture.CancelTargeting();
            return Success(request.Id, Observe());
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_SHOP_SCENARIO") != null
            && request.Operation == "check_test_shop" && LocalPlayer != null)
            return Success(request.Id, JsonSerializer.Serialize(ShopFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_TREASURE_SCENARIO") != null
            && request.Operation == "check_test_treasure" && LocalPlayer != null)
            return Success(request.Id, JsonSerializer.Serialize(TreasureFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_REST_SCENARIO") != null
            && request.Operation == "check_test_rest_site" && LocalPlayer != null)
            return Success(request.Id, JsonSerializer.Serialize(RestSiteFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_REWARD_SCENARIO") != null
            && request.Operation == "check_test_rewards" && LocalPlayer != null)
            return Success(request.Id, JsonSerializer.Serialize(RewardFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_POTION_SCENARIO") != null && LocalPlayer != null)
        {
            if (request.Operation == "check_test_potion_state")
                return Success(request.Id, JsonSerializer.Serialize(PotionFixture.Read(LocalPlayer)));
            if (request.Operation == "replace_test_potion")
            {
                await PotionFixture.Replace(LocalPlayer);
                return Success(request.Id, Observe());
            }
        }
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
        if (request.Operation == "check_test_play_state" && testMode
            && testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") != null && LocalPlayer != null)
            return Success(request.Id, JsonSerializer.Serialize(PlayFixture.Read(LocalPlayer)));
        if (request.Operation is "inspect_targets" or "play_card")
            return await CardPlayRequest(request, document.RootElement);
        if (request.Operation == "check_test_selection_race" && testMode
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "scroll_race")
            return Success(request.Id, JsonSerializer.Serialize(await SelectionFixture.CheckScrollRace(ObservationFrame)));
        if (request.Operation is "inspect_selection" or "set_selection_view" or "select_card" or "selection_option")
            return await SelectionRequest(request, document.RootElement);
        if (request.Operation == "check_test_deck_lifecycle" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") is { } deckChecks)
            return Success(request.Id, JsonSerializer.Serialize(await DeckInspectionChecks.Lifecycle(this, deckChecks)));
        if (request.Operation == "check_test_card_views" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") is { } cardChecks)
            return Success(request.Id, JsonSerializer.Serialize(await DeckInspectionChecks.CardViews(this, cardChecks)));
        if (request.Operation == "check_test_piles" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_PILE_CHECKS") is { } pileChecks)
            return Success(request.Id, JsonSerializer.Serialize(await PileInspectionChecks.Run(this, pileChecks)));
        if (request.Operation == "check_test_map" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_MAP_CHECKS") is { } mapChecks)
            return Success(request.Id, JsonSerializer.Serialize(await MapInspectionChecks.Run(this, mapChecks)));
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
        {
            var inspectedPlayer = LocalPlayer;
            if (inspectedPlayer == null || !CanInspectCombatants())
                return FileMailbox.Error(request.Id, "illegal_action", "Combatant details are unavailable in the current screen.");
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_COMBATANT_CHECKS");
            if (testMode && checks != null)
                CombatantInspectionChecks.Run(checks, inspectedPlayer);
            var inspection = CombatantInspection.Read(inspectedPlayer, observation.CardId);
            return Success(request.Id, JsonSerializer.Serialize(new
            {
                snapshot_id = document.RootElement.GetProperty("snapshot_id").GetString(),
                inspection.scene, inspection.player, inspection.enemies, inspection.allies, inspection.hover_tips
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
            if (hand == null || !CanInspectHand())
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
            await game.StartNewSingleplayerRun(testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") switch
                {
                    "companions_osty" or "companions_first" => ModelDb.Character<Necrobinder>(),
                    "companions_blade" => ModelDb.Character<Regent>(),
                    "orbs" or "orb_chain" => ModelDb.Character<Defect>(),
                    _ => ModelDb.Character<Ironclad>()
                },
                testSettings.Get("STS2_AGENT_TEST_ENDING_SCENARIO") != null,
                ModelDb.ActsByIndex.Select(acts => acts[0]).ToArray(),
                Array.Empty<ModifierModel>(), "STS2AGENTROUNDTRIP", GameMode.Standard);
            string? turnScenario = testSettings.Get("STS2_AGENT_TEST_TURN_SCENARIO");
            string? selectionScenario = testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO");
            string? playScenario = testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO");
            if (playScenario == "companions_first")
                await RelicCmd.Remove(LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState())!
                    .Relics.OfType<BoundPhylactery>().Single());
            if (selectionScenario == "paradox")
                await RelicCmd.Obtain<ChoicesParadox>(LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState())!);
            Task roomEntry = RunManager.Instance.EnterRoomDebug(RoomType.Monster,
                model: selectionScenario == "knowledge" ? ModelDb.Encounter<KnowledgeDemonBoss>().ToMutable()
                    : playScenario is "test_subject" or "no_target" or "random_empty" ? ModelDb.Encounter<TestSubjectBoss>().ToMutable()
                    : turnScenario == "revive" ? ModelDb.Encounter<DecimillipedeElite>().ToMutable()
                    : turnScenario == "thieving_hopper" ? ModelDb.Encounter<ThievingHopperWeak>().ToMutable()
                    : playScenario?.StartsWith("minion_", StringComparison.Ordinal) == true ? ModelDb.Encounter<TheObscuraNormal>().ToMutable()
                    : playScenario?.StartsWith("fog_", StringComparison.Ordinal) == true ? ModelDb.Encounter<LivingFogNormal>().ToMutable()
                    : ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: false);
            if (selectionScenario == "paradox")
            {
                SelectionFixture.Pending = roomEntry;
                await WaitUntil(() => roomEntry.IsFaulted || CardSelection.Current is { Status: "visible" });
                if (roomEntry.IsFaulted) await roomEntry;
            }
            else
            {
                await roomEntry;
                await WaitUntil(() => CanEndTurn());
            }
            if (selectionScenario != null)
            {
                // Debug entry bypasses map travel's normal disable step.
                RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
                NRun.Instance!.GlobalUi.MapScreen.SetTravelEnabled(false);
                await SelectionFixture.Configure(selectionScenario, LocalPlayer!);
                if (selectionScenario is not ("tyranny" or "retain_zero" or "retain_one" or "retain_death" or "retain_victory"))
                {
                    await WaitUntil(() => SelectionFixture.Pending?.IsFaulted == true || CardSelection.Current is { Status: "visible" });
                    if (SelectionFixture.Pending?.IsFaulted == true) await SelectionFixture.Pending;
                }
            }
            if (turnScenario != null) await TurnFixture.Configure(turnScenario, LocalPlayer!);
            if (playScenario != null) await PlayFixture.Configure(playScenario, LocalPlayer!);
            if (testSettings.Get("STS2_AGENT_TEST_POTION_SCENARIO") is { } potionScenario)
                await PotionFixture.Configure(potionScenario, LocalPlayer!);
            if (testSettings.Get("STS2_AGENT_TEST_REWARD_SCENARIO") is { } rewardScenario)
                await RewardFixture.Configure(rewardScenario, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_SHOP_SCENARIO") is { } shopScenario)
                await ShopFixture.Configure(shopScenario, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_TREASURE_SCENARIO") is { } treasureScenario)
                await TreasureFixture.Configure(treasureScenario, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_REST_SCENARIO") is { } restScenario)
                await RestSiteFixture.Configure(restScenario, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_ANCIENT_SCENARIO") is { } ancientScenarioName)
                await AncientFixture.Configure(ancientScenarioName, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") is { } eventScenarioName)
                await EventFixture.Configure(eventScenarioName, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_ENDING_SCENARIO") is { } endingScenario)
                await EndingFixture.Configure(endingScenario, LocalPlayer!, ObservationFrame);
            if (testSettings.Get("STS2_AGENT_TEST_NAVIGATION_SCENARIO") is { } navigationScenario)
                await NavigationFixture.Configure(navigationScenario, LocalPlayer!, ObservationFrame);
            // Debug room entry bypasses the normal map-travel disabling step.
            if (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_MAP_CHECKS") != null)
            {
                var run = RunManager.Instance.DebugOnlyGetState()!;
                run.AddVisitedMapCoord(run.Map.StartingMapPoint.coord);
                run.ActFloor = 1;
                NRun.Instance!.GlobalUi.MapScreen.InitMarker(run.Map.StartingMapPoint.coord);
                NRun.Instance!.GlobalUi.MapScreen.SetTravelEnabled(false);
            }
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
                await PowerCmd.Apply<EscapeArtistPower>(choices, enemies[0], 5, enemies[0], null);
            }
        }
        else if (request.Operation == "end_turn")
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
            return Success(request.Id, JsonSerializer.Serialize(MapInspection.Read(map, run,
                snapshot.RootElement.GetProperty("snapshot_id").GetString()!)));
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
        var inspection = deckInspection.Read(screen, player, options.DetailLevel,
            snapshot.RootElement.GetProperty("snapshot_id").GetString()!);
        string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS");
        if (testMode && checks != null)
            DeckInspectionChecks.Run(checks, screen, player, deckInspection, inspection, options.DetailLevel);
        return Success(request.Id, JsonSerializer.Serialize(inspection));
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
                return Success(request.Id, JsonSerializer.Serialize(PileInspection.Result(options, "unavailable",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!, visible
                        ? "The pile button is disabled." : "The pile button is not visible.", null,
                    visible ? "entry_disabled" : "entry_not_visible")));
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
                return Success(request.Id, JsonSerializer.Serialize(PileInspection.Result(options, "empty",
                    snapshot.RootElement.GetProperty("snapshot_id").GetString()!,
                    EnglishCardText.Read(() => EnglishCardText.Plain(emptyTip.GetFormattedText())), Array.Empty<object>())));
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
