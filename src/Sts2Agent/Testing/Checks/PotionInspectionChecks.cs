using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class PotionInspectionChecks
{
    public static object Run(string? reportPath, Func<string>? observe = null)
    {
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        var holders = PotionInspection.VisibleHolders()
            ?? throw new InvalidOperationException("Potion checks require a visible test belt.");
        var container = NRun.Instance!.GlobalUi.TopBar.PotionContainer;
        string language = LocManager.Instance.Language;
        var source = new LocString("static_hover_tips", "POTION_SLOT.title");
        string originalTitle = source.GetFormattedText();
        var cachedBefore = HoverTipFactory.FromPotion<SkillPotion>();
        var inspected = PotionInspection.Read(holders);
        Check("english_slot_tip", inspected.slot_tip!.title == "Potion Slot" && inspected.slot_tip!.description.Length > 0);
        Check("full_belt_still_has_slot_tip", inspected.potion_slots.Length == 3 && inspected.potion_slots.All(potion => potion != null));
        Check("skill_potion_text", inspected.potion_slots[0] is { name: "Skill Potion" } skill
            && skill.description!.Contains("3") && skill.description!.Contains("Skill") && skill.hover_tips.Length == 0);
        Check("block_potion_extra_tip", inspected.potion_slots[1]!.hover_tips.Any(tip => tip.title == "Block"));
        var energyPotion = ModelDb.Potion<EnergyPotion>().ToMutable();
        energyPotion.Owner = LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()!)!;
        var energy = energyPotion.DynamicVars.Values.OfType<EnergyVar>().First();
        string originalPrefix = energy.ColorPrefix;
        try
        {
            energy.ColorPrefix = "test-prefix";
            var detail = PotionInspection.Details(energyPotion);
            Check("potion_energy_icon", detail.description!.Contains("<Energy>"));
            Check("energy_prefix_restored", energy.ColorPrefix == "test-prefix");
            EnglishCardText.Read(() => HoverTipText.WithPotionValues(energyPotion, () => HoverTipFactory.FromPotion(energyPotion)));
            Check("nested_potion_tip_restores_prefix", energy.ColorPrefix == "test-prefix");
        }
        finally { energy.ColorPrefix = originalPrefix; }
        void Hidden(CanvasItem item, string name)
        {
            bool visible = item.Visible;
            try
            {
                item.Visible = false;
                Check(name, PotionInspection.VisibleHolders() == null);
                if (observe != null)
                {
                    using var state = JsonDocument.Parse(observe());
                    Check(name + "_basic_unknown", state.RootElement.GetProperty("top_bar").GetProperty("potion_slots").ValueKind == JsonValueKind.Null);
                }
            }
            finally { item.Visible = visible; }
        }
        Hidden(container, "hidden_belt_is_unavailable");
        Hidden(holders[0], "hidden_slot_does_not_shift_indices");
        Hidden(holders[0].Potion!.GetNode<TextureRect>("%Image"), "hidden_potion_is_not_read");
        bool enabled = holders[0].IsEnabled;
        Vector2 position = holders[0].Position;
        try
        {
            holders[0].Disable();
            Check("disabled_slot_keeps_static_identity", PotionInspection.VisibleHolders() != null
                && PotionInspection.Read(holders).potion_slots[0] is { name: "Skill Potion", description: null });
            if (enabled) holders[0].Enable();
            holders[0].Position = new Vector2(-10000, -10000);
            Check("offscreen_slot_is_readable", PotionInspection.VisibleHolders() != null);
            Check("offscreen_slot_cannot_be_clicked", PotionActions.Find(0) == null);
            if (observe != null)
            {
                using var state = JsonDocument.Parse(observe());
                var slots = state.RootElement.GetProperty("top_bar").GetProperty("potion_slots");
                Check("offscreen_slot_basic_identity", slots.ValueKind == JsonValueKind.Array && slots[0].GetProperty("name").GetString() == "Skill Potion");
            }
        }
        finally
        {
            holders[0].Position = position;
            if (enabled) holders[0].Enable(); else holders[0].Disable();
        }
        var mouse = holders[0].MouseFilter;
        var focus = holders[0].FocusMode;
        try
        {
            holders[0].MouseFilter = Control.MouseFilterEnum.Ignore;
            holders[0].FocusMode = Control.FocusModeEnum.None;
            Check("no_hover_entry_keeps_static_identity", PotionInspection.VisibleHolders() != null
                && PotionInspection.Read(holders).potion_slots[0] is { name: "Skill Potion", description: null });
            List<string> types = [];
            using var journal = new PotionJournal(LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()!)!, (type, _) => types.Add(type));
            typeof(PotionJournal).GetMethod("Used", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)!
                .Invoke(journal, [holders[0].Potion!.Model]);
            Check("visible_automatic_potion_event_does_not_require_hover", types.SequenceEqual(["potion_used"]));
        }
        finally { holders[0].MouseFilter = mouse; holders[0].FocusMode = focus; }
        var image = holders[0].Potion!.GetNode<TextureRect>("%Image");
        var texture = image.Texture;
        try
        {
            image.Texture = null;
            Check("missing_texture_is_unknown", PotionInspection.VisibleHolders() == null);
        }
        finally { image.Texture = texture; }
        var summary = PotionInspection.Read(holders, full: false);
        Check("summary_skips_all_hover_text", summary.slot_tip == null && summary.unavailable_hover_sources.Length == 0
            && summary.potion_slots.All(slot => slot == null || slot.description == null && slot.hover_tips.Length == 0));
        var scale = image.Scale;
        try { image.Scale = Vector2.Zero; Check("zero_scale_icon_is_unknown", PotionInspection.VisibleHolders() == null); }
        finally { image.Scale = scale; }
        var color = image.Modulate;
        try { image.Modulate = new Color(color, 0); Check("transparent_icon_is_unknown", PotionInspection.VisibleHolders() == null); }
        finally { image.Modulate = color; }
        bool clip = holders[0].ClipContents;
        Vector2 imagePosition = image.Position;
        try
        {
            holders[0].ClipContents = true;
            image.Position = new Vector2(10000, 10000);
            Check("actually_clipped_icon_is_unknown", PotionInspection.VisibleHolders() == null);
        }
        finally { holders[0].ClipContents = clip; image.Position = imagePosition; }
        Check("locale_unchanged", language == LocManager.Instance.Language && source.GetFormattedText() == originalTitle);
        Check("potion_cache_unchanged", HoverTipFactory.FromPotion<SkillPotion>().Equals(cachedBefore));
        Check("read_is_repeatable", JsonSerializer.Serialize(inspected) == JsonSerializer.Serialize(PotionInspection.Read(holders)));
        var report = new { language, results };
        if (reportPath != null) File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Potion inspection checks failed: " + JsonSerializer.Serialize(report));
        return report;
    }
}
