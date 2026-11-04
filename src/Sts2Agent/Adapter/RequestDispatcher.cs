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
    private async Task<string> ExecuteCore(Request request)
    {
        if (await TestRequestBeforeCapture(request) is { } early) return early;
        var snapshot = Capture();
        string before = snapshot.Json;
        JsonElement beforeState = snapshot.State;
        if (request.Operation is not ("set_test_capture_failure" or "inspect_potions" or "inspect_relics" or "inspect_combatants" or "inspect_deck" or "inspect_pile" or "inspect_selection" or "select_card" or "selection_option" or "set_selection_view" or "inspect_targets" or "play_card" or "use_potion" or "discard_potion" or "claim_reward" or "choose_rest_option" or "loot_treasure" or "buy_item" or "choose_ancient_option" or "choose_event_option" or "set_divination_tool" or "divine" or "respond_to_confirmation" or "travel_to_node" or "run_result_option")
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
            return Success(request, before);
        }
        if (request.Operation == "capture_screenshot")
        {
            if (ViewportCapture.Read() is not { } capture)
                return FileMailbox.Error(request.Id, "screenshot_unavailable", "A rendered game viewport is required.");
            return Success(request, JsonSerializer.Serialize(new
            {
                snapshot_id = beforeState.GetProperty("snapshot_id").GetString(),
                capture.width, capture.height, png_base64 = Convert.ToBase64String(capture.png)
            }));
        }
        if (await TestRequestAfterCapture(request, beforeState) is { } testResponse) return testResponse;
        if (request.Operation == "respond_to_confirmation")
            return await ConfirmationRequest(request, beforeState);
        if (request.Operation is "inspect_run_result" or "run_result_option") return await RunResultRequest(request, beforeState);
        if (request.Operation is "advance_dialogue" or "proceed" && EpilogueInspection.Current != null)
            return await EpilogueRequest(request, beforeState);
        if (request.Operation == "travel_to_node") return await TravelRequest(request, beforeState);
        if (request.Operation is "use_potion" or "discard_potion" || request.Operation == "inspect_targets"
            && request.Arguments is { } targetArguments && targetArguments.TryGetProperty("potion_slot", out _))
            return await PotionRequest(request, beforeState);
        if (request.Operation is "inspect_ancient" or "choose_ancient_option" or "advance_dialogue"
            || request.Operation == "proceed" && RewardInspection.Current == null && AncientInspection.Current != null)
            return await AncientRequest(request, beforeState);
        if (request.Operation is "set_divination_tool" or "divine"
            || request.Operation is "inspect_event" or "proceed" && RewardInspection.Current == null && DivinationInspection.Current != null)
            return await DivinationRequest(request, beforeState);
        if (request.Operation is "inspect_event" or "choose_event_option"
            || request.Operation == "proceed" && RewardInspection.Current == null && EventInspection.Current != null)
            return await EventRequest(request, beforeState);
        if (request.Operation is "open_shop" or "close_shop" or "inspect_shop" or "buy_item"
            || request.Operation == "proceed" && RewardInspection.Current == null && ShopInspection.Current != null)
            return await ShopRequest(request, beforeState);
        if (request.Operation is "loot_treasure" or "inspect_treasure"
            || request.Operation == "proceed" && RewardInspection.Current == null && TreasureInspection.Current != null)
            return await TreasureRequest(request, beforeState);
        if (request.Operation is "inspect_rest_site" or "choose_rest_option"
            || request.Operation == "proceed" && RewardInspection.Current == null && RestSiteInspection.Current != null)
            return await RestSiteRequest(request, beforeState);
        if (request.Operation is "inspect_rewards" or "claim_reward" or "proceed")
            return await RewardRequest(request, beforeState);
        if (request.Operation is "inspect_targets" or "play_card")
            return await CardPlayRequest(request, beforeState);
        if (request.Operation is "inspect_selection" or "set_selection_view" or "select_card" or "selection_option")
            return await SelectionRequest(request, beforeState);
        if (request.Operation == "inspect_deck")
        {
            DeckOptions options;
            try { options = DeckOptions.Parse(request.Arguments); }
            catch (Exception error) when (error is JsonException or InvalidOperationException)
            {
                return ResponseBuilder.Error(request.Id, "invalid_request", "Invalid deck options: use view_upgrades, sort_by and descending; descending requires sort_by.",
                    publicMessage: true, uiUnchanged: true);
            }
            return await InspectDeck(request, options);
        }
        if (request.Operation == "inspect_pile")
        {
            PileOptions options;
            try { options = PileOptions.Parse(request.Arguments); }
            catch (Exception error) when (error is JsonException or InvalidOperationException)
            {
                return ResponseBuilder.Error(request.Id, "invalid_request", "Invalid combat pile options: specify pile as draw, discard or exhaust.",
                    publicMessage: true, uiUnchanged: true);
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
            UiChanged();
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
                return Success(request, after);
            }
            finally
            {
                if (GodotObject.IsInstanceValid(map)) map.Opened -= Opened;
            }
        }
        if (request.Operation == "close_card_view")
        {
            var screen = CardView.Current;
            if (CardView.CloseUnavailableReason(screen) is { } reason)
                return ResponseBuilder.Error(request.Id, "illegal_action", reason, publicMessage: true, uiUnchanged: true);
            UiChanged();
            CardView.Close(screen!);
            return Success(request, await SettledObservation());
        }
        if (request.Operation == "close_deck")
        {
            var screen = DeckView.Current;
            if (screen == null || !DeckView.CanClose(screen))
                return FileMailbox.Error(request.Id, "illegal_action", "The current deck screen cannot be closed.");
            UiChanged();
            DeckView.Close(screen);
            return Success(request, await SettledObservation());
        }
        if (request.Operation == "inspect_relics")
        {
            bool full = true;
            if (request.Arguments is { } options)
            {
                if (options.EnumerateObject().Any(property => property.Name != "level")
                    || options.TryGetProperty("level", out var level)
                        && (level.ValueKind != JsonValueKind.String || level.GetString() is not ("summary" or "full")))
                    return FileMailbox.Error(request.Id, "invalid_request", "Relic level must be full or summary.", publicMessage: true);
                if (options.TryGetProperty("level", out level)) full = level.GetString() != "summary";
            }
            if (RelicInspection.UnavailableReason() is { } reason)
                return FileMailbox.Error(request.Id, "illegal_action", reason, publicMessage: true);
            var holders = RelicInspection.VisibleHolders()!;
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_RELIC_CHECKS");
            if (testMode && checks != null && full)
                RelicInspectionChecks.Run(checks);
            return InspectionSuccess(request, beforeState, RelicInspection.Inspect(holders, full));
        }
        if (request.Operation == "inspect_combatants")
            return CombatantsRequest(request, beforeState);
        if (request.Operation == "inspect_potions")
        {
            bool full = true;
            if (request.Arguments is { } options)
            {
                if (options.EnumerateObject().Any(property => property.Name != "level")
                    || options.TryGetProperty("level", out var level)
                        && (level.ValueKind != JsonValueKind.String || level.GetString() is not ("summary" or "full")))
                    return FileMailbox.Error(request.Id, "invalid_request", "Potion level must be full or summary.", publicMessage: true);
                if (options.TryGetProperty("level", out level)) full = level.GetString() != "summary";
            }
            if (PotionInspection.UnavailableReason() is { } reason)
                return FileMailbox.Error(request.Id, "illegal_action", reason, publicMessage: true);
            var holders = PotionInspection.VisibleHolders()!;
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_POTION_CHECKS");
            if (testMode && checks != null && full)
                PotionInspectionChecks.Run(checks, Observe);
            return InspectionSuccess(request, beforeState, PotionInspection.Read(holders, full));
        }
        if (request.Operation == "inspect_ui")
        {
            if (!UiInspection.CanRead())
                return FileMailbox.Error(request.Id, "illegal_action", "UI details are unavailable in the current screen.", publicMessage: true);
            string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_UI_CHECKS");
            if (testMode && checks != null)
                UiInspectionChecks.Run(checks);
            return InspectionSuccess(request, beforeState, new { hover_tips = UiInspection.Read() });
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
            return InspectionSuccess(request, beforeState, new {
                energy = resources.Energy, max_energy = resources.Maximum, stars = resources.Stars,
                draw_count = resources.DrawCount, discard_count = resources.DiscardCount, exhaust_count = resources.ExhaustCount,
                hand = CombatObservation.HandCards(hand).Select(reader.Card).ToArray() });
        }
        if (request.ExpectedState != beforeState.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before submitting an action.");
        if (request.Operation == "end_turn") return await EndTurnRequest(request);
        if (!beforeState.GetProperty("available_actions").EnumerateArray()
                .Any(action => action.GetString() == request.Operation))
            return FileMailbox.Error(request.Id, "illegal_action", "Action is not available in this state.");


        return Success(request, await SettledObservation());
    }

}
