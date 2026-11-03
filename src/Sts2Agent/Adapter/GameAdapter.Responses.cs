using System.Text.Json;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private void UiChanged()
    {
        execution?.UiInteractionStarted();
        capture.UiChanged();
    }

    private string TransitionSuccess(Request request, string observed, string reason,
        object? rewardResult = null, object? purchaseResult = null) =>
        Success(request, ResponseBuilder.WithTransition(observed, TransitionResult.Create(reason), rewardResult, purchaseResult));

    private string Success(Request request, string observed)
    {
        var state = JsonNode.Parse(observed)!.AsObject();
        if (request.WantsDivinationImage && state["divination"] is JsonObject board
            && board["status"]?.GetValue<string>() == "visible")
        {
            var screen = DivinationInspection.Current;
            var image = screen == null || testMode && MediaFailureFixture.Enabled
                ? null : ViewportCapture.Read(DivinationInspection.Bounds(screen));
            if (image == null)
                return FileMailbox.Error(request.Id, "screenshot_unavailable", "A rendered divination board image is required.");
            var (width, height, png) = image.Value;
            state["divination_image"] = JsonSerializer.SerializeToNode(new { width, height, png_base64 = Convert.ToBase64String(png) });
        }
        if (CardSelection.Current is { } selection) state["selection_view"] = selection.Status;
        return ResponseBuilder.Success(request.Id, state);
    }
}
