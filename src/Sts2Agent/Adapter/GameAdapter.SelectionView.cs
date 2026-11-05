namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> SetSelectionView(Request request, CardSelection? candidate, string view)
    {
        if (SelectionAvailability.ViewUnavailableReason(candidate) is { } reason)
            return ResponseBuilder.Error(request.Id, "illegal_action", reason,
                publicMessage: true, uiUnchanged: true);
        var selection = candidate!;
        bool peeking = view == "battlefield";
        if (selection.Peeking != peeking)
        {
            UiChanged();
            selection.Eye!.ForceClick();
        }
        string state = await SettledObservation();
        if (!SelectionActions.Same(selection) || !selection.Exposed || selection.Peeking != peeking)
            return FileMailbox.Error(request.Id, "illegal_action",
                "The selection changed while switching views. Read the current state before continuing.", publicMessage: true);
        return Success(request, state);
    }
}
