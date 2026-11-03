using System.Text.Json;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private string InspectionSuccess(Request request, JsonElement snapshot, object details) =>
        Success(request, ObservationContext.Inspection(snapshot, details));
}
