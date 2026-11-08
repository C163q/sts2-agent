using System.Text.RegularExpressions;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Helpers;
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
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.sts2.Core.Nodes.TopBar;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class CombatObservation
{
    private readonly EnglishText english = new();
    private readonly CardIdentityMap<CardModel> cardIds = new();
    private readonly Dictionary<CardModel, string> publicCardNames = [];
    internal string? KnownCardName(CardModel card) => publicCardNames.GetValueOrDefault(card);
    internal void RememberCardName(CardModel card, string name) => publicCardNames[card] = name;
    private CombatState? identityCombat;
    internal int CardId(CardModel card) => cardIds.Get(card);

    public void Synchronize(CombatState? combat, Player? player)
    {
        if (!ReferenceEquals(identityCombat, combat))
        {
            identityCombat = combat;
            cardIds.Clear();
            publicCardNames.Clear();
        }
        if (combat == null || player == null)
            return;
        // Only past local-player draws assign opaque IDs; no pile contents are read.
        foreach (var entry in CombatManager.Instance.History.Entries.OfType<CardDrawnEntry>())
            if (ReferenceEquals(entry.Card.Owner, player))
                cardIds.Get(entry.Card);
    }

    public static string Status(bool allowCardView = false, bool allowMap = false)
    {
        var room = NCombatRoom.Instance;
        var global = NRun.Instance?.GlobalUi;
        if (room == null || global == null || !room.IsNodeReady() || !global.IsNodeReady())
            return "not_ready";
        if ((global.CapstoneContainer.InUse && !(allowCardView
                && global.CapstoneContainer.CurrentCapstoneScreen is NDeckViewScreen or NCardPileScreen))
            || (VisibleUi.Shown(global.MapScreen) && !(allowMap && global.MapScreen.IsOpen && !global.MapScreen.IsTraveling))
            || (global.Overlays.ScreenCount > 0 && !CardSelection.BattlefieldOverlay)
            || CardSelection.Current is { Owner: NPlayerHand, Peeking: false }
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

    public CombatantInspection.Result Combatants(Player? player) =>
        CombatantInspection.Read(player, CardId, CombatantInspection.Level.Summary);

    public object? Player(Player? player, CombatantInspection.Result? common = null)
    {
        if (player == null || Status() != "visible")
            return null;
        common ??= Combatants(player);
        if (common.player == null) return null;
        var room = NCombatRoom.Instance!;
        NCreature? node = room.GetCreatureNode(player.Creature);
        if (!VisibleUi.Shown(node) || !VisibleUi.OnScreen(node!.Body))
            return null;
        var resources = CombatResources.Read();
        return new
        {
            character = player.Character.Id.Entry,
            common.player.hp, common.player.max_hp, common.player.hp_display, common.player.block,
            common.player.hp_preview,
            energy = resources.Energy, max_energy = resources.Maximum, stars = resources.Stars,
            powers = common.player.powers,
            orb_slots = common.player.orb_slots,
            sovereign_blades = common.player.sovereign_blades,
            hand = VisibleUi.Shown(room.Ui.Hand) ? HandCards(room.Ui.Hand).Select(Card).ToArray() : null,
            draw_count = resources.DrawCount,
            discard_count = resources.DiscardCount,
            exhaust_count = resources.ExhaustCount
        };
    }

    internal static bool CardVisible(NCard? card) => CardVisible(card, VisibleUi.OnScreen);

    internal static IEnumerable<NCard> HandCards(NPlayerHand hand) => hand.ActiveHolders
        .Where(holder => VisibleUi.Shown(holder) && CardVisible(holder.CardNode)).Select(holder => holder.CardNode!);

    internal static bool CardVisible(NCard? card, Func<CanvasItem?, bool> readable) => VisibleUi.Shown(card)
        && new[] { "%TitleLabel", "%Portrait", "%AncientPortrait", "%Frame" }
            .Any(path => readable(card!.GetNodeOrNull<Control>(path)));

    public object[]? Enemies(CombatantInspection.Result? common = null)
    {
        if (Status() != "visible")
            return null;
        common ??= Combatants(null);
        var nodes = EnemyNodes().ToArray();
        if (!nodes.Select(node => node.Entity.CombatId).SequenceEqual(common.enemies.Select(item => item.id)))
            throw new InvalidOperationException("Displayed enemies changed during observation.");
        return common.enemies.Cast<object>().ToArray();
    }

    internal static IEnumerable<NCreature> VisibleCreatureNodes() =>
        NCombatRoom.Instance!.CreatureNodes.Concat(NCombatRoom.Instance.RemovingCreatureNodes).Distinct()
            .Where(node => VisibleUi.Shown(node) && VisibleUi.OnScreen(node.Body))
            .OrderBy(node => node.GlobalPosition.X);

    internal static IEnumerable<NCreature> EnemyNodes() => VisibleCreatureNodes().Where(node => node.Entity.IsEnemy);
    internal static IEnumerable<NCreature> AllyNodes() => VisibleCreatureNodes()
        .Where(node => !node.Entity.IsPlayer && !node.Entity.IsEnemy);

    public object[]? Allies(CombatantInspection.Result? common = null)
    {
        if (Status() != "visible") return null;
        common ??= Combatants(null);
        var nodes = AllyNodes().ToArray();
        if (!nodes.Select(node => node.Entity.CombatId).SequenceEqual(common.allies.Select(item => item.id)))
            throw new InvalidOperationException("Displayed allies changed during observation.");
        return nodes.Select((node, index) =>
        {
            var shared = common.allies[index];
            var result = new Dictionary<string, object?>
            {
                ["id"] = shared.id, ["name"] = shared.name,
                ["hp"] = shared.hp, ["max_hp"] = shared.max_hp, ["hp_display"] = shared.hp_display,
                ["block"] = shared.block, ["powers"] = shared.powers, ["hp_preview"] = shared.hp_preview
            };
            if (shared.block_shared_with != null) result["block_shared_with"] = shared.block_shared_with;
            return (object)result;
        }).ToArray();
    }

    internal static object Intent(NIntent intent)
    {
        // Identify the rendered texture, never the monster's mutable next-move model.
        var sprite = intent.GetNodeOrNull<Sprite2D>("%Intent");
        string? path = VisibleUi.Displayed(sprite) ? sprite?.Texture?.ResourcePath : null;
        string? category = path == null ? null : Regex.Match(path,
            @"intent_(attack_[1-5]|carddebuff|death_blow|megadebuff|buff|defend|escape|heal|hidden|sleep|statuscard|stunned|summon|unknown)").Groups[1].Value;
        category = category switch
        {
            "megadebuff" => "debuff", "carddebuff" => "card_debuff", "statuscard" => "status",
            "stunned" => "stun", "" => "unrecognized", _ => category
        };
        if (category?.StartsWith("attack_") == true)
            category = "attack";
        return new { category, value = VisibleUi.DisplayedText(intent, "%Value") };
    }

    internal Dictionary<string, object?> Card(NCard card)
    {
        bool identified = card.Visibility == ModelVisibility.Visible;
        string? name = english.CardName(card);
        if (identified && name != null && card.Model is { } model && CardVisible(card)) RememberCardName(model, name);
        var highlight = card.CardHighlight;
        bool glow = VisibleUi.OnScreen(highlight) && highlight.Material is ShaderMaterial shader
            && shader.GetShaderParameter("width").AsSingle() > 0;
        bool energyShown = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%EnergyIcon"));
        bool starShown = VisibleUi.OnScreen(card.GetNodeOrNull<Control>("%StarIcon"));
        List<string> markers = [];
        if (VisibleUi.OnScreen(card.GetNodeOrNull<CanvasItem>("%UnplayableEnergyIcon")))
            markers.Add("energy");
        if (VisibleUi.OnScreen(card.GetNodeOrNull<CanvasItem>("%UnplayableStarIcon")))
            markers.Add("star");
        var result = new Dictionary<string, object?>
        {
            ["id"] = cardIds.Get(card.Model!), ["name"] = name,
            ["type"] = identified ? english.Name(card.Model!.Type.ToLocString()) : null,
            ["rarity"] = identified ? card.Model!.Rarity.ToString().ToLowerInvariant() : null,
            ["visual_card_pool"] = identified ? card.Model!.VisualCardPool.Title : null,
            ["energy_cost"] = energyShown ? VisibleUi.Text(card, "%EnergyLabel") : null,
            ["star_cost"] = starShown ? VisibleUi.Text(card, "%StarLabel") : null,
            ["unplayable_markers"] = markers,
            ["outline"] = !glow ? "none" : highlight.Modulate.IsEqualApprox(NCardHighlight.playableColor) ? "cyan"
                : highlight.Modulate.IsEqualApprox(NCardHighlight.gold) ? "gold"
                : highlight.Modulate.IsEqualApprox(NCardHighlight.red) ? "red" : "other"
        };
        string? energyColor = energyShown ? VisibleUi.SpecialCostColor(card, "%EnergyLabel") : null;
        string? starColor = starShown ? VisibleUi.SpecialCostColor(card, "%StarLabel") : null;
        if (energyColor != null)
            result["energy_cost_color"] = energyColor;
        if (starColor != null)
            result["star_cost_color"] = starColor;
        CardAppearance.Read(card, result);
        return result;
    }

    internal static (int? current, int? maximum, string display) Health(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        string? text = VisibleUi.Text(bar, "%HpLabel");
        var pair = Pair(text);
        string display = pair.current.HasValue ? "numeric"
            : text == EnglishCardText.LocalizedText(new LocString("gameplay_ui", "HEALTH_BAR.DEAD")) ? "dead"
            : VisibleUi.OnScreen(bar?.GetNodeOrNull<TextureRect>("%InfinityTex")) ? "infinite"
            : text != null ? "unknown" : "hidden";
        return (pair.current, pair.maximum, display);
    }

    internal static bool HealthNumbersVisible(Creature creature)
    {
        var node = NCombatRoom.Instance?.GetCreatureNode(creature);
        return VisibleUi.Shown(node) && Health(node!).display is "numeric" or "dead";
    }

    internal static int? Block(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        if (!VisibleUi.Shown(bar) || !VisibleUi.OnScreen(bar!.HpBarContainer))
            return null;
        return VisibleUi.Shown(bar?.GetNodeOrNull<Control>("%BlockContainer"))
            ? VisibleUi.Number(bar, "%BlockLabel") : 0;
    }

    internal static bool BlockNumbersVisible(Creature creature)
    {
        var node = NCombatRoom.Instance?.GetCreatureNode(creature);
        return Status() == "visible" && VisibleUi.Shown(node) && VisibleUi.OnScreen(node!.Body)
            && Block(node).HasValue;
    }

    internal static (int? current, int? maximum) Pair(string? text)
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
        if (!RunUi.TopBarReadable())
            return null;
        var global = NRun.Instance!.GlobalUi;
        var bar = global.TopBar;
        var run = RunManager.Instance.DebugOnlyGetState();
        var hp = Pair(VisibleUi.Descendants<NTopBarHp>(bar).Select(node => VisibleUi.Text(node, "%HpLabel")).FirstOrDefault(text => text != null));
        return new
        {
            hp = hp.current, max_hp = hp.maximum,
            gold = VisibleUi.Number(bar.Gold, "%GoldLabel"),
            floor = VisibleUi.Number(bar.FloorIcon, "FloorNumLabel"),
            ascension = VisibleUi.Number(bar, "%AscensionLabel"),
            deck_count = VisibleUi.Number(bar.Deck, "DeckCardCount"),
            room_icon = Icon(bar.RoomIcon.GetNodeOrNull<TextureRect>("Icon")),
            bosses = VisibleUi.Descendants<TextureRect>(bar.BossIcon)
                .Where(icon => icon.Name != "Outline" && VisibleUi.OnScreen(icon) && icon.Texture != null)
                .Select(icon => BossName(icon.Texture!.ResourcePath, run)).ToArray(),
            potion_slots = PotionSlots(bar.PotionContainer),
            relic_count = RelicInspection.HeldCount(),
            relics = RelicInspection.DisplayedHolders()?.Select(RelicInspection.Static).ToArray(),
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

    private object? PotionSlots(NPotionContainer container)
    {
        var holders = PotionInspection.DisplayedHolders(container);
        if (holders == null) return null;
        return holders.Select(PotionInspection.Static).ToArray();
    }

    private static string? Icon(TextureRect? icon) => VisibleUi.OnScreen(icon)
        ? Path.GetFileNameWithoutExtension(icon?.Texture?.ResourcePath) : null;

}
