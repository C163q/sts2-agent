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

internal sealed partial class GameAdapter
{
    private async Task<string?> TestRequestBeforeCapture(Request request)
    {
        if (request.Operation == "arm_test_card_rejection" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            var inputs = CardPlayOptions.Parse(request.Arguments, false);
            if (inputs[0].TargetId.HasValue || !CanPlayCards()
                || new TargetInspection(observation).FindCard(inputs[0].CardId) is not { } card)
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a current test hand card ID.");
            CardPlayRejectionFixture.Arm(card);
            return Success(request, JsonSerializer.Serialize(new { armed = true }));
        }
        if (request.Operation == "check_test_play_queue" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (LocalPlayer is not { } player || !CanPlayCards() || request.Arguments is not { } args
                || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("mode", out var mode)
                || mode.ValueKind != JsonValueKind.String || !PlayQueueChecks.Modes.Contains(mode.GetString()))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a native queue probe mode in a ready test combat.");
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await PlayQueueChecks.Run(mode.GetString()!, player, observation, Frame, Observe)));
        }
        if (request.Operation is "configure_test_run" or "reset_test_run" or "get_test_session")
            return await TestRunRequest(request);
        if (request.Operation == "set_test_potion_display" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Arguments is not { } options || options.EnumerateObject().Any(p => p.Name is not ("mode" or "index"))
                || !options.TryGetProperty("mode", out var mode) || mode.ValueKind != JsonValueKind.String
                || mode.GetString() is not ("normal" or "no_hover" or "disabled" or "hidden" or "offscreen"))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a potion display test mode.");
            int index = 0;
            if (options.TryGetProperty("index", out var supplied) && (supplied.ValueKind != JsonValueKind.Number || !supplied.TryGetInt32(out index) || index < 0))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a nonnegative test slot index.");
            return Success(request, JsonSerializer.Serialize(PotionDisplayFixture.Set(mode.GetString()!, index)));
        }
        if (request.Operation == "set_test_relic_display" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Arguments is not { } options
                || options.EnumerateObject().Any(property => property.Name is not ("mode" or "index"))
                || !options.TryGetProperty("mode", out var mode) || mode.ValueKind != JsonValueKind.String
                || mode.GetString() is not ("normal" or "grayed" or "pulsing" or "both" or "unknown_tint" or "no_shader" or "hidden_inventory" or "hidden_top_bar"))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a relic display fixture mode.");
            int index = 0;
            if (options.TryGetProperty("index", out var supplied) && (supplied.ValueKind != JsonValueKind.Number || !supplied.TryGetInt32(out index) || index < 0))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected a nonnegative test relic index.");
            return Success(request, JsonSerializer.Serialize(RelicDisplayFixture.Set(mode.GetString()!, index)));
        }
        if (request.Operation == "set_test_relic_hover" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Arguments is not { } options || options.EnumerateObject().Count() != 1
                || !options.TryGetProperty("enabled", out var flag) || flag.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected test enabled flag.");
            return Success(request, JsonSerializer.Serialize(RelicHoverFixture.SetEnabled(flag.GetBoolean())));
        }
        if (request.Operation == "set_test_combatant_hover" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Arguments is not { } testArguments
                || testArguments.EnumerateObject().Count() != 1
                || !testArguments.TryGetProperty("enabled", out var enabled)
                || enabled.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected the test enabled flag.");
            return Success(request, JsonSerializer.Serialize(CombatantHoverChecks.SetEnabled(enabled.GetBoolean())));
        }
        return null;
    }

    private async Task<string?> TestRequestAfterCapture(Request request, JsonElement before)
    {
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Operation == "check_test_end_turn")
                return Success(request, JsonSerializer.Serialize(TurnTransitionChecks.EndTurn(EndTurnUnavailableReason, Observe)));
            if (request.Operation == "check_test_card_movements" && LocalPlayer is { } movementPlayer)
            {
                async Task Frame() { await ObservationFrame(); Observe(); }
                return Success(request, JsonSerializer.Serialize(await TurnTransitionChecks.Movements(movementPlayer, observation, Frame)));
            }
        }
        if (request.Operation == "set_test_capture_failure" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
                || !args.TryGetProperty("enabled", out var enabled) || enabled.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                return FileMailbox.Error(request.Id, "invalid_request", "Expected test enabled flag.");
            MediaFailureFixture.Enabled = enabled.GetBoolean();
            return ResponseBuilder.Success(request.Id, new System.Text.Json.Nodes.JsonObject { ["enabled"] = MediaFailureFixture.Enabled });
        }
        if (request.Operation == "check_test_potion_readers" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
            return Success(request, JsonSerializer.Serialize(PotionInspectionChecks.Run(null, Observe)));
        if (request.Operation == "check_test_display_readers" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } displayPlayer)
        {
            await RelicCmd.Obtain<Anchor>(displayPlayer);
            await RelicCmd.Obtain<Lantern>(displayPlayer);
            await RelicCmd.Obtain<PenNib>(displayPlayer);
            await SettledObservation();
            return Success(request, JsonSerializer.Serialize(RelicInspectionChecks.Run()));
        }
        if (request.Operation == "check_test_dispatch" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
            return Success(request, JsonSerializer.Serialize(await TestDispatchChecks.Run()));
        if (request.Operation == "check_test_run_result_text" && testMode
            && (System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
                || testSettings.Get("STS2_AGENT_TEST_ENDING_SCENARIO") != null))
            return Success(request, JsonSerializer.Serialize(RunResultTextChecks.Read(runResultInspection)));
        if (request.Operation == "check_test_card_additions" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } additionPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await CardAdditionChecks.Run(additionPlayer, Frame, observation.CardId)));
        }
        if (request.Operation == "check_test_permanent_cards" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } permanentPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await PermanentCardChecks.Run(permanentPlayer, Frame, observation.CardId)));
        }
        if (request.Operation == "check_test_combat_handoff" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } handoffPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await CombatHandoffChecks.Run(handoffPlayer, observation, Frame, Observe)));
        }
        if (request.Operation == "check_test_death_notifications" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } deathPlayer)
            return Success(request, JsonSerializer.Serialize(await DeathNotificationChecks.Run(deathPlayer, observation.CardId)));
        if (request.Operation == "check_test_orb_events" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } orbEventPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await OrbEventChecks.Run(orbEventPlayer, Frame, observation.CardId)));
        }
        if (request.Operation == "check_test_companions" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } companionPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await CompanionChecks.Run(companionPlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation == "check_test_blades" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } bladePlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await SovereignBladeChecks.Run(bladePlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation == "check_test_orb_visibility" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } orbPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await OrbVisibilityChecks.Run(orbPlayer, Frame, Observe)));
        }
        if (request.Operation == "check_test_capacity" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } capacityPlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            return Success(request, JsonSerializer.Serialize(await CapacityChecks.Run(capacityPlayer, Frame, observation.CardId, Observe)));
        }
        if (request.Operation is "check_test_combat_resources" or "check_test_star_reveal" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } combatResourcePlayer)
        {
            async Task Frame() { await ObservationFrame(); Observe(); }
            var checks = request.Operation == "check_test_star_reveal"
                ? await CombatResourceChecks.FirstReveal(combatResourcePlayer, Frame, observation.CardId)
                : await CombatResourceChecks.Run(combatResourcePlayer, Frame, observation.CardId);
            return Success(request, JsonSerializer.Serialize(checks));
        }
        if (request.Operation == "check_test_inventory" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } inventoryPlayer)
            return Success(request, JsonSerializer.Serialize(await RunInventoryChecks.Run(inventoryPlayer, ObservationFrame, observation.CardId)));
        if (request.Operation == "check_test_resources" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1" && LocalPlayer is { } resourcePlayer)
            return Success(request, JsonSerializer.Serialize(await RunResourceChecks.Run(resourcePlayer, ObservationFrame)));
        if (request.Operation == "check_test_resource_masks" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "deck" && LocalPlayer is { } maskedPlayer)
            return Success(request, JsonSerializer.Serialize(await RunResourceChecks.Covered(maskedPlayer, ObservationFrame)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_ENDING_SCENARIO") != null
            && request.Operation is "external_back_test_result" or "reopen_test_timeline" or "close_test_timeline")
        {
            if (request.Operation == "reopen_test_timeline")
                NGame.Instance!.MainMenu!.SubmenuStack.PushSubmenuType<MegaCrit.Sts2.Core.Nodes.Screens.Timeline.NTimelineScreen>();
            else if (request.Operation == "external_back_test_result")
                NGame.Instance!.MainMenu!.SubmenuStack.Peek()!.GetNode<NButton>("BackButton").ForceClick();
            else NGame.Instance!.MainMenu!.SubmenuStack.Peek()!.GetNode<NButton>("BackButton").ForceClick();
            for (int i = 0; i < 100; i++) await ObservationFrame();
            return Success(request, await SettledObservation());
        }
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1")
        {
            if (request.Operation == "inspect_test_browsing_containers")
                return Success(request, JsonSerializer.Serialize(new { containers = BrowsableContentChecks.Containers() }));
            if (request.Operation == "prepare_test_browsable_result")
            {
                BrowsableContentChecks.PrepareResult(runResultInspection);
                return Success(request, Observe());
            }
            if (request.Operation == "prepare_test_browsable_history")
            {
                await BrowsableContentChecks.PrepareHistory(runResultInspection, ObservationFrame);
                return Success(request, Observe());
            }
            if (request.Operation == "check_test_browsable_content")
                return Success(request, JsonSerializer.Serialize(BrowsableContentChecks.Run(rewardInspection, runResultInspection, Observe)));
        }
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && request.Operation == "check_test_top_bar")
            return Success(request, JsonSerializer.Serialize(TopBarVisibilityChecks.Run(observation, Observe)));
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && request.Operation == "check_test_selection_prompt")
            return Success(request, JsonSerializer.Serialize(SelectionPromptChecks.Run(observation, Observe)));
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") is "grid_enchantments" or "upgrade_enchantments"
            && request.Operation == "check_test_selection_observation")
            return Success(request, JsonSerializer.Serialize(SelectionObservationChecks.Run(observation, Observe)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == "afflictions"
            && request.Operation == "check_test_afflictions")
            return Success(request, JsonSerializer.Serialize(AfflictionObservationChecks.Run(observation, Observe)));
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && request.Operation == "check_test_hand_resources" && LocalPlayer is { } handResourcePlayer)
            return Success(request, JsonSerializer.Serialize(await HandResourceChecks.Run(this, handResourcePlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") == "enchantments"
            && request.Operation == "check_test_enchantments")
            return Success(request, JsonSerializer.Serialize(EnchantmentObservationChecks.Run()));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_TURN_SCENARIO") == "thieving_hopper"
            && request.Operation == "capture_test_power_tips")
            return Success(request, JsonSerializer.Serialize(await PowerTextChecks.CaptureHopper(ObservationFrame)));
        if (testMode && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && request.Operation == "capture_test_gas_bomb_intent")
            return Success(request, JsonSerializer.Serialize(await IntentTextChecks.CaptureGasBomb(ObservationFrame)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") != null && LocalPlayer != null)
        {
            if (testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") == "trial")
            {
                if (request.Operation == "check_test_confirmation")
                    return Success(request, JsonSerializer.Serialize(ConfirmationFixture.Read()));
                if (request.Operation is "open_test_unowned_confirmation" or "cancel_test_confirmation" or "reopen_test_confirmation")
                {
                    if (request.Operation == "open_test_unowned_confirmation") ConfirmationFixture.OpenUnowned();
                    else if (request.Operation == "cancel_test_confirmation") ConfirmationFixture.Cancel();
                    else ConfirmationFixture.Reopen();
                    await WaitUntil(() => !EventConfirmation.BackdropAnimating
                        && (EventConfirmation.Current is not { } popup || EventConfirmation.Ready(popup)));
                    return Success(request, await SettledObservation());
                }
            }
            if (request.Operation == "check_test_divination" && DivinationInspection.Current != null)
                return Success(request, JsonSerializer.Serialize(DivinationFixture.Read(LocalPlayer)));
            if (request.Operation == "check_test_event") return Success(request, JsonSerializer.Serialize(EventFixture.Read(LocalPlayer)));
            if (request.Operation == "check_test_event_english") return Success(request, JsonSerializer.Serialize(EventTextChecks.Run(
                testSettings.Get("STS2_AGENT_TEST_EVENT_SCENARIO") == "tea")));
            if (request.Operation == "prepare_test_event_victory")
            {
                await EventFixture.PrepareVictory(LocalPlayer);
                return Success(request, await SettledObservation());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_ANCIENT_SCENARIO") is { } ancientScenario && LocalPlayer != null)
        {
            if (request.Operation == "check_test_ancient") return Success(request, JsonSerializer.Serialize(AncientFixture.Read(LocalPlayer)));
            if (request.Operation == "start_test_ancient_combat")
            {
                await AncientFixture.EnterCombat(ancientScenario, LocalPlayer, ObservationFrame);
                return Success(request, await SettledObservation());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_NAVIGATION_SCENARIO") != null && LocalPlayer != null)
        {
            if (request.Operation == "check_test_navigation")
                return Success(request, JsonSerializer.Serialize(NavigationFixture.Read(LocalPlayer)));
            if (request.Operation == "finish_test_navigation_boss")
            {
                await NavigationFixture.FinishBoss(ObservationFrame);
                return Success(request, await SettledObservation());
            }
            if (request.Operation is "set_test_navigation_drawing" or "clear_test_navigation_drawing")
            {
                NRun.Instance!.GlobalUi.MapScreen.Drawings.SetDrawingModeLocal(request.Operation.StartsWith("set_")
                    ? MegaCrit.Sts2.Core.Nodes.Screens.Map.DrawingMode.Drawing : MegaCrit.Sts2.Core.Nodes.Screens.Map.DrawingMode.None);
                return Success(request, Observe());
            }
            if (request.Operation == "scroll_test_navigation")
            {
                using var scroll = new InputEventPanGesture { Delta = new Vector2(0, -30) };
                NRun.Instance!.GlobalUi.MapScreen.Call("ProcessScrollEvent", scroll);
                for (int i = 0; i < 30; i++) await ObservationFrame();
                return Success(request, Observe());
            }
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_SHOP_SCENARIO") == "targeting"
            && request.Operation == "cancel_test_shop_targeting")
        {
            await ShopFixture.CancelTargeting();
            return Success(request, Observe());
        }
        if (testMode && testSettings.Get("STS2_AGENT_TEST_SHOP_SCENARIO") != null
            && request.Operation == "check_test_shop" && LocalPlayer != null)
            return Success(request, JsonSerializer.Serialize(ShopFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_TREASURE_SCENARIO") != null
            && request.Operation == "check_test_treasure" && LocalPlayer != null)
            return Success(request, JsonSerializer.Serialize(TreasureFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_REST_SCENARIO") != null
            && request.Operation == "check_test_rest_site" && LocalPlayer != null)
            return Success(request, JsonSerializer.Serialize(RestSiteFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_REWARD_SCENARIO") != null
            && request.Operation == "check_test_rewards" && LocalPlayer != null)
            return Success(request, JsonSerializer.Serialize(RewardFixture.Read(LocalPlayer)));
        if (testMode && testSettings.Get("STS2_AGENT_TEST_POTION_SCENARIO") != null && LocalPlayer != null)
        {
            if (request.Operation == "check_test_potion_state")
                return Success(request, JsonSerializer.Serialize(PotionFixture.Read(LocalPlayer)));
            if (request.Operation == "replace_test_potion")
            {
                await PotionFixture.Replace(LocalPlayer);
                return Success(request, Observe());
            }
        }
        if (request.Operation == "check_test_play_state" && testMode
            && testSettings.Get("STS2_AGENT_TEST_PLAY_SCENARIO") != null && LocalPlayer != null)
            return Success(request, JsonSerializer.Serialize(PlayFixture.Read(LocalPlayer)));
        if (request.Operation == "check_test_selection_race" && testMode
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "scroll_race")
            return Success(request, JsonSerializer.Serialize(await SelectionFixture.CheckScrollRace(ObservationFrame)));
        if (request.Operation == "check_test_selection_input" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "grid_manual")
            return Success(request, JsonSerializer.Serialize(await SelectionInputChecks.Run(this, observation, ObservationFrame, Observe)));
        if (request.Operation == "check_test_selection_options" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "grid_manual")
            return Success(request, JsonSerializer.Serialize(await SelectionOptionChecks.Run(this, Observe)));
        if (request.Operation == "check_test_selection_view" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") == "1"
            && testSettings.Get("STS2_AGENT_TEST_SELECTION_SCENARIO") == "grid_manual")
            return Success(request, JsonSerializer.Serialize(await SelectionViewChecks.Run(this, Observe)));
        if (request.Operation == "check_test_deck_lifecycle" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") is { } deckChecks)
            return Success(request, JsonSerializer.Serialize(await DeckInspectionChecks.Lifecycle(this, deckChecks)));
        if (request.Operation == "check_test_card_views" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_DECK_CHECKS") is { } cardChecks)
            return Success(request, JsonSerializer.Serialize(await DeckInspectionChecks.CardViews(this, cardChecks)));
        if (request.Operation == "check_test_piles" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_PILE_CHECKS") is { } pileChecks)
            return Success(request, JsonSerializer.Serialize(await PileInspectionChecks.Run(this, pileChecks)));
        if (request.Operation == "check_test_map" && testMode
            && System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_MAP_CHECKS") is { } mapChecks)
            return Success(request, JsonSerializer.Serialize(await MapInspectionChecks.Run(this, mapChecks)));
        if (request.Operation == "start_test_combat")
        {
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before submitting an action.");
        if (!before.GetProperty("available_actions").EnumerateArray()
                .Any(action => action.GetString() == request.Operation))
            return FileMailbox.Error(request.Id, "illegal_action", "Action is not available in this state.");
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
            return Success(request, await SettledObservation());
        }
        return null;
    }
}
