using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class SelectionObservationChecks
{
    public static object Run(CombatObservation observation, Func<string> observe)
    {
        var selection = CardSelection.Current!;
        var reader = new SelectionInspection(observation);
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        JsonElement Read(bool full = false) => JsonSerializer.SerializeToElement(reader.Read(selection, full));
        string before = observe();
        if (selection.InPreview)
        {
            var after = DeckUpgradeSelection.Previews(selection).Single().after;
            var field = HarmonyLib.AccessTools.Field(typeof(NCard), "_visibility");
            var original = after.Visibility;
            try
            {
                foreach (var hidden in new[] { ModelVisibility.NotSeen, ModelVisibility.Locked })
                {
                    field.SetValue(after, hidden);
                    foreach (bool full in new[] { false, true })
                        Check($"preview {hidden} does not reveal upgraded effect ({full})",
                            Read(full).GetProperty("upgrade_previews")[0].GetProperty("after")
                                .GetProperty("description").ValueKind == JsonValueKind.Null);
                }
            }
            finally { field.SetValue(after, original); }
            Check("preview checks restore UI", before == observe());
            return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
        }
        Check("complete basic candidates", Read().GetProperty("cards").GetArrayLength() == 40);
        Check("complete detail candidates", Read(true).GetProperty("cards").GetArrayLength() == 40);
        Check("basic cards do not include hover help", Read().GetProperty("cards").EnumerateArray()
            .All(card => !card.TryGetProperty("hover_tips", out _)));
        var holder = selection.Holders.First(h => CombatObservation.CardVisible(h.CardNode)
            && h.CardNode!.Model!.Enchantment != null);
        var node = holder.CardNode!;
        int id = observation.CardId(holder.CardModel!);
        var visibility = HarmonyLib.AccessTools.Field(typeof(NCard), "_visibility");
        var originalVisibility = node.Visibility;
        try
        {
            foreach (var hidden in new[] { ModelVisibility.NotSeen, ModelVisibility.Locked })
            {
                visibility.SetValue(node, hidden);
                foreach (bool full in new[] { false, true })
                {
                    var card = Read(full).GetProperty("cards").EnumerateArray().Single(c => c.GetProperty("id").GetInt32() == id);
                    Check($"{hidden} does not reveal card attributes ({full})", (!card.TryGetProperty("enchantment", out var effect)
                        || effect.ValueKind == JsonValueKind.Null)
                        && card.GetProperty("type").ValueKind == JsonValueKind.Null
                        && card.GetProperty("description").ValueKind == JsonValueKind.Null);
                }
            }
        }
        finally { visibility.SetValue(node, originalVisibility); }
        var visibleCard = Read().GetProperty("cards").EnumerateArray().Single(card => card.GetProperty("id").GetInt32() == id);
        var energyIcon = node.GetNode<Control>("%EnergyIcon");
        var iconPosition = energyIcon.Position;
        try
        {
            energyIcon.Position += new Vector2(-10000, 0);
            var clipped = Read().GetProperty("cards").EnumerateArray().Single(card => card.GetProperty("id").GetInt32() == id);
            Check("partly clipped candidate retains browsable cost", clipped.GetProperty("energy_cost").GetRawText()
                == visibleCard.GetProperty("energy_cost").GetRawText());
        }
        finally { energyIcon.Position = iconPosition; }
        var tabPosition = node.EnchantmentTab.Position;
        try
        {
            node.EnchantmentTab.Position += new Vector2(-10000, 0);
            var clipped = Read().GetProperty("cards").EnumerateArray().Single(card => card.GetProperty("id").GetInt32() == id);
            Check("partly clipped candidate retains browsable enchantment", clipped.TryGetProperty("enchantment", out var enchantment)
                && enchantment.GetRawText() == visibleCard.GetProperty("enchantment").GetRawText());
        }
        finally { node.EnchantmentTab.Position = tabPosition; }
        bool shown = selection.Owner.Visible;
        try
        {
            selection.Owner.Visible = false;
            var hidden = Read();
            Check("covered grid does not expose candidates", hidden.GetProperty("status").GetString() == "covered"
                && hidden.GetProperty("cards").ValueKind == JsonValueKind.Null && hidden.GetProperty("options").GetArrayLength() == 0);
        }
        finally { selection.Owner.Visible = shown; }
        Check("preview reads preserve originals and UI", before == observe());
        return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
    }
}
