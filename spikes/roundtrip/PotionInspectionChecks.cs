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
    public static void Run(string reportPath)
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
        Check("english_slot_tip", inspected.slot_tip.title == "Potion Slot" && inspected.slot_tip.description.Length > 0);
        Check("full_belt_still_has_slot_tip", inspected.potion_slots.Length == 3 && inspected.potion_slots.All(potion => potion != null));
        Check("skill_potion_text", inspected.potion_slots[0] is { name: "Skill Potion" } skill
            && skill.description.Contains("3") && skill.description.Contains("Skill") && skill.hover_tips.Length == 0);
        Check("block_potion_extra_tip", inspected.potion_slots[1]!.hover_tips.Any(tip => tip.title == "Block"));
        var energyPotion = ModelDb.Potion<EnergyPotion>().ToMutable();
        energyPotion.Owner = LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()!)!;
        var energy = energyPotion.DynamicVars.Values.OfType<EnergyVar>().First();
        string originalPrefix = energy.ColorPrefix;
        try
        {
            energy.ColorPrefix = "test-prefix";
            var detail = PotionInspection.Details(energyPotion);
            Check("potion_energy_icon", detail.description.Contains("<Energy>"));
            Check("energy_prefix_restored", energy.ColorPrefix == "test-prefix");
            EnglishCardText.Read(() => HoverTipFactory.FromPotion(energyPotion));
            Check("nested_potion_tip_restores_prefix", energy.ColorPrefix == "test-prefix");
        }
        finally { energy.ColorPrefix = originalPrefix; }
        void Hidden(CanvasItem item, string name)
        {
            bool visible = item.Visible;
            try { item.Visible = false; Check(name, PotionInspection.VisibleHolders() == null); }
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
            Check("disabled_slot_is_unavailable", PotionInspection.VisibleHolders() == null);
            if (enabled) holders[0].Enable();
            holders[0].Position = new Vector2(-10000, -10000);
            Check("offscreen_slot_is_unavailable", PotionInspection.VisibleHolders() == null);
        }
        finally
        {
            holders[0].Position = position;
            if (enabled) holders[0].Enable(); else holders[0].Disable();
        }
        Check("locale_unchanged", language == LocManager.Instance.Language && source.GetFormattedText() == originalTitle);
        Check("potion_cache_unchanged", HoverTipFactory.FromPotion<SkillPotion>().Equals(cachedBefore));
        Check("read_is_repeatable", JsonSerializer.Serialize(inspected) == JsonSerializer.Serialize(PotionInspection.Read(holders)));
        File.WriteAllText(reportPath, JsonSerializer.Serialize(new { language, results }, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Potion inspection checks failed; see the local report.");
    }
}
