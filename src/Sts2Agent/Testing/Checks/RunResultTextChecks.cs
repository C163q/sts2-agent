using Godot;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;
using System.Text.Json;

namespace Sts2Agent;

internal static class RunResultTextChecks
{
    public static object Read(RunResultInspection results)
    {
        var root = results.Current?.Root ?? throw new InvalidOperationException("Expected a displayed result page.");
        var nativeLabels = VisibleUi.Descendants<CanvasItem>(root)
            .Where(node => node is Label or RichTextLabel).Select(node => (node, text: node is Label label ? label.Text : ((RichTextLabel)node).Text)).ToArray();
        var texts = VisibleUi.Descendants<CanvasItem>(root).Where(VisibleUi.Browsable)
            .Select(node => node switch { Label label => label.Text, RichTextLabel rich => rich.Text, _ => null })
            .Where(text => !string.IsNullOrWhiteSpace(text)).Distinct().ToArray();
        // Retained labels must survive unrelated localization work without changing native UI.
        for (int i = 0; i < 256; i++) _ = new LocString("cards", "LANTERN_KEY.title").GetFormattedText();
        using var body = JsonSerializer.SerializeToDocument(results.Read(full: true));
        var actual = body.RootElement.GetProperty("texts").EnumerateArray().Select(t => t.GetString()).ToHashSet();
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        string? title = body.RootElement.GetProperty("title").GetString();
        if (root is NGameOverScreen)
        {
            Check("structured_banner_is_not_repeated", title == null || !actual.Contains(title));
            foreach (var row in body.RootElement.GetProperty("score_lines").EnumerateArray())
                Check("structured_score_is_not_repeated", !actual.Contains(row.GetProperty("label").GetString())
                    && !actual.Contains(row.GetProperty("value").GetString()));
            foreach (var option in body.RootElement.GetProperty("options").EnumerateArray())
                Check("structured_button_is_not_repeated", !actual.Contains(option.GetProperty("text").GetString()));
        }
        string collision = title ?? "Unstructured narrative";
        var narrative = new Label { Name = "UnstructuredNarrative", Text = collision,
            Position = new Vector2(40, 120), Size = new Vector2(650, 40) };
        root.AddChild(narrative);
        try
        {
            using var duplicated = JsonSerializer.SerializeToDocument(results.Read(full: true));
            Check("same_text_from_independent_narrative_is_retained", VisibleUi.Browsable(narrative)
                && duplicated.RootElement.GetProperty("texts").EnumerateArray().Any(t => t.GetString() == collision));
        }
        finally { root.RemoveChild(narrative); narrative.QueueFree(); }
        Check("native_labels_remain_unchanged", nativeLabels.All(item =>
            (item.node is Label label ? label.Text : ((RichTextLabel)item.node).Text) == item.text));
        return new { texts, culture = LocManager.Instance.CultureInfo.Name, passed, checks };
    }
}
