using System.Text.Json;

namespace Sts2Agent;

internal sealed record Request(string Id, string Operation, string? ExpectedState, JsonElement? Arguments = null,
    ResponseOptions? ResponseOptions = null)
{
    public bool WantsDivinationImage => ResponseOptions?.IncludeDivinationImage ?? true;
}

internal sealed record ResponseOptions(bool IncludeDivinationImage = true)
{
    public static ResponseOptions Parse(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object || value.EnumerateObject().Count() > 1
            || value.EnumerateObject().Any(property => property.Name != "include_divination_image"))
            throw new JsonException("Expected only include_divination_image in response_options.");
        if (!value.TryGetProperty("include_divination_image", out var supplied)) return new();
        if (supplied.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
            throw new JsonException("include_divination_image must be boolean.");
        return new(supplied.GetBoolean());
    }
}
