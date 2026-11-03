using System.Text.Json;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal static class ResponseBuilder
{
    public static string Inspection(JsonElement snapshot, object details)
    {
        var result = JsonSerializer.SerializeToNode(details)!.AsObject();
        foreach (string key in new[] { "snapshot_id", "scene", "screen", "schema_version" })
            result[key] = JsonNode.Parse(snapshot.GetProperty(key).GetRawText());
        return result.ToJsonString();
    }

    public static string WithTransition(string observation, object transition,
        object? rewardResult = null, object? purchaseResult = null)
    {
        var state = JsonNode.Parse(observation)!.AsObject();
        state["transition"] = JsonSerializer.SerializeToNode(transition);
        if (rewardResult != null) state["reward_result"] = JsonSerializer.SerializeToNode(rewardResult);
        if (purchaseResult != null) state["purchase_result"] = JsonSerializer.SerializeToNode(purchaseResult);
        return state.ToJsonString();
    }

    public static string Success(string id, JsonObject state) => JsonSerializer.Serialize(new { id, ok = true, state });

    public static string Error(string id, string code, string message, bool publicMessage = false, bool? actionSubmitted = null)
    {
        var error = new JsonObject { ["code"] = code, ["message"] = message };
        if (publicMessage) error["public_message"] = message;
        if (actionSubmitted.HasValue) error["action_submitted"] = actionSubmitted.Value;
        return JsonSerializer.Serialize(new { id, ok = false, error });
    }

    public static string Failure(string id, Exception error)
    {
        var cause = error.GetBaseException();
        return Error(id, cause is TimeoutException ? "timeout" : "game_error", cause.Message);
    }

    public static string WithExecution(string response, RequestExecution execution)
    {
        var result = JsonNode.Parse(response)!.AsObject();
        result["execution"] = JsonSerializer.SerializeToNode(execution.Facts);
        return result.ToJsonString();
    }
}
