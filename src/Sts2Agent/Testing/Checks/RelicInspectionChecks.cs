using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class RelicInspectionChecks
{
    public static void Run(string reportPath)
    {
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        var holders = RelicInspection.VisibleHolders()
            ?? throw new InvalidOperationException("Relic checks require a visible test inventory.");
        var inventory = NRun.Instance!.GlobalUi.RelicInventory;
        var counterHolder = holders.Single(holder => holder.Relic.Model is PenNib);
        var lantern = holders.Single(holder => holder.Relic.Model is Lantern).Relic.Model;
        string language = LocManager.Instance.Language;
        var localized = new LocString("relics", "BURNING_BLOOD.title");
        string originalTitle = localized.GetFormattedText();
        var keyword = HoverTipFactory.FromKeyword(CardKeyword.Exhaust);
        var energy = lantern.DynamicVars.Values.OfType<EnergyVar>().First();
        string prefix = energy.ColorPrefix;
        string originalTips = JsonSerializer.Serialize(lantern.HoverTips.Select(HoverTipText.From));
        energy.ColorPrefix = prefix;
        var before = RelicInspection.Read(holders);
        Check("english_burning_blood", before.Any(item => item.name == "Burning Blood"
            && item.description.Contains("6") && item.counter == null));
        Check("anchor_native_keyword", before.Any(item => item.name == "Anchor"
            && item.description.Contains("10") && item.hover_tips.Any(tip => tip.title == "Block")));
        Check("zero_counter_is_visible", before.Single(item => item.name == "Pen Nib").counter == 0);
        Check("energy_icon_and_tip", before.Any(item => item.name == "Lantern"
            && item.description.Contains("<Energy>") && item.hover_tips.Any(tip => tip.title == "Energy")));
        Check("english_text", before.All(item => !(item.name + item.description
            + string.Concat(item.hover_tips.Select(tip => tip.title + tip.description)))
            .Any(character => character >= '\u4e00' && character <= '\u9fff')));
        Check("read_preserves_energy_prefix", energy.ColorPrefix == prefix);
        try
        {
            energy.ColorPrefix = "test-prefix";
            Check("energy_format_uses_native_prefix", RelicInspection.Details(lantern, null).description.Contains("<Energy>"));
            Check("custom_energy_prefix_restored", energy.ColorPrefix == "test-prefix");
        }
        finally { energy.ColorPrefix = prefix; }
        var detached = ModelDb.Relic<Lantern>().ToMutable();
        detached.Owner = lantern.Owner;
        detached.IsMelted = true;
        string nativeMelted = EnglishCardText.Read(() => HoverTipText.From(detached.HoverTip).description);
        Check("melted_description_uses_native_wrapper", RelicInspection.Details(detached, null).description == nativeMelted
            && nativeMelted != before.Single(item => item.name == "Lantern").description);

        int count = holders.Length;
        void Hidden(CanvasItem node, string name, Func<bool> verify)
        {
            bool visible = node.Visible;
            try { node.Visible = false; Check(name, verify()); }
            finally { node.Visible = visible; }
        }
        Hidden(inventory, "hidden_inventory_is_unavailable", () => RelicInspection.VisibleHolders() == null);
        Hidden(counterHolder, "hidden_relic_is_excluded", () => RelicInspection.VisibleHolders()!.Length == count - 1);
        Hidden(counterHolder.Relic.Icon, "hidden_icon_is_excluded", () => RelicInspection.VisibleHolders()!.Length == count - 1);
        Hidden(counterHolder.GetNode<CanvasItem>("%AmountLabel"), "hidden_counter_is_unknown",
            () => RelicInspection.Read(RelicInspection.VisibleHolders()!).Single(item => item.name == "Pen Nib").counter == null);
        bool enabled = counterHolder.IsEnabled;
        var filter = counterHolder.MouseFilter;
        var position = counterHolder.Position;
        var modulate = counterHolder.Relic.Icon.SelfModulate;
        var texture = counterHolder.Relic.Icon.Texture;
        var scale = counterHolder.Relic.Icon.Scale;
        try
        {
            counterHolder.Disable();
            Check("disabled_holder_is_excluded", RelicInspection.VisibleHolders()!.Length == count - 1);
            if (enabled) counterHolder.Enable();
            counterHolder.MouseFilter = Control.MouseFilterEnum.Ignore;
            Check("non_hoverable_holder_is_excluded", RelicInspection.VisibleHolders()!.Length == count - 1);
            counterHolder.MouseFilter = filter;
            counterHolder.Position = new Vector2(-10000, -10000);
            Check("offscreen_relic_is_excluded", RelicInspection.VisibleHolders()!.Length == count - 1);
            counterHolder.Position = position;
            counterHolder.Relic.Icon.SelfModulate = new Color(1, 1, 1, 0);
            Check("transparent_icon_is_excluded", RelicInspection.VisibleHolders()!.Length == count - 1);
            counterHolder.Relic.Icon.SelfModulate = modulate;
            counterHolder.Relic.Icon.Texture = null;
            Check("missing_texture_is_excluded", RelicInspection.VisibleHolders()!.Length == count - 1);
        }
        finally
        {
            counterHolder.Position = position;
            counterHolder.Relic.Icon.SelfModulate = modulate;
            counterHolder.Relic.Icon.Texture = texture;
            if (enabled) counterHolder.Enable(); else counterHolder.Disable();
            counterHolder.MouseFilter = filter;
        }
        var visibility = holders.Select(holder => holder.Visible).ToArray();
        try
        {
            foreach (var holder in holders) holder.Visible = false;
            Check("no_visible_relics_is_empty", RelicInspection.Read(RelicInspection.VisibleHolders()!).Length == 0);
        }
        finally
        {
            for (int index = 0; index < holders.Length; index++) holders[index].Visible = visibility[index];
        }
        Check("locale_unchanged", language == LocManager.Instance.Language && localized.GetFormattedText() == originalTitle);
        Check("keyword_cache_unchanged", HoverTipFactory.FromKeyword(CardKeyword.Exhaust).Equals(keyword));
        Check("icon_not_animated", counterHolder.Relic.Icon.Scale == scale);
        Check("read_is_repeatable", JsonSerializer.Serialize(before) == JsonSerializer.Serialize(RelicInspection.Read(holders)));
        string afterTips = JsonSerializer.Serialize(lantern.HoverTips.Select(HoverTipText.From));
        energy.ColorPrefix = prefix;
        Check("original_chinese_tips_unchanged", afterTips == originalTips);
        File.WriteAllText(reportPath, JsonSerializer.Serialize(new { language, inspection = before, results },
            new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Relic inspection checks failed; see the local report.");
    }
}
