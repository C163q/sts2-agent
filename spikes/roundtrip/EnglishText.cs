using System.Text.Json;
using System.Text.RegularExpressions;
using Godot;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class EnglishText
{
    private readonly Dictionary<string, Dictionary<string, string>> tables = [];

    public string? CardName(NCard? card)
    {
        if (card == null || !GodotObject.IsInstanceValid(card)) return null;
        string? displayed = VisibleUi.Text(card, "%TitleLabel");
        if (displayed == null) return null;
        if (card.Visibility != ModelVisibility.Visible)
            return Entry("card_library", card.Visibility == ModelVisibility.Locked ? "LOCKED.title" : "UNKNOWN.title");
        // Preserve the visible suffix without reading a hidden upgrade level.
        return Name(card.Model!.TitleLocString) is { } name ? name + Regex.Match(displayed, @"\+\d*$").Value : null;
    }

    public string? Name(LocString title)
    {
        string? text = Entry(title.LocTable, title.LocEntryKey);
        if (text == null)
            return null;
        foreach (var variable in title.Variables)
            if (variable.Value is string or int or decimal)
                text = text.Replace("{" + variable.Key + "}", Convert.ToString(variable.Value,
                    System.Globalization.CultureInfo.InvariantCulture));
        return text.Contains('{') ? null : Plain(text);
    }

    public string? Entry(string table, string key)
    {
        if (!tables.TryGetValue(table, out var entries))
        {
            // Read a separate resource table; changing LocManager's locale refreshes game UI.
            using var file = Godot.FileAccess.Open($"res://localization/eng/{table}.json", Godot.FileAccess.ModeFlags.Read);
            entries = file == null ? [] : JsonSerializer.Deserialize<Dictionary<string, string>>(file.GetAsText()) ?? [];
            tables.Add(table, entries);
        }
        return entries.GetValueOrDefault(key);
    }

    public string? Button(string? displayed, int? turn)
    {
        if (displayed == null)
            return null;
        foreach (string key in new[] { "END_TURN_BUTTON", "UNDO_END_TURN_BUTTON" })
        {
            var source = new LocString("gameplay_ui", key);
            if (turn.HasValue)
                source.Add("turnNumber", turn.Value);
            if (Plain(source.GetFormattedText()) == displayed)
                return Entry("gameplay_ui", key)?.Replace("{turnNumber}", turn?.ToString());
        }
        return null;
    }

    public static string Plain(string text) => Regex.Replace(text, @"\[/?[^\]]+\]", "").Trim();
}
