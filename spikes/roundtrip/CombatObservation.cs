using System.Text.RegularExpressions;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Potions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class CombatObservation
{
    private readonly EnglishText english = new();

    public static string Status()
    {
        var room = NCombatRoom.Instance;
        var global = NRun.Instance?.GlobalUi;
        if (room == null || global == null || !room.IsNodeReady() || !global.IsNodeReady())
            return "not_ready";
        if (global.CapstoneContainer.InUse || global.Overlays.ScreenCount > 0
            || NModalContainer.Instance?.OpenModal != null
            || VisibleUi.Shown(NGame.Instance?.InspectCardScreen)
            || VisibleUi.Shown(NGame.Instance?.InspectRelicScreen)
            || NGame.Instance!.Transition.InTransition
            || (VisibleUi.Shown(NGame.Instance.Transition)
                && NGame.Instance.Transition.Material is ShaderMaterial transitionMaterial
                && transitionMaterial.GetShaderParameter("threshold").AsSingle() > 0.000001f)
            || VisibleUi.Descendants<CanvasItem>(NGame.Instance.Transition).Any(VisibleUi.Shown))
            return "covered";
        return VisibleUi.Shown(room) ? "visible" : "hidden";
    }

    public object? Player(Player? player)
    {
        if (player == null || Status() != "visible")
            return null;
        var room = NCombatRoom.Instance!;
        NCreature? node = room.GetCreatureNode(player.Creature);
        if (!VisibleUi.Shown(node) || !VisibleUi.OnScreen(node!.Body))
            return null;
        var hp = Health(node!);
        string? energyText = VisibleUi.Descendants<NEnergyCounter>(room.Ui.EnergyCounterContainer)
            .Select(counter => VisibleUi.Text(counter, "Label")).FirstOrDefault(text => text != null);
        var energy = Pair(energyText);
        return new
        {
            character = player.Character.Id.Entry, name = english.Name(player.Character.Title),
            hp = hp.current, max_hp = hp.maximum, hp_text = hp.text, hp_infinite = hp.infinite, block = Block(node!),
            energy = energy.current, max_energy = energy.maximum,
            stars = VisibleUi.Descendants<NStarCounter>(room.Ui).Where(VisibleUi.OnScreen)
                .Select(counter => VisibleUi.Number(counter, "%CountLabel")).FirstOrDefault(),
            powers = Powers(node!),
            hand = VisibleUi.Shown(room.Ui.Hand) ? room.Ui.Hand.ActiveHolders
                .Where(holder => VisibleUi.Shown(holder) && VisibleUi.Shown(holder.CardNode)
                    && new[] { "%TitleLabel", "%Portrait", "%AncientPortrait", "%Frame" }
                        .Any(path => VisibleUi.OnScreen(holder.CardNode!.GetNodeOrNull<Control>(path))))
                .Select((holder, index) => Card(holder.CardNode!, index)).ToArray() : null,
            draw_count = VisibleUi.Number(room.Ui.DrawPile, "CountContainer/Count"),
            discard_count = VisibleUi.Number(room.Ui.DiscardPile, "CountContainer/Count"),
            exhaust_count = VisibleUi.Number(room.Ui.ExhaustPile, "CountContainer/Count")
        };
    }

    public object[]? Enemies()
    {
        if (Status() != "visible")
            return null;
        return NCombatRoom.Instance!.CreatureNodes.Concat(NCombatRoom.Instance.RemovingCreatureNodes).Distinct()
            .Where(node => node.Entity.IsMonster && VisibleUi.Shown(node) && VisibleUi.OnScreen(node.Body))
            .OrderBy(node => node.GlobalPosition.X).Select(Enemy).ToArray();
    }

    private object Enemy(NCreature node)
    {
        var hp = Health(node);
        return new
        {
            id = node.Entity.CombatId, model = node.Entity.ModelId.Entry,
            name = english.Name(node.Entity.Monster!.Title),
            hp = hp.current, max_hp = hp.maximum, hp_text = hp.text, hp_infinite = hp.infinite, block = Block(node),
            powers = Powers(node),
            intents = !VisibleUi.Shown(node.IntentContainer) ? null : node.IntentContainer.GetChildren()
                .OfType<NIntent>().Where(intent => VisibleUi.OnScreen(intent.GetNodeOrNull<Control>("%IntentHolder")))
                .Select(Intent).ToArray()
        };
    }

    private static object Intent(NIntent intent)
    {
        // Identify the rendered texture, never the monster's mutable next-move model.
        var sprite = intent.GetNodeOrNull<Sprite2D>("%Intent");
        string? path = VisibleUi.Shown(sprite) ? sprite?.Texture?.ResourcePath : null;
        string? category = path == null ? null : Regex.Match(path,
            @"intent_(attack_[1-5]|carddebuff|death_blow|megadebuff|buff|defend|escape|heal|hidden|sleep|statuscard|stunned|summon|unknown)").Groups[1].Value;
        category = category switch
        {
            "megadebuff" => "debuff", "carddebuff" => "card_debuff", "statuscard" => "status",
            "stunned" => "stun", "" => "unrecognized", _ => category
        };
        if (category?.StartsWith("attack_") == true)
            category = "attack";
        return new { category, value = VisibleUi.Text(intent, "%Value") };
    }

    private object Card(NCard card, int index)
    {
        bool identified = card.Visibility == ModelVisibility.Visible;
        string? title = VisibleUi.Text(card, "%TitleLabel");
        string? name = title == null ? null : !identified
            ? english.Entry("card_library", card.Visibility == ModelVisibility.Locked ? "LOCKED.title" : "UNKNOWN.title")
            : english.Name(card.Model!.TitleLocString);
        if (identified && name != null && title != null)
        {
            // The suffix is visible text; do not expose the hidden upgrade level separately.
            string suffix = Regex.Match(title, @"\+\d*$").Value;
            name += suffix;
        }
        var highlight = card.CardHighlight;
        bool glow = VisibleUi.OnScreen(highlight) && highlight.Material is ShaderMaterial shader
            && shader.GetShaderParameter("width").AsSingle() > 0;
        return new
        {
            position = index, model = identified ? card.Model!.Id.Entry : null, name,
            type = VisibleUi.Text(card, "%TypeLabel") is string typeText && identified
                && typeText == card.Model!.Type.ToLocString().GetFormattedText()
                ? english.Name(card.Model.Type.ToLocString()) : null,
            energy_cost = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%EnergyIcon"))
                ? VisibleUi.Text(card, "%EnergyLabel") : null,
            energy_cost_color = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%EnergyIcon"))
                ? VisibleUi.TextColor(card, "%EnergyLabel") : null,
            star_cost = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%StarIcon"))
                ? VisibleUi.Text(card, "%StarLabel") : null,
            star_cost_color = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%StarIcon"))
                ? VisibleUi.TextColor(card, "%StarLabel") : null,
            energy_unplayable_marker = VisibleUi.OnScreen(card.GetNodeOrNull<CanvasItem>("%UnplayableEnergyIcon")),
            star_unplayable_marker = VisibleUi.OnScreen(card.GetNodeOrNull<CanvasItem>("%UnplayableStarIcon")),
            outline = !glow ? null : highlight.Modulate.IsEqualApprox(NCardHighlight.playableColor) ? "cyan"
                : highlight.Modulate.IsEqualApprox(NCardHighlight.gold) ? "gold"
                : highlight.Modulate.IsEqualApprox(NCardHighlight.red) ? "red" : "other"
        };
    }

    private object[]? Powers(NCreature node)
    {
        var container = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")
            ?.GetNodeOrNull<NPowerContainer>("%PowerContainer");
        if (!VisibleUi.Shown(container))
            return null;
        return container!.GetChildren().OfType<NPower>()
            .Where(power => VisibleUi.OnScreen(power) && power.Model.IsVisible)
            .Select(power => (object)new { name = english.Name(power.Model.Title),
                amount = VisibleUi.Number(power, "%AmountLabel") }).ToArray();
    }

    private (int? current, int? maximum, string? text, bool? infinite) Health(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        string? text = VisibleUi.Text(bar, "%HpLabel");
        var pair = Pair(text);
        if (text != null && !pair.current.HasValue)
            text = text == new LocString("gameplay_ui", "HEALTH_BAR.DEAD").GetFormattedText()
                ? english.Entry("gameplay_ui", "HEALTH_BAR.DEAD") : null;
        return (pair.current, pair.maximum, text, !VisibleUi.Shown(bar) ? null
            : VisibleUi.OnScreen(bar?.GetNodeOrNull<TextureRect>("%InfinityTex")));
    }

    private static int? Block(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        if (!VisibleUi.Shown(bar) || !VisibleUi.OnScreen(bar!.HpBarContainer))
            return null;
        return VisibleUi.Shown(bar?.GetNodeOrNull<Control>("%BlockContainer"))
            ? VisibleUi.Number(bar, "%BlockLabel") : 0;
    }

    private static (int? current, int? maximum) Pair(string? text)
    {
        string[] parts = text?.Split('/') ?? [];
        return parts.Length == 2 && int.TryParse(parts[0], out int current) && int.TryParse(parts[1], out int maximum)
            ? (current, maximum) : (null, null);
    }

    public int? Turn()
    {
        string? text = Status() == "visible" ? VisibleUi.Text(NCombatRoom.Instance?.Ui.EndTurnButton, "Visuals/Label") : null;
        return int.TryParse(Regex.Match(text ?? "", @"\d+").Value, out int turn) ? turn : null;
    }

    public object? Buttons()
    {
        if (Status() != "visible")
            return null;
        var button = NCombatRoom.Instance!.Ui.EndTurnButton;
        string? text = VisibleUi.Text(button, "Visuals/Label");
        return new { end_turn = !VisibleUi.OnScreen(button) ? null : new
            { text = english.Button(text, Turn()), enabled = button.IsEnabled } };
    }

    public object? TopBar()
    {
        if (Status() != "visible")
            return null;
        var global = NRun.Instance!.GlobalUi;
        var bar = global.TopBar;
        var run = RunManager.Instance.DebugOnlyGetState();
        return new
        {
            gold = VisibleUi.Number(bar.Gold, "%GoldLabel"),
            floor = VisibleUi.Number(bar.FloorIcon, "FloorNumLabel"),
            ascension = VisibleUi.Number(bar, "%AscensionLabel"),
            deck_count = VisibleUi.Number(bar.Deck, "DeckCardCount"),
            room_icon = Icon(bar.RoomIcon.GetNodeOrNull<TextureRect>("Icon")),
            boss_icons = VisibleUi.Descendants<TextureRect>(bar.BossIcon)
                .Where(icon => icon.Name != "Outline" && VisibleUi.OnScreen(icon) && icon.Texture != null)
                .Select(icon => new { icon = Icon(icon), name = BossName(icon.Texture!.ResourcePath, run) }).ToArray(),
            potion_slots = bar.PotionContainer.GetNodeOrNull<Control>("MarginContainer/PotionHolders")?
                .GetChildren().OfType<NPotionHolder>().Where(VisibleUi.OnScreen)
                .Select((holder, index) => new { position = index, empty = !holder.HasPotion,
                    name = holder.HasPotion ? english.Name(holder.Potion!.Model.Title) : null }).ToArray(),
            relics = VisibleUi.Shown(global.RelicInventory) ? global.RelicInventory.RelicNodes
                .Where(VisibleUi.OnScreen).Select((holder, index) => new
                {
                    position = index, name = english.Name(holder.Relic.Model.Title),
                    counter = VisibleUi.Number(holder, "%AmountLabel")
                }).ToArray() : null,
            map_visible = VisibleUi.OnScreen(bar.Map), deck_visible = VisibleUi.OnScreen(bar.Deck),
            settings_visible = VisibleUi.OnScreen(bar.Pause)
        };
    }

    private string? BossName(string texture, RunState? run)
    {
        if (run == null)
            return null;
        foreach (var boss in new[] { run.Act.BossEncounter, run.Act.SecondBossEncounter })
            if (boss != null && Path.GetFileNameWithoutExtension(texture).Equals(boss.Id.Entry, StringComparison.OrdinalIgnoreCase))
                return english.Name(boss.Title);
        return null;
    }

    private static string? Icon(TextureRect? icon) => VisibleUi.OnScreen(icon)
        ? Path.GetFileNameWithoutExtension(icon?.Texture?.ResourcePath) : null;

    public object? Overlay()
    {
        if (Status() != "visible")
            return null;
        // Only explicitly identified, currently displayed labels are included.
        return new
        {
            release = VisibleUi.Text(NRun.Instance!.GlobalUi, "DebugInfo/ReleaseInfo"),
            seed = VisibleUi.Text(NRun.Instance, "%DebugSeed"),
            modded = VisibleUi.Text(NRun.Instance.GlobalUi, "DebugInfo/ModdedWarning")
        };
    }
}
