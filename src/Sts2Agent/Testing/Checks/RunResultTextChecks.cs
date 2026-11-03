using Godot;
using MegaCrit.Sts2.Core.Localization;

namespace Sts2Agent;

internal static class RunResultTextChecks
{
    public static object Read(RunResultInspection results)
    {
        var root = results.Current?.Root ?? throw new InvalidOperationException("Expected a displayed result page.");
        var texts = VisibleUi.Descendants<CanvasItem>(root).Where(VisibleUi.Browsable)
            .Select(node => node switch { Label label => label.Text, RichTextLabel rich => rich.Text, _ => null })
            .Where(text => !string.IsNullOrWhiteSpace(text)).Distinct().ToArray();
        // Retained labels must survive unrelated localization work without changing native UI.
        for (int i = 0; i < 256; i++) _ = new LocString("cards", "LANTERN_KEY.title").GetFormattedText();
        return new { texts, culture = LocManager.Instance.CultureInfo.Name };
    }
}
