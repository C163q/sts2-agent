using System.Text.Json;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static string InspectionSuccess(string id, JsonElement snapshot, object details) =>
        Success(id, ObservationContext.Inspection(snapshot, details));
}
