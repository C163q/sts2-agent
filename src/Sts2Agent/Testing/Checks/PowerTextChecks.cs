using System.Reflection;
using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Localization;

namespace Sts2Agent;

internal static class PowerTextChecks
{
    public static object Run()
    {
        using var file = Godot.FileAccess.Open("res://localization/eng/powers.json", Godot.FileAccess.ModeFlags.Read);
        var table = JsonSerializer.Deserialize<Dictionary<string, string>>(file.GetAsText())!;
        string language = LocManager.Instance.Language;
        var cases = new List<(LocString text, string template)>();
        var expected = new List<string>();
        List<object> results = [];
        foreach (var (key, template) in table.Where(entry => entry.Key.EndsWith(".smartDescription", StringComparison.Ordinal)
            || entry.Key.EndsWith(".description", StringComparison.Ordinal) || entry.Key.EndsWith(".remoteDescription", StringComparison.Ordinal)))
            foreach (int amount in new[] { 1, 2, 5 })
                foreach (bool onPlayer in new[] { true, false })
                {
                    var text = new LocString("powers", key);
                    foreach (System.Text.RegularExpressions.Match match in System.Text.RegularExpressions.Regex.Matches(template, @"\{([\w]+)"))
                    {
                        string name = match.Groups[1].Value;
                        object value = name switch
                        {
                            "Amount" => (decimal)amount,
                            "Energy" => new MegaCrit.Sts2.Core.Localization.DynamicVars.EnergyVar(amount),
                            "OnPlayer" => onPlayer,
                            "IsMultiplayer" => !onPlayer,
                            "OwnerName" => "Test Creature",
                            "ApplierName" or "Applier" => new MegaCrit.Sts2.Core.Localization.DynamicVars.StringVar(name, "Test Creature"),
                            "AfflictionTitle" or "Card" => new MegaCrit.Sts2.Core.Localization.DynamicVars.StringVar(name, "Test Card"),
                            "energyPrefix" => "colorless",
                            "singleStarIcon" => "[img]res://images/packed/sprite_fonts/star_icon.png[/img]",
                            _ => new MegaCrit.Sts2.Core.Localization.DynamicVars.DynamicVar(name, amount)
                        };
                        text.AddObj(name, value);
                    }
                    cases.Add((text, template));
                }
        try
        {
            LocManager.Instance.SetLanguage("eng");
            foreach (var (text, template) in cases)
            {
                string value = text.GetFormattedText();
                if (value == template && template.Contains('{'))
                    throw new InvalidOperationException("Native power template was not formatted: " + text.LocEntryKey);
                expected.Add(value);
            }
            LocManager.Instance.SetLanguage("zhs");
            for (int index = 0; index < cases.Count; index++)
            {
                var (text, template) = cases[index];
                string actual = EnglishCardText.Read(() => text.GetFormattedText());
                results.Add(new { key = text.LocEntryKey, amount = text.Variables.GetValueOrDefault("Amount"),
                    onPlayer = text.Variables.GetValueOrDefault("OnPlayer"), plural = template.Contains(":plural:"),
                    passed = actual == expected[index], expected = expected[index], actual });
            }
        }
        finally { LocManager.Instance.SetLanguage(language); }
        return new { templates = cases.Count / 6, results,
            passed = results.All(result => JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()) };
    }

    public static async Task<object> CaptureHopper(Func<Task> frame)
    {
        var node = CombatObservation.EnemyNodes().Single();
        var power = CombatantInspection.PowerContainer(node)!.GetChildren().OfType<NPower>()
            .Single(power => power.Model is EscapeArtistPower);
        string language = LocManager.Instance.Language;
        var directory = Directory.GetParent(Environment.GetEnvironmentVariable("STS2_AGENT_IPC_DIR")!)!.FullName;
        List<object> results = [];
        try
        {
            foreach (string locale in new[] { "zhs", "eng" })
            {
                LocManager.Instance.SetLanguage(locale);
                typeof(NPower).GetMethod("OnHovered", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(power, null);
                try
                {
                    for (int i = 0; i < 15; i++) await frame();
                    string path = Path.Combine(directory, $"native-escape-{power.Model.Amount}-{locale}.png");
                    TestCapture.Save(path);
                    results.Add(new { locale, amount = power.Model.Amount, path,
                        tips = power.Model.HoverTips.Select(HoverTipText.From).ToArray() });
                }
                finally { typeof(NPower).GetMethod("OnUnhovered", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(power, null); }
            }
        }
        finally { LocManager.Instance.SetLanguage(language); }
        for (int i = 0; i < 15; i++) await frame();
        return new { language, results };
    }
}
