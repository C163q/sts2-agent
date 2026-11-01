using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.MonsterMoves.Intents;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal sealed class CombatantInspection
{
    private const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;
    private static readonly FieldInfo IntentModel = typeof(NIntent).GetField("_intent", PrivateInstance)!;
    private static readonly FieldInfo IntentTargets = typeof(NIntent).GetField("_targets", PrivateInstance)!;
    private static readonly FieldInfo IntentOwner = typeof(NIntent).GetField("_owner", PrivateInstance)!;
    private readonly Dictionary<(string? title, string description), List<string>> tips = [];

    internal sealed record PowerText(string? name, int? amount);
    internal sealed record PlayerText(PowerText[]? powers, OrbInspection.OrbText?[]? orb_slots,
        SovereignBladeInspection.BladeText[] sovereign_blades);
    internal sealed record AllyText(uint? id, string? name, PowerText[]? powers);
    internal sealed record EnemyText(uint? id, string? name, PowerText[]? powers, object[]? intents);
    internal sealed record SharedTip(string? title, string description, string[] sources);
    internal sealed record Result(string scene, PlayerText? player, EnemyText[] enemies, AllyText[] allies, SharedTip[] hover_tips);

    public static Result Read(Player player, Func<CardModel, int> cardId) =>
        EnglishCardText.Read(() => new CombatantInspection().ReadAll(player, cardId));

    private Result ReadAll(Player player, Func<CardModel, int> cardId)
    {
        if (CombatObservation.Status() != "visible" || NCombatRoom.Instance!.Ui.Hand.InCardPlay)
            throw new InvalidOperationException("Combatant details require a visible combat screen.");
        var playerNode = NCombatRoom.Instance!.GetCreatureNode(player.Creature);
        var playerText = VisibleUi.Shown(playerNode) && VisibleUi.OnScreen(playerNode!.Body)
            ? new PlayerText(Powers(playerNode, "player"), Orbs(playerNode), Blades(playerNode, cardId)) : null;
        var enemies = CombatObservation.EnemyNodes().Select((node, index) => new EnemyText(
            node.Entity.CombatId, EnglishCardText.Plain(node.Entity.Monster!.Title.GetFormattedText()),
            Powers(node, $"enemies.{index}"), Intents(node, $"enemies.{index}"))).ToArray();
        var allies = CombatObservation.AllyNodes().Select((node, index) => new AllyText(
            node.Entity.CombatId, EnglishCardText.Plain(node.Entity.Monster!.Title.GetFormattedText()),
            Powers(node, $"allies.{index}"))).ToArray();
        return new Result("combat", playerText, enemies, allies,
            tips.Select(pair => new SharedTip(pair.Key.title, pair.Key.description, pair.Value.ToArray())).ToArray());
    }

    internal static NPowerContainer? PowerContainer(NCreature node) =>
        node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NPowerContainer>("%PowerContainer");

    private SovereignBladeInspection.BladeText[] Blades(NCreature node, Func<CardModel, int> cardId)
    {
        var blades = SovereignBladeInspection.VisibleNodes(node, cardId);
        for (int i = 0; i < blades.Length; i++)
            if (SovereignBladeInspection.Hoverable(blades[i]))
                // Hover-card rendering recalculates previews; an off-hand card can retain stale cached values.
                AddText(new HoverTipText(EnglishCardText.Plain(blades[i].Card.Title),
                    (string)BrowsedCard.Read(blades[i].Card, "preview", PileType.Deck, upgrades: false,
                        full: true, preservePile: true)["description"]!), $"player.sovereign_blades.{i}");
        return SovereignBladeInspection.Read(node, cardId);
    }

    private OrbInspection.OrbText?[]? Orbs(NCreature node)
    {
        var slots = OrbInspection.VisibleNodes(node);
        if (slots == null) return null;
        for (int i = 0; i < slots.Length; i++)
            if (slots[i].Model is { } model && OrbInspection.Hoverable(slots[i]))
                Add(model.HoverTips, $"player.orb_slots.{i}");
        return OrbInspection.Read(node);
    }

    private PowerText[]? Powers(NCreature node, string source)
    {
        var container = PowerContainer(node);
        if (!VisibleUi.Shown(container))
            return null;
        List<PowerText> powers = [];
        foreach (var power in container!.GetChildren().OfType<NPower>())
        {
            if (!VisibleUi.OnScreen(power) || !power.Model.IsVisible
                || !VisibleUi.OnScreen(power.GetNodeOrNull<TextureRect>("%Icon"))
                || power.MouseFilter == Control.MouseFilterEnum.Ignore)
                continue;
            var hoverTips = EnglishCardText.ReadPower(power.Model, () => power.Model.HoverTips.ToArray());
            Add(hoverTips, $"{source}.powers.{powers.Count}");
            powers.Add(new PowerText(EnglishCardText.Plain(power.Model.Title.GetFormattedText()),
                VisibleUi.Number(power, "%AmountLabel")));
        }
        return powers.ToArray();
    }

    private object[]? Intents(NCreature node, string source)
    {
        if (!VisibleUi.Shown(node.IntentContainer))
            return null;
        List<object> intents = [];
        foreach (var intent in node.IntentContainer.GetChildren().OfType<NIntent>())
        {
            var sprite = intent.GetNodeOrNull<Sprite2D>("%Intent");
            if (!VisibleUi.OnScreen(intent.GetNodeOrNull<Control>("%IntentHolder"))
                || !VisibleUi.Shown(sprite) || sprite!.Texture == null
                || intent.MouseFilter == Control.MouseFilterEnum.Ignore)
                continue;
            var model = IntentModel.GetValue(intent) as AbstractIntent
                ?? throw new InvalidOperationException("Displayed intent is unavailable.");
            if (!ReferenceEquals(IntentOwner.GetValue(intent), node.Entity))
                throw new InvalidOperationException("Displayed intent owner changed.");
            if (model.HasIntentTip)
            {
                var targets = IntentTargets.GetValue(intent) as IEnumerable<Creature>
                    ?? throw new InvalidOperationException("Displayed intent targets are unavailable.");
                Add([model.GetHoverTip(targets, node.Entity)], $"{source}.intents.{intents.Count}");
            }
            intents.Add(CombatObservation.Intent(intent));
        }
        return intents.ToArray();
    }

    private void Add(IEnumerable<IHoverTip> entries, string source)
    {
        foreach (var tip in entries.Select(HoverTipText.From))
            AddText(tip, source);
    }

    private void AddText(HoverTipText tip, string source)
    {
        var key = (tip.title, tip.description);
        if (!tips.TryGetValue(key, out var sources)) tips[key] = sources = [];
        if (!sources.Contains(source)) sources.Add(source);
    }
}
