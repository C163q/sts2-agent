using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace Sts2Agent;

internal static class SelectionViewChecks
{
    public static async Task<object> Run(GameAdapter adapter, Func<string> observe)
    {
        var selection = CardSelection.Current!;
        var eye = selection.Eye!;
        if (!selection.CanPeek || selection.Peeking) throw new InvalidOperationException("Expected the visible grid and enabled eye.");
        var selected = selection.Selected;
        using var original = JsonDocument.Parse(observe());
        string? token = original.RootElement.GetProperty("snapshot_id").GetString();
        var enabled = HarmonyLib.AccessTools.Field(typeof(NClickableControl), "_isEnabled");
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        bool visible = eye.Visible;
        try
        {
            foreach (string state in new[] { "disabled", "hidden" })
            {
                enabled.SetValue(eye, state != "disabled");
                eye.Visible = state != "hidden";
                using var before = JsonDocument.Parse(observe());
                Check(state + " eye is not offered as a view action",
                    !before.RootElement.GetProperty("available_actions").EnumerateArray()
                        .Any(a => a.GetString() == "set_selection_view"));
                var request = new Request(Guid.NewGuid().ToString("N"), "set_selection_view", null,
                    JsonSerializer.SerializeToElement(new { view = "battlefield" }));
                using var response = JsonDocument.Parse(await adapter.Execute(request));
                var error = response.RootElement.GetProperty("error");
                Check(state + " eye has a specific unchanged rejection",
                    error.GetProperty("code").GetString() == "illegal_action"
                    && error.GetProperty("ui_unchanged").GetBoolean()
                    && error.GetProperty("public_message").GetString()!.Contains(state == "disabled" ? "disabled" : "visible")
                    && !response.RootElement.GetProperty("execution").GetProperty("ui_interaction_started").GetBoolean());
            }
            var invalidRequest = new Request(Guid.NewGuid().ToString("N"), "set_selection_view", null,
                JsonSerializer.SerializeToElement(new { view = 5 }));
            using var invalid = JsonDocument.Parse(await adapter.Execute(invalidRequest));
            var invalidError = invalid.RootElement.GetProperty("error");
            Check("raw invalid view arguments are public and unchanged",
                invalidError.GetProperty("code").GetString() == "invalid_request"
                && invalidError.GetProperty("ui_unchanged").GetBoolean()
                && invalidError.GetProperty("public_message").GetString()!.Contains("view"));
        }
        finally { enabled.SetValue(eye, true); eye.Visible = visible; }
        using var restored = JsonDocument.Parse(observe());
        Check("view checks restore the eye, selection and snapshot", selection.CanPeek && !selection.Peeking
            && selection.Selected.SequenceEqual(selected)
            && restored.RootElement.GetProperty("snapshot_id").GetString() == token);
        return new { checks, passed = checks.All(c => JsonSerializer.SerializeToElement(c).GetProperty("passed").GetBoolean()) };
    }
}
