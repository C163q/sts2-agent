using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.ControllerInput;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.sts2.Core.Nodes.TopBar;

namespace Sts2Agent;

internal static class UiInspection
{
    private const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;
    private static readonly MethodInfo RoomTipPrefix = typeof(NTopBarRoomIcon)
        .GetMethod("GetHoverTipPrefixForRoomType", PrivateInstance)!;
    private static readonly FieldInfo BoundPile = typeof(NCombatCardPile).GetField("_pile", PrivateInstance)!;
    private static bool Hoverable(CanvasItem node) => VisibleUi.OnScreen(node)
        && (node is not NClickableControl clickable || HoverAccess.CanFocus(clickable));

    public static bool CanRead() => RunUi.TopBarReadable() || CombatObservation.Status() == "visible";
    public static HoverTextSources.Tip[] Read() => EnglishCardText.Read(ReadEnglish);

    private static HoverTextSources.Tip[] ReadEnglish()
    {
        if (!CanRead()) throw new InvalidOperationException("UI details require an exposed UI region.");
        var tips = new TipCollector();
        if (RunUi.TopBarReadable()) ReadTopBar(tips);
        if (CombatObservation.Status() == "visible") ReadCombat(tips);
        return tips.Items.ToArray();
    }

    private static void ReadTopBar(TipCollector tips)
    {
        var bar = NRun.Instance!.GlobalUi.TopBar;
        var run = RunManager.Instance.DebugOnlyGetState()!;
        var player = LocalContext.GetMe(run)!;
        if (VisibleUi.OnScreen(bar.Portrait) && Hoverable(bar.PortraitTip) && bar.PortraitTip.ShowTip)
            tips.Add(AscensionHelper.GetHoverTip(player.Character, run.AscensionLevel,
                run.GameMode.AreAchievementsAndEpochsLocked()), "top_bar.ascension");
        tips.Static(bar.Hp, "HIT_POINTS", ["top_bar.hp", "top_bar.max_hp"]);
        tips.Static(bar.Gold, "MONEY_POUCH", ["top_bar.gold"]);
        if (VisibleUi.OnScreen(bar.RoomIcon.GetNodeOrNull<TextureRect>("Icon")))
            tips.Static(bar.RoomIcon, (string)RoomTipPrefix.Invoke(bar.RoomIcon, null)!, ["top_bar.room_icon"]);
        tips.Static(bar.FloorIcon, "FLOOR", ["top_bar.floor"]);

        var visibleBosses = VisibleUi.Descendants<TextureRect>(bar.BossIcon)
            .Where(icon => icon.Name != "Outline" && VisibleUi.OnScreen(icon) && icon.Texture != null)
            .Select(icon => new[] { run.Act.BossEncounter, run.Act.SecondBossEncounter }.FirstOrDefault(boss =>
                boss != null && Path.GetFileNameWithoutExtension(icon.Texture!.ResourcePath)
                    .Equals(boss.Id.Entry, StringComparison.OrdinalIgnoreCase)))
            .Where(boss => boss != null).Distinct().ToArray();
        if (visibleBosses.Length > 0)
            tips.Static(bar.BossIcon, visibleBosses.Length == 2 ? "DOUBLE_BOSS" : "BOSS", ["top_bar.bosses"],
                configure: (title, description) =>
                {
                    for (int i = 0; i < visibleBosses.Length; i++)
                    {
                        string key = visibleBosses.Length == 1 ? "BossName" : "BossName" + (i + 1);
                        title.Add(key, visibleBosses[i]!.Title);
                        description.Add(key, visibleBosses[i]!.Title);
                    }
                });
        tips.Static(bar.Map, "MAP", ["top_bar.map_visible"], MegaInput.viewMap);
        tips.Static(bar.Deck, "DECK", ["top_bar.deck_visible", "top_bar.deck_count"], MegaInput.viewDeckAndTabLeft);
        tips.Static(bar.Pause, "SETTINGS", ["top_bar.settings_visible"]);

    }

    private static void ReadCombat(TipCollector tips)
    {
        var room = NCombatRoom.Instance!;
        var player = LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()!)!;
        foreach (var energy in VisibleUi.Descendants<NEnergyCounter>(room.Ui.EnergyCounterContainer))
            tips.Static(energy, "ENERGY_COUNT", ["player.energy", "player.max_energy"],
                configure: (_, description) => description.Add("energyPrefix", EnergyIconHelper.GetPrefix(player.Character.CardPool)));
        foreach (var stars in VisibleUi.Descendants<NStarCounter>(room.Ui))
            tips.Static(stars, "STAR_COUNT", ["player.stars"], configure: (_, description) =>
                description.Add("singleStarIcon", "[img]res://images/packed/sprite_fonts/star_icon.png[/img]"));

        var orbSlots = room.GetCreatureNode(player.Creature) is { } creature ? OrbInspection.VisibleNodes(creature) : null;
        for (int i = 0; i < (orbSlots?.Length ?? 0); i++)
            if (orbSlots![i].Model == null && OrbInspection.Hoverable(orbSlots[i]))
                tips.Add(OrbModel.EmptySlotHoverTipHoverTip, $"player.orb_slots.{OrbInspection.ArrayIndex(i, orbSlots.Length)}");

        void Pile(NCombatCardPile pile, string key, string source)
        {
            if (!VisibleUi.OnScreen(pile) || BoundPile.GetValue(pile) == null)
                return;
            string? hotkey = ((string[]?)pile.GetType().GetProperty("Hotkeys", PrivateInstance)?.GetValue(pile))?.FirstOrDefault();
            tips.Static(pile, key, [source], configure: (title, _) => title.Add("Hotkey",
                hotkey == null ? "None" : NInputManager.Instance!.GetCurrentHotkey(hotkey).ToString()));
        }
        Pile(room.Ui.DrawPile, "DRAW_PILE", "player.draw_count");
        Pile(room.Ui.DiscardPile, "DISCARD_PILE", "player.discard_count");
        Pile(room.Ui.ExhaustPile, "EXHAUST_PILE", "player.exhaust_count");
        if (!CombatManager.Instance.IsPlayerReadyToEndTurn(player))
            tips.Static(room.Ui.EndTurnButton, "END_TURN", ["buttons.end_turn"], MegaInput.endTurn);
    }

    private sealed class TipCollector
    {
        private readonly HoverTextSources texts = new();
        public HoverTextSources.Tip[] Items => texts.Items;
        public void Add(HoverTip tip, params string[] sources)
        {
            string? title = tip.Title == null ? null : EnglishCardText.Plain(tip.Title);
            string description = EnglishCardText.Plain(tip.Description);
            texts.Add(title, description, sources);
        }

        public void Static(CanvasItem node, string key, string[] sources, string? hotkey = null,
            Action<LocString, LocString>? configure = null)
        {
            if (!Hoverable(node))
                return;
            var title = new LocString("static_hover_tips", key + ".title");
            var description = new LocString("static_hover_tips", key + ".description");
            if (hotkey != null)
                title.Add("Hotkey", NInputManager.Instance!.GetCurrentHotkey(hotkey).ToString());
            configure?.Invoke(title, description);
            Add(new HoverTip(title, description), sources);
        }

    }
}
