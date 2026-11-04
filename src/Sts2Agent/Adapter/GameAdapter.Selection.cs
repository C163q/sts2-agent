using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static NCombatCardPile? SelectionPileButton(PileOptions options)
    {
        var selection = CardSelection.Current;
        if (selection is not { Peeking: true, Owner: not NPlayerHand }) return null;
        string path = options.Pile switch { "draw" => "%DrawPile", "discard" => "%DiscardPile", _ => "%ExhaustPile" };
        return selection.Owner.GetNodeOrNull<NCombatPilesContainer>("%CombatPiles")?.GetNodeOrNull<NCombatCardPile>(path);
    }

    private async Task<string> InspectSelection(Request request, JsonElement before)
    {
        bool? viewUpgrades = null;
        if (request.Arguments is { } inspectionArgs
            && inspectionArgs.EnumerateObject().Any())
        {
            if (inspectionArgs.EnumerateObject().Count() != 1
                || !inspectionArgs.TryGetProperty("view_upgrades", out var flag)
                || flag.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                return ResponseBuilder.Error(request.Id, "invalid_request", "Expected an optional boolean view_upgrades.",
                    publicMessage: true, uiUnchanged: true);
            viewUpgrades = flag.GetBoolean();
        }
        var candidate = CardSelection.Current;
        if (SelectionInspection.UnavailableReason(candidate) is { } reason)
            return ResponseBuilder.Error(request.Id, "illegal_action", reason,
                publicMessage: true, uiUnchanged: true);
        var selection = candidate!;
        bool unavailable = viewUpgrades.HasValue && !selection.CanViewUpgrades;
        JsonElement context = before.Clone();
        string? snapshot = before.GetProperty("snapshot_id").GetString();
        if (viewUpgrades.HasValue && !unavailable && selection.ViewUpgrades != viewUpgrades)
        {
            UiChanged();
            selection.UpgradeToggle!.ForceClick();
            string viewed = await SettledObservation();
            if (!SelectionActions.Same(selection) || selection.Status != "visible" || selection.InPreview
                || selection.ViewUpgrades != viewUpgrades)
                return FileMailbox.Error(request.Id, "illegal_action", "The selection changed while switching upgrade previews. Read the current state before continuing.", publicMessage: true);
            using var current = JsonDocument.Parse(viewed);
            snapshot = current.RootElement.GetProperty("snapshot_id").GetString();
            context = current.RootElement.Clone();
        }
        var result = new Dictionary<string, object?> {
            ["snapshot_id"] = snapshot,
            ["selection"] = new SelectionInspection(observation).Read(selection, full: true) };
        if (unavailable) result["errors"] = new[] { new { code = "upgrade_view_unavailable" } };
        return InspectionSuccess(request, context, result);
    }

    private async Task<string> SelectionRequest(Request request, JsonElement before)
    {
        if (request.Operation == "inspect_selection") return await InspectSelection(request, before);
        string? value = null;
        int cardId = -1;
        string field = request.Operation == "select_card" ? "card_id"
            : request.Operation == "selection_option" ? "option_id" : "view";
        var arguments = request.Arguments;
        if (arguments == null || arguments.Value.EnumerateObject().Count() != 1
            || !arguments.Value.TryGetProperty(field, out var supplied)
            || (field == "card_id" ? supplied.ValueKind != JsonValueKind.Number || !supplied.TryGetInt32(out cardId) || cardId < 0
                : supplied.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(value = supplied.GetString()) || value.Length > 128)
            || (field == "view" && value is not ("battlefield" or "selection")))
            return FileMailbox.Error(request.Id, "invalid_request", "Invalid selection arguments.");
        var selection = CardSelection.Current;
        if (selection == null || !selection.Supported || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return FileMailbox.Error(request.Id, "illegal_action", "No supported local card selection is available.");
        if (request.Operation == "set_selection_view")
        {
            if (!selection.CanPeek)
                return FileMailbox.Error(request.Id, "illegal_action", "The native eye button is unavailable.");
            bool peeking = value == "battlefield";
            if (selection.Peeking != peeking)
            {
                UiChanged();
                selection.Eye!.ForceClick();
            }
            string state = await SettledObservation();
            if (!SelectionActions.Same(selection) || !selection.Exposed || selection.Peeking != peeking)
                return FileMailbox.Error(request.Id, "illegal_action", "The selection changed while switching views.");
            return Success(request, state);
        }
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current selection before acting.");
        if (selection.Status != "visible")
            return FileMailbox.Error(request.Id, "illegal_action", "The selection is covered or hidden.");

        var model = request.Operation == "select_card" ? selection.Cards.FirstOrDefault(card => observation.CardId(card) == cardId) : null;
        var button = request.Operation == "selection_option" ? selection.Options().FirstOrDefault(option => option.id == value).button : null;
        if (request.Operation == "select_card" ? model == null || !selection.CanSelect
            : button == null || !button.IsEnabled)
            return FileMailbox.Error(request.Id, "illegal_action", "The requested candidate or button is unavailable.");
        var journal = CombatJournalScope.Current!;
        bool startedInCombat = journal.Capturing;
        UiChanged();
        if (model != null)
        {
            CardMovementJournal.Choose(model);
            try { await SelectionActions.Click(selection, model, ObservationFrame); }
            catch (InvalidOperationException error) { return FileMailbox.Error(request.Id, "illegal_action", error.Message); }
        }
        else button!.ForceClick();

        var (after, reason) = await ActionObservation(() =>
        {
            bool ready = CanEndTurn() && RunManager.Instance.ActionQueueSet.IsEmpty;
            string? boundary = journal.StopReason(ready);
            if (!startedInCombat)
            {
                var current = CardSelection.Current;
                if (RewardInspection.Current != null || RestSiteInspection.Current != null || TreasureInspection.Current != null || ShopInspection.Current != null || AncientInspection.Current != null || EventInspection.Current != null) boundary = NonCombatBoundary();
                else if (CardSelection.AwaitingInput) boundary = "choice_required";
                else if (current == null) boundary = "selection_resolved";
            }
            return boundary;
        });
        object transition = journal.Result(reason);
        return Success(request, ResponseBuilder.WithTransition(after, transition));
    }
}
