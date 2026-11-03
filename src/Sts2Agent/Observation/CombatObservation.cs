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
    private CombatState? identityCombat;
    internal int CardId(CardModel card) => cardIds.Get(card);

    public void Synchronize(CombatState? combat, Player? player)
    {
        if (!ReferenceEquals(identityCombat, combat))
        {
            identityCombat = combat;
            cardIds.Clear();
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

    public object? Player(Player? player)
    {
        if (player == null || Status() != "visible")
            return null;
        var room = NCombatRoom.Instance!;
        NCreature? node = room.GetCreatureNode(player.Creature);
        if (!VisibleUi.Shown(node) || !VisibleUi.OnScreen(node!.Body))
            return null;
        var hp = Health(node!);
        var resources = CombatResources.Read();
        return new
        {
            character = player.Character.Id.Entry,
            hp = hp.current, max_hp = hp.maximum, hp_display = hp.display, block = Block(node!),
            energy = resources.Energy, max_energy = resources.Maximum, stars = resources.Stars,
            powers = Powers(node!),
            orb_slots = OrbInspection.Read(node!),
            sovereign_blades = SovereignBladeInspection.Read(node!, CardId),
            hand = VisibleUi.Shown(room.Ui.Hand) ? HandCards(room.Ui.Hand).Select(Card).ToArray() : null,
            draw_count = VisibleUi.Number(room.Ui.DrawPile, "CountContainer/Count"),
            discard_count = VisibleUi.Number(room.Ui.DiscardPile, "CountContainer/Count"),
            exhaust_count = VisibleUi.Number(room.Ui.ExhaustPile, "CountContainer/Count")
        };
    }

    internal static bool CardVisible(NCard? card) => CardVisible(card, VisibleUi.OnScreen);

    internal static IEnumerable<NCard> HandCards(NPlayerHand hand) => hand.ActiveHolders
        .Where(holder => VisibleUi.Shown(holder) && CardVisible(holder.CardNode)).Select(holder => holder.CardNode!);

    internal static bool CardVisible(NCard? card, Func<CanvasItem?, bool> readable) => VisibleUi.Shown(card)
        && new[] { "%TitleLabel", "%Portrait", "%AncientPortrait", "%Frame" }
            .Any(path => readable(card!.GetNodeOrNull<Control>(path)));

    public object[]? Enemies()
    {
        if (Status() != "visible")
            return null;
        return EnemyNodes().Select(Enemy).ToArray();
    }

    internal static IEnumerable<NCreature> VisibleCreatureNodes() =>
        NCombatRoom.Instance!.CreatureNodes.Concat(NCombatRoom.Instance.RemovingCreatureNodes).Distinct()
            .Where(node => VisibleUi.Shown(node) && VisibleUi.OnScreen(node.Body))
            .OrderBy(node => node.GlobalPosition.X);

    internal static IEnumerable<NCreature> EnemyNodes() => VisibleCreatureNodes().Where(node => node.Entity.IsEnemy);
    internal static IEnumerable<NCreature> AllyNodes() => VisibleCreatureNodes()
        .Where(node => !node.Entity.IsPlayer && !node.Entity.IsEnemy);

    public object[]? Allies()
    {
        if (Status() != "visible") return null;
        return AllyNodes().Select(node =>
        {
            var hp = Health(node);
            var result = new Dictionary<string, object?>
            {
                ["id"] = node.Entity.CombatId, ["name"] = english.Name(node.Entity.Monster!.Title),
                ["hp"] = hp.current, ["max_hp"] = hp.maximum, ["hp_display"] = hp.display,
                ["block"] = Block(node), ["powers"] = Powers(node)
            };
            var display = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar");
            if (display != null && CardSelection.Field(display, "_blockTrackingCreature") is Creature { IsPlayer: true } tracked
                && ReferenceEquals(tracked.Player, node.Entity.PetOwner) && LocalContext.IsMe(tracked))
                result["block_shared_with"] = "player";
            return (object)result;
        }).ToArray();
    }

    private object Enemy(NCreature node)
    {
        var hp = Health(node);
        return new
        {
            id = node.Entity.CombatId,
            name = english.Name(node.Entity.Monster!.Title),
            hp = hp.current, max_hp = hp.maximum, hp_display = hp.display, block = Block(node),
            powers = Powers(node),
            intents = !VisibleUi.Shown(node.IntentContainer) ? null : node.IntentContainer.GetChildren()
                .OfType<NIntent>().Where(intent => VisibleUi.OnScreen(intent.GetNodeOrNull<Control>("%IntentHolder")))
                .Select(Intent).ToArray()
        };
    }

    internal static object Intent(NIntent intent)
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

    internal Dictionary<string, object?> Card(NCard card)
    {
        bool identified = card.Visibility == ModelVisibility.Visible;
        string? name = english.CardName(card);
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

    internal static (int? current, int? maximum, string display) Health(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        string? text = VisibleUi.Text(bar, "%HpLabel");
        var pair = Pair(text);
        string display = pair.current.HasValue ? "numeric"
            : text == new LocString("gameplay_ui", "HEALTH_BAR.DEAD").GetFormattedText() ? "dead"
            : VisibleUi.OnScreen(bar?.GetNodeOrNull<TextureRect>("%InfinityTex")) ? "infinite"
            : text != null ? "unknown" : "hidden";
        return (pair.current, pair.maximum, display);
    }

    internal static bool HealthNumbersVisible(Creature creature)
    {
        var node = NCombatRoom.Instance?.GetCreatureNode(creature);
        return VisibleUi.Shown(node) && Health(node!).display is "numeric" or "dead";
    }

    private static int? Block(NCreature node)
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
            relics = RelicInspection.DisplayedHolders()?.Select(holder => new
                {
                    name = english.RelicName(holder.Relic.Model),
                    counter = VisibleUi.Number(holder, "%AmountLabel"),
                    melted = RelicInspection.Melted(holder.Relic)
                }).ToArray(),
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
        var layout = container.GetNodeOrNull<Control>("MarginContainer/PotionHolders");
        if (!VisibleUi.Shown(container) || !VisibleUi.Shown(layout))
            return null;
        var holders = layout!.GetChildren().OfType<NPotionHolder>().ToArray();
        if (holders.Any(holder => !VisibleUi.OnScreen(holder)))
            return null;
        return holders.Select(holder =>
        {
            if (!holder.HasPotion) return null;
            var value = new Dictionary<string, object?> { ["name"] = english.Name(holder.Potion!.Model.Title) };
            if (holder.Potion.Model is MegaCrit.Sts2.Core.Models.Potions.FoulPotion && ShopInspection.Current is { } shop && ShopInspection.Exposed(shop))
                value["usable_here"] = PotionActions.MerchantVisible(holder.Potion.Model) && PotionActions.Reason(holder.Potion.Model) == null;
            if (RewardInspection.Animating(holder.Potion, "_bounceTween")) value["bouncing"] = true;
            return value;
        }).ToArray();
    }

    private static string? Icon(TextureRect? icon) => VisibleUi.OnScreen(icon)
        ? Path.GetFileNameWithoutExtension(icon?.Texture?.ResourcePath) : null;

}
