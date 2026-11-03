using System.Text.Json;
using Godot;
using System.Text.RegularExpressions;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> EpilogueRequest(Request request, JsonElement before)
    {
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Observe the current dialogue before acting.");
        var context = EpilogueInspection.Current;
        var button = context == null ? null : EpilogueInspection.Button(context);
        if (context == null || !EpilogueInspection.Ready(context) || button == null
            || EpilogueInspection.IsProceed(button) != (request.Operation == "proceed"))
            return FileMailbox.Error(request.Id, "illegal_action", "The requested dialogue action is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? NonCombatBoundary() : "interrupted");
        return TransitionSuccess(request, after, reason);
    }

    private async Task<string> RunResultRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_run_result";
        string? id = null;
        if (!inspect && (request.Arguments is not { ValueKind: JsonValueKind.Object } args
            || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("option_id", out var option)
            || option.ValueKind != JsonValueKind.String || (id = option.GetString()) == null
            || !Regex.IsMatch(id, @"\A[a-z][a-z0-9_]*(?::[0-9]+)?\z")))
            return FileMailbox.Error(request.Id, "invalid_request", "A current result option_id is required.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Observe the current result before acting.");
        var context = runResultInspection.Current;
        if (context == null || !RunResultInspection.Exposed(context) || !runResultInspection.Ready(context))
            return FileMailbox.Error(request.Id, "illegal_action", "The run result is unavailable.");
        if (inspect) return InspectionSuccess(request, before, new { run_result = runResultInspection.Read(full: true) });
        var button = runResultInspection.Options(context).FirstOrDefault(o => o.id == id).button;
        if (button == null || !RunResultInspection.Clickable(button))
            return FileMailbox.Error(request.Id, "illegal_action", "The requested result button is unavailable.");
        if (button is NEpochSlot slot && !VisibleUi.OnScreen(slot))
        {
            await context.Root.GetNode<NSlotsContainer>("%SlotsContainer").LerpToSlot(slot.GlobalPosition.X);
            if (!ReferenceEquals(runResultInspection.Current?.Root, context.Root) || !runResultInspection.Ready(context)
                || !RunResultInspection.Clickable(slot) || !VisibleUi.OnScreen(slot))
                return FileMailbox.Error(request.Id, "illegal_action", "The unlock screen changed while scrolling.");
        }
        bool returningToMenu = id == "main_menu" || runResultInspection.ReturningToMenu;
        if (id == "main_menu") runResultInspection.Leaving();
        UiChanged();
        if (id is "next_chapter" or "previous_chapter")
        {
            // These native paginators subscribe to MouseReleased, not Released.
            using var release = new InputEventMouseButton { ButtonIndex = MouseButton.Left, Pressed = false };
            button.EmitSignal(NClickableControl.SignalName.MouseReleased, release);
        }
        else button.ForceClick();
        var (after, reason) = await ActionObservation(() => NModalContainer.Instance?.OpenModal != null ? "manual_input_required"
            : returningToMenu && NGame.Instance?.MainMenu is { } targetMenu && !targetMenu.SubmenuStack.SubmenusOpen
                && !RunUi.Transitioning() ? "action_completed" : NonCombatBoundary(includeRunOutcome: false));
        if (NGame.Instance?.MainMenu is { } menu && !menu.SubmenuStack.SubmenusOpen && !RunUi.Transitioning())
            runResultInspection.Finished();
        return TransitionSuccess(request, after, reason);
    }

}
