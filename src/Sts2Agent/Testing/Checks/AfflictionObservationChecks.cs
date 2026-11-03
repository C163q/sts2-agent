using System.Text.Json;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class AfflictionObservationChecks
{
    public static object Run(CombatObservation reader, Func<string> observe)
    {
        List<object> checks = [];
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        JsonElement Read(NCard card) => JsonSerializer.SerializeToElement(reader.Card(card));
        bool Absent(NCard card) => Read(card).GetProperty("affliction").ValueKind == JsonValueKind.Null;
        string before = observe();
        foreach (var card in CombatObservation.HandCards(NCombatRoom.Instance!.Ui.Hand))
        {
            if (card.Model!.Affliction == null) { Check("plain card null", Absent(card)); continue; }
            var effect = Read(card).GetProperty("affliction");
            string name = card.Model.Affliction.Id.Entry == "BOUND" ? "Bound" : "Smog";
            Check(name + " visible name only", effect.GetRawText() == JsonSerializer.Serialize(new { name }));
            if (name == "Bound") Check("coexists with enchantment", Read(card).GetProperty("enchantment").ValueKind == JsonValueKind.Object);
            var overlay = (Control)CardSelection.Field(card, "_cardOverlay")!;
            bool shown = overlay.Visible;
            try { overlay.Visible = false; Check(name + " hidden overlay", Absent(card)); }
            finally { overlay.Visible = shown; }
            var modulate = overlay.Modulate;
            try { overlay.Modulate = new Color(1, 1, 1, 0); Check(name + " transparent overlay", Absent(card)); }
            finally { overlay.Modulate = modulate; }
            var position = overlay.Position;
            try { overlay.Position += new Vector2(-10000, 0); Check(name + " offscreen overlay", Absent(card)); }
            finally { overlay.Position = position; }
            var field = AccessTools.Field(typeof(NCard), "_visibility");
            var visibility = card.Visibility;
            try
            {
                foreach (var hidden in new[] { ModelVisibility.NotSeen, ModelVisibility.Locked })
                {
                    field.SetValue(card, hidden);
                    Check(name + " unidentified " + hidden, Absent(card)
                        && Read(card).GetProperty("enchantment").ValueKind == JsonValueKind.Null);
                }
            }
            finally { field.SetValue(card, visibility); }
        }
        Check("sampling preserves UI and state", before == observe());
        return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
    }
}
