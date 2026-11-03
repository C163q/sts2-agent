using System.Text.Json;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal static class TransitionResult
{
    public static bool Complete(string reason, TurnEventBuffer? buffer = null) =>
        buffer?.Truncated != true && reason is not ("timeout" or "interrupted");

    public static object Create(string reason, TurnEventBuffer? buffer = null) => new {
        stop_reason = reason, complete = Complete(reason, buffer),
        events = buffer?.Events ?? new List<Dictionary<string, object?>>() };

    public static void ApplyEvents(JsonObject transition, TurnEventBuffer buffer)
    {
        transition["events"] = JsonSerializer.SerializeToNode(buffer.Events);
        transition["complete"] = transition["complete"]!.GetValue<bool>() && !buffer.Truncated;
    }
}
