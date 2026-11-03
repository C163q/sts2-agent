using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal sealed class ObservationSnapshot
{
    public string Json { get; }
    public JsonElement State { get; }
    public string Token { get; }
    public object? CombatIdentity { get; }
    public object? PlayerIdentity { get; }
    public object? SelectionIdentity { get; }

    private ObservationSnapshot(string json, string token, object? combat, object? player, object? selection)
    {
        Json = json;
        using var document = JsonDocument.Parse(json);
        State = document.RootElement.Clone();
        Token = token;
        CombatIdentity = combat;
        PlayerIdentity = player;
        SelectionIdentity = selection;
    }

    public static ObservationSnapshot Create(string body, bool maskDivinationDialogue,
        object? combat, object? player, object? selection)
    {
        string permissionState = body;
        if (maskDivinationDialogue)
        {
            var logical = JsonNode.Parse(body)!;
            if (logical["divination"] is JsonObject sphere) sphere["dialogue"] = null;
            permissionState = logical.ToJsonString();
        }
        string token = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(permissionState)));
        return new("{\"snapshot_id\":\"" + token + "\"," + body[1..], token, combat, player, selection);
    }
}
