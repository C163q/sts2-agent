using System.Text.Json;
using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class UiInspectionChecks
{
    public static void Run(string reportPath)
    {
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        var room = NCombatRoom.Instance!;
        var bar = NRun.Instance!.GlobalUi.TopBar;
        string language = LocManager.Instance.Language;
        var source = new LocString("static_hover_tips", "ENERGY_COUNT.title");
        string originalTitle = source.GetFormattedText();
        var energy = VisibleUi.Descendants<NEnergyCounter>(room.Ui.EnergyCounterContainer).First();
        var cachedTipField = typeof(NEnergyCounter).GetField("_hoverTip", BindingFlags.NonPublic | BindingFlags.Instance)!;
        var cachedTip = (HoverTip)cachedTipField.GetValue(energy)!;
        string? cachedTitle = cachedTip.Title;
        string cachedDescription = cachedTip.Description;
        var tips = UiInspection.Read();
        Check("english_energy_tip", tips.Any(tip => tip.title == "Energy" && tip.description.Contains("<Energy>")));
        Check("only_ui_sources", tips.SelectMany(tip => tip.sources).All(path =>
            !path.Contains("potion") && !path.Contains("power") && !path.Contains("relic")
            && !path.Contains("intents") && !path.Contains("hand") && !path.Contains("block")));
        Check("tips_have_unique_sources", tips.All(tip => tip.sources.Length > 0
            && tip.sources.Distinct().Count() == tip.sources.Length));
        Check("shared_tips_are_unique", tips.Select(tip => (tip.title, tip.description)).Distinct().Count() == tips.Length);
        Check("portrait_tip_respects_show_tip", bar.PortraitTip.ShowTip
            || !tips.Any(tip => tip.sources.Contains("player.character")));
        Check("hidden_stars_are_excluded", VisibleUi.Descendants<NStarCounter>(room.Ui).Any(VisibleUi.OnScreen)
            || !tips.Any(tip => tip.sources.Contains("player.stars")));
        var player = LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()!)!;
        var ascension = EnglishCardText.Read(() => AscensionHelper.GetHoverTip(player.Character, 6, false));
        Check("english_ascension_template", ascension.Title?.Contains("Ironclad") == true
            && ascension.Description.Length > 0 && !ascension.Description.Any(character => character >= '\u4e00' && character <= '\u9fff'));
        bool energyVisible = energy.Visible;
        bool buttonVisible = room.Ui.EndTurnButton.Visible;
        try
        {
            energy.Visible = false;
            room.Ui.EndTurnButton.Visible = false;
            var hidden = UiInspection.Read();
            Check("hidden_energy_is_excluded", !hidden.Any(tip => tip.sources.Contains("player.energy")));
            Check("hidden_end_turn_is_excluded", !hidden.Any(tip => tip.sources.Contains("buttons.end_turn")));
            energy.Visible = energyVisible;
            Vector2 position = energy.Position;
            try
            {
                energy.Position = new Vector2(-10000, -10000);
                Check("offscreen_energy_is_excluded", !UiInspection.Read().Any(tip => tip.sources.Contains("player.energy")));
            }
            finally { energy.Position = position; }
        }
        finally
        {
            energy.Visible = energyVisible;
            room.Ui.EndTurnButton.Visible = buttonVisible;
        }
        NCombatCardPile[] piles = [room.Ui.DrawPile, room.Ui.DiscardPile, room.Ui.ExhaustPile];
        bool[] enabledPiles = piles.Select(pile => pile.IsEnabled).ToArray();
        bool enabledEndTurn = room.Ui.EndTurnButton.IsEnabled;
        try
        {
            foreach (var pile in piles)
                pile.Disable();
            room.Ui.EndTurnButton.Disable();
            var disabled = UiInspection.Read();
            Check("disabled_piles_are_excluded", !disabled.Any(tip => tip.sources.Any(path =>
                path is "player.draw_count" or "player.discard_count" or "player.exhaust_count")));
            Check("disabled_end_turn_is_excluded", !disabled.Any(tip => tip.sources.Contains("buttons.end_turn")));
        }
        finally
        {
            for (int i = 0; i < piles.Length; i++)
                if (enabledPiles[i]) piles[i].Enable(); else piles[i].Disable();
            if (enabledEndTurn) room.Ui.EndTurnButton.Enable(); else room.Ui.EndTurnButton.Disable();
        }
        Check("locale_unchanged", language == LocManager.Instance.Language && source.GetFormattedText() == originalTitle);
        var afterTip = (HoverTip)cachedTipField.GetValue(energy)!;
        Check("cached_ui_tip_unchanged", afterTip.Title == cachedTitle && afterTip.Description == cachedDescription);
        Check("read_is_repeatable", JsonSerializer.Serialize(tips) == JsonSerializer.Serialize(UiInspection.Read()));
        File.WriteAllText(reportPath, JsonSerializer.Serialize(new { language, results },
            new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("UI inspection checks failed; see the local report.");
    }
}
