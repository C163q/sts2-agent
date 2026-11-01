using System.Reflection;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class EnchantmentObservationChecks
{
    public static object Run()
    {
        var cards = NCombatRoom.Instance!.Ui.Hand.ActiveHolders.Select(holder => holder.CardNode!).ToArray();
        var sharp = cards.Single(card => card.Model!.Enchantment?.Id.Entry == "SHARP");
        var swift = cards.Single(card => card.Model!.Enchantment?.Id.Entry == "SWIFT");
        var clone = cards.Single(card => card.Model!.Enchantment?.Id.Entry == "CLONE");
        var plain = cards.Single(card => card.Model!.Enchantment == null);
        var reader = new CombatObservation();
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        JsonElement Read(NCard card) => JsonSerializer.SerializeToElement(reader.Card(card));
        JsonElement Enchantment(NCard card) => Read(card).TryGetProperty("enchantment", out var value) ? value : default;
        bool Value(NCard card, string key, object expected) => Enchantment(card).ValueKind == JsonValueKind.Object
            && Enchantment(card).TryGetProperty(key, out var value) && value.GetRawText() == JsonSerializer.Serialize(expected);
        bool Absent(NCard card) => !Read(card).TryGetProperty("enchantment", out _);
        string before = Read(sharp).GetRawText();
        Check("visible_name", Value(sharp, "name", "Sharp"));
        Check("visible_amount", Value(sharp, "amount", 3));
        Check("normal_icon", Value(sharp, "dimmed", false));
        Check("disabled_icon", Value(swift, "dimmed", true));
        Check("no_enchantment", Absent(plain));
        Check("unshown_model_amount_omitted", Value(clone, "name", "Clone")
            && !Enchantment(clone).TryGetProperty("amount", out _));
        var tab = sharp.EnchantmentTab;
        var icon = sharp.GetNode<TextureRect>("%Enchantment/Icon");
        var label = sharp.GetNode<Label>("%Enchantment/Label");
        void Hidden(CanvasItem item, string name, Func<bool> check)
        {
            bool visible = item.Visible;
            try { item.Visible = false; Check(name, check()); }
            finally { item.Visible = visible; }
        }
        Hidden(tab, "hidden_tab", () => Absent(sharp));
        Hidden(icon, "hidden_icon", () => Absent(sharp));
        Hidden(sharp, "hidden_card", () => Absent(sharp));
        Hidden(label, "hidden_amount", () => Value(sharp, "name", "Sharp") && !Enchantment(sharp).TryGetProperty("amount", out _));
        string text = label.Text;
        try { label.Text = "73"; Check("amount_comes_from_label", Value(sharp, "amount", 73)); }
        finally { label.Text = text; }
        Vector2 position = tab.Position;
        try { tab.Position += new Vector2(-10000, 0); Check("offscreen_tab", Absent(sharp)); }
        finally { tab.Position = position; }
        var texture = icon.Texture;
        try { icon.Texture = null; Check("missing_icon", Absent(sharp)); }
        finally { icon.Texture = texture; }
        bool material = icon.UseParentMaterial;
        var shader = (ShaderMaterial)tab.Material;
        var saturation = shader.GetShaderParameter("s");
        try
        {
            icon.UseParentMaterial = true;
            shader.SetShaderParameter("s", 0.1f);
            Check("dimmed_comes_from_ui", Value(sharp, "dimmed", true));
        }
        finally { icon.UseParentMaterial = material; shader.SetShaderParameter("s", saturation); }
        var visibility = typeof(NCard).GetField("_visibility", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var original = sharp.Visibility;
        try
        {
            foreach (var hidden in new[] { ModelVisibility.NotSeen, ModelVisibility.Locked })
            {
                // Keep the icon visible while testing the independent identity boundary.
                visibility.SetValue(sharp, hidden);
                Check("anonymous_" + hidden, Absent(sharp));
            }
        }
        finally { visibility.SetValue(sharp, original); }
        Check("read_and_checks_restore_ui", before == Read(sharp).GetRawText());
        return new { results, passed = results.All(result => JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()) };
    }
}
