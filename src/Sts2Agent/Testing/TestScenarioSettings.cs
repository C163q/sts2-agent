using System.Reflection;
using System.Text.Json;

namespace Sts2Agent;

internal sealed class TestScenarioSettings
{
    private static readonly Dictionary<string, string[]> Catalog = LoadCatalog();
    private Dictionary<string, string>? configured;

    private static Dictionary<string, string[]> LoadCatalog()
    {
        using var stream = typeof(TestScenarioSettings).Assembly.GetManifestResourceStream("Sts2Agent.TestScenarios")!;
        return JsonSerializer.Deserialize<Dictionary<string, string[]>>(stream)!;
    }

    public void Configure(JsonElement scenarios)
    {
        if (scenarios.ValueKind != JsonValueKind.Object) throw new ArgumentException("scenarios must be an object.");
        var next = new Dictionary<string, string>();
        foreach (var property in scenarios.EnumerateObject())
        {
            if (!Catalog.TryGetValue(property.Name, out var choices) || property.Name == "ending"
                || property.Value.ValueKind != JsonValueKind.String || !choices.Contains(property.Value.GetString()))
                throw new ArgumentException("Unknown or process-isolated scenario: " + property.Name);
            if (!next.TryAdd(property.Name, property.Value.GetString()!)) throw new ArgumentException("Duplicate scenario.");
        }
        configured = next;
    }

    public string? Get(string variable)
    {
        const string prefix = "STS2_AGENT_TEST_";
        const string suffix = "_SCENARIO";
        if (configured != null && variable.StartsWith(prefix) && variable.EndsWith(suffix))
            return configured.GetValueOrDefault(variable[prefix.Length..^suffix.Length].ToLowerInvariant());
        return Environment.GetEnvironmentVariable(variable);
    }
}
