using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace Sts2Agent;

internal static class SelectionPromptChecks
{
    public static object Run(CombatObservation observation, Func<string> observe)
    {
        var selection = CardSelection.Current!;
        if (selection.Kind is not ("bundle" or "view_cards") || selection.Status != "visible")
            throw new InvalidOperationException("A visible bundle or result screen is required.");
        CanvasItem label = selection.Kind == "bundle"
            ? selection.Owner.GetNode<NCommonBanner>("Banner").label
            : selection.Owner.GetNode<RichTextLabel>("%BottomLabel");
        string baseline = observe();
        var reader = new SelectionInspection(observation);
        var checks = new List<object>();
        string? Detail() => JsonSerializer.SerializeToElement(reader.Read(selection, full: true)).GetProperty("prompt").GetString();
        string? Basic()
        {
            using var current = JsonDocument.Parse(observe());
            return current.RootElement.GetProperty("selection").GetProperty("prompt").GetString();
        }
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        Check("visible prompt agrees across readers", !string.IsNullOrWhiteSpace(Detail()) && Detail() == Basic());
        bool visible = label.Visible;
        Color color = label.Modulate;
        bool ownerVisible = selection.Owner.Visible;
        try
        {
            label.Visible = false;
            Check("hidden label does not disclose text", Detail() == null && Basic() == null);
            label.Visible = visible;
            label.Modulate = new Color(color.R, color.G, color.B, 0);
            Check("transparent label does not disclose text", Detail() == null && Basic() == null);
            label.Modulate = color;
            selection.Owner.Visible = false;
            Check("hidden page does not disclose text", Detail() == null && Basic() == null);
        }
        finally
        {
            label.Visible = visible;
            label.Modulate = color;
            selection.Owner.Visible = ownerVisible;
        }
        Check("checks restore UI", baseline == observe());
        return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
    }
}
