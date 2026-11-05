using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace Sts2Agent;

internal static class SelectionOptionChecks
{
    public static async Task<object> Run(GameAdapter adapter, Func<string> observe)
    {
        var selection = CardSelection.Current!;
        var button = selection.Options().Single(option => option.id == "confirm").button;
        if (!button.IsEnabled) throw new InvalidOperationException("Expected an enabled confirmation button.");
        var selected = selection.Selected;
        using var original = JsonDocument.Parse(observe());
        string? originalToken = original.RootElement.GetProperty("snapshot_id").GetString();
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        var enabled = HarmonyLib.AccessTools.Field(typeof(NClickableControl), "_isEnabled");
        try
        {
            // Preserve the visible button to test disabled input without starting its hide tween.
            enabled.SetValue(button, false);
            using var before = JsonDocument.Parse(observe());
            var request = new Request(Guid.NewGuid().ToString("N"), "selection_option",
                before.RootElement.GetProperty("snapshot_id").GetString(),
                JsonSerializer.SerializeToElement(new { option_id = "confirm" }));
            using var rejected = JsonDocument.Parse(await adapter.Execute(request));
            var error = rejected.RootElement.GetProperty("error");
            var facts = rejected.RootElement.GetProperty("execution");
            Check("visible disabled option has a specific public reason",
                error.GetProperty("code").GetString() == "illegal_action"
                && error.GetProperty("public_message").GetString()!.Contains("disabled"));
            Check("disabled option guarantees no input",
                !error.GetProperty("action_submitted").GetBoolean()
                && !facts.GetProperty("ui_interaction_started").GetBoolean()
                && !facts.GetProperty("action_submission_observed").GetBoolean());
            Check("disabled option preserves the selected cards", selection.Selected.SequenceEqual(selected));

            using var stale = JsonDocument.Parse(await adapter.Execute(request with { ExpectedState = "outdated" }));
            var staleError = stale.RootElement.GetProperty("error");
            Check("stale state takes priority over disabled options",
                staleError.GetProperty("code").GetString() == "stale_state"
                && !staleError.TryGetProperty("action_submitted", out _));

            using var invalid = JsonDocument.Parse(await adapter.Execute(request with {
                Arguments = JsonSerializer.SerializeToElement(new { option_id = 5 }) }));
            var invalidError = invalid.RootElement.GetProperty("error");
            Check("native argument rejection is public and unsubmitted",
                invalidError.GetProperty("code").GetString() == "invalid_request"
                && invalidError.GetProperty("public_message").GetString()!.Contains("option_id")
                && !invalidError.GetProperty("action_submitted").GetBoolean());
        }
        finally { enabled.SetValue(button, true); }
        using var restored = JsonDocument.Parse(observe());
        Check("option checks restore the button and original snapshot", button.IsEnabled
            && restored.RootElement.GetProperty("snapshot_id").GetString() == originalToken
            && selection.Selected.SequenceEqual(selected));
        return new { checks, passed = checks.All(c => JsonSerializer.SerializeToElement(c).GetProperty("passed").GetBoolean()) };
    }
}
