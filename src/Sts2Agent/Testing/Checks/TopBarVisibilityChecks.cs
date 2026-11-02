using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.sts2.Core.Nodes.TopBar;

namespace Sts2Agent;

internal static class TopBarVisibilityChecks
{
    public static object Run(CombatObservation observation, Func<string> observe)
    {
        var bar = NRun.Instance!.GlobalUi.TopBar;
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        JsonElement Read() => JsonSerializer.SerializeToElement(observation.TopBar());
        string before = observe();
        Check("exposed top bar is readable", RunUi.TopBarReadable() && Read().ValueKind == JsonValueKind.Object);
        void Hidden(CanvasItem item, string name, Func<bool> condition)
        {
            bool visible = item.Visible;
            try { item.Visible = false; Check(name, condition()); }
            finally { item.Visible = visible; }
        }
        Hidden(bar, "hidden bar is not readable", () => Read().ValueKind == JsonValueKind.Null);
        Hidden(bar, "hidden inventory is not inferred", () => RelicInspection.HeldCount() == null
            && RelicInspection.VisibleHolders() == null && PotionInspection.VisibleHolders() == null);
        Color color = bar.Modulate;
        try
        {
            bar.Modulate = new Color(color, 0);
            Check("transparent bar is not readable", Read().ValueKind == JsonValueKind.Null);
        }
        finally { bar.Modulate = color; }
        Vector2 position = bar.Position;
        try
        {
            bar.Position += new Vector2(10000, 0);
            Check("offscreen bar is not readable", Read().ValueKind == JsonValueKind.Null);
        }
        finally { bar.Position = position; }
        var gold = bar.Gold.GetNode<Label>("%GoldLabel");
        Hidden(gold, "hidden gold does not use model value", () => Read().GetProperty("gold").ValueKind == JsonValueKind.Null
            && Read().GetProperty("hp").ValueKind == JsonValueKind.Number);
        string text = gold.Text;
        try
        {
            gold.Text = "17";
            Check("gold comes from visible label", Read().GetProperty("gold").GetInt32() == 17);
        }
        finally { gold.Text = text; }
        var health = VisibleUi.Descendants<NTopBarHp>(bar).Single().GetNode<Label>("%HpLabel");
        Hidden(health, "hidden health does not use model values", () => Read().GetProperty("hp").ValueKind == JsonValueKind.Null
            && Read().GetProperty("max_hp").ValueKind == JsonValueKind.Null
            && Read().GetProperty("gold").ValueKind == JsonValueKind.Number);
        var full = JsonSerializer.Deserialize<JsonElement>(observe());
        Check("details match current native hover availability",
            full.GetProperty("available_actions").EnumerateArray().Any(a => a.GetString() == "inspect_potions")
                == (PotionInspection.VisibleHolders() != null)
            && full.GetProperty("available_actions").EnumerateArray().Any(a => a.GetString() == "inspect_relics")
                == (RelicInspection.VisibleHolders() != null));
        Check("checks restore UI and observation", before == observe());
        return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
    }
}
