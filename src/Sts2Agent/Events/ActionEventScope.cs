using System.Text.Json;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal sealed class ActionEventScope : IDisposable
{
    public static ActionEventScope? Current { get; private set; }
    public TurnEventBuffer Buffer { get; }

    public ActionEventScope(int limit = 512)
    {
        if (Current != null) throw new InvalidOperationException("An action is already being recorded.");
        Buffer = new(limit);
        Current = this;
    }

    public string Apply(string response)
    {
        var root = JsonNode.Parse(response)!;
        if (root["ok"]?.GetValue<bool>() != true || root["state"]?["transition"] is not JsonObject transition)
            return response;
        TransitionResult.ApplyEvents(transition, Buffer);
        return root.ToJsonString();
    }

    public void Dispose()
    {
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
