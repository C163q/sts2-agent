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

internal sealed class CombatantInspection(CombatantInspection.Level level)
{
    internal enum Level { Summary, Full }
    private const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;
    private static readonly FieldInfo IntentModel = typeof(NIntent).GetField("_intent", PrivateInstance)!;
    private static readonly FieldInfo IntentTargets = typeof(NIntent).GetField("_targets", PrivateInstance)!;
    private static readonly FieldInfo IntentOwner = typeof(NIntent).GetField("_owner", PrivateInstance)!;
    private readonly Dictionary<(string? title, string description), List<string>> tips = [];
    private readonly List<string> unavailable = [];

    internal sealed record PowerText(string? name, int? amount);
    internal sealed record PlayerText(PowerText[]? powers, OrbInspection.OrbText?[]? orb_slots,
        SovereignBladeInspection.BladeText[] sovereign_blades);
    internal sealed record AllyText(uint? id, string? name, PowerText[]? powers);
    internal sealed record EnemyText(uint? id, string? name, PowerText[]? powers, object[]? intents);
    internal sealed record SharedTip(string? title, string description, string[] sources);
    internal sealed record Result(PlayerText? player, EnemyText[] enemies, AllyText[] allies,
        SharedTip[] hover_tips, string[] unavailable_hover_sources);

    public static Result Read(Player? player, Func<CardModel, int> cardId, Level level = Level.Full) =>
        EnglishCardText.Read(() => new CombatantInspection(level).ReadAll(player, cardId));

    internal static string? UnavailableReason(Level level)
    {
        if (CombatObservation.Status() != "visible")
            return "The battlefield is covered, hidden, or not ready. Expose the battlefield before inspecting combatants.";
        if (level == Level.Full && NCombatRoom.Instance!.Ui.Hand.InCardPlay)
            return "Hover help is unavailable while dragging, aiming, or playing a card. Use preset summary for static combatant data.";
        return null;
    }

    private Result ReadAll(Player? player, Func<CardModel, int> cardId)
    {
        if (UnavailableReason(level) is { } reason) throw new InvalidOperationException(reason);
        var playerNode = player == null ? null : NCombatRoom.Instance!.GetCreatureNode(player.Creature);
        var playerText = VisibleUi.Shown(playerNode) && VisibleUi.OnScreen(playerNode!.Body)
            ? new PlayerText(Powers(playerNode, "player"), Orbs(playerNode), Blades(playerNode, cardId)) : null;
        var enemies = CombatObservation.EnemyNodes().Select((node, index) => new EnemyText(
            node.Entity.CombatId, EnglishCardText.Plain(node.Entity.Monster!.Title.GetFormattedText()),
            Powers(node, $"enemies.{index}"), Intents(node, $"enemies.{index}"))).ToArray();
        var allies = CombatObservation.AllyNodes().Select((node, index) => new AllyText(
            node.Entity.CombatId, EnglishCardText.Plain(node.Entity.Monster!.Title.GetFormattedText()),
            Powers(node, $"allies.{index}"))).ToArray();
        return new Result(playerText, enemies, allies,
            tips.Select(pair => new SharedTip(pair.Key.title, pair.Key.description, pair.Value.ToArray())).ToArray(),
            unavailable.ToArray());
    }

    internal static NPowerContainer? PowerContainer(NCreature node) =>
        node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NPowerContainer>("%PowerContainer");

    private SovereignBladeInspection.BladeText[] Blades(NCreature node, Func<CardModel, int> cardId)
    {
        var blades = SovereignBladeInspection.VisibleNodes(node, cardId);
        if (level == Level.Full)
            for (int i = 0; i < blades.Length; i++)
            {
                string source = $"player.sovereign_blades.{i}";
                if (!SovereignBladeInspection.Hoverable(blades[i])) { unavailable.Add(source); continue; }
                // Native hover rendering refreshes previews; never reuse stale off-hand values.
                AddText(new HoverTipText(EnglishCardText.Plain(blades[i].Card.Title),
                    (string)BrowsedCard.Read(blades[i].Card, "preview", PileType.Deck, upgrades: false,
                        full: true, preservePile: true)["description"]!), source);
            }
        return SovereignBladeInspection.ReadNodes(blades, cardId);
    }

    private OrbInspection.OrbText?[]? Orbs(NCreature node)
    {
        var slots = OrbInspection.VisibleNodes(node);
        if (slots == null) return null;
        if (level == Level.Full)
            for (int i = 0; i < slots.Length; i++)
                if (slots[i].Model is { } model)
                {
                    string source = $"player.orb_slots.{i}";
                    if (OrbInspection.Hoverable(slots[i])) Add(model.HoverTips, source);
                    else unavailable.Add(source);
                }
        return OrbInspection.ReadSlots(slots);
    }

    private PowerText[]? Powers(NCreature node, string source)
    {
        var container = PowerContainer(node);
        if (!VisibleUi.Shown(container)) return null;
        List<PowerText> powers = [];
        foreach (var power in container!.GetChildren().OfType<NPower>())
        {
            if (!VisibleUi.Displayed(power) || !power.Model.IsVisible
                || !VisibleUi.Displayed(power.GetNodeOrNull<TextureRect>("%Icon"))) continue;
            string path = $"{source}.powers.{powers.Count}";
            powers.Add(new PowerText(EnglishCardText.Plain(power.Model.Title.GetFormattedText()),
                VisibleUi.DisplayedNumber(power, "%AmountLabel")));
            if (level != Level.Full) continue;
            if (power.MouseFilter == Control.MouseFilterEnum.Ignore) { unavailable.Add(path); continue; }
            Add(EnglishCardText.ReadPower(power.Model, () => power.Model.HoverTips.ToArray()), path);
        }
        return powers.ToArray();
    }

    private object[]? Intents(NCreature node, string source)
    {
        if (!VisibleUi.Shown(node.IntentContainer)) return null;
        List<object> intents = [];
        foreach (var intent in node.IntentContainer.GetChildren().OfType<NIntent>())
        {
            var sprite = intent.GetNodeOrNull<Sprite2D>("%Intent");
            if (!VisibleUi.Displayed(intent.GetNodeOrNull<Control>("%IntentHolder"))
                || !VisibleUi.Displayed(sprite) || sprite!.Texture == null
                || Mathf.Abs(sprite.GetGlobalTransformWithCanvas().Determinant()) <= 0.000001f) continue;
            string path = $"{source}.intents.{intents.Count}";
            intents.Add(CombatObservation.Intent(intent));
            if (level != Level.Full) continue;
            var model = IntentModel.GetValue(intent) as AbstractIntent
                ?? throw new InvalidOperationException("Displayed intent is unavailable.");
            if (!ReferenceEquals(IntentOwner.GetValue(intent), node.Entity))
                throw new InvalidOperationException("Displayed intent owner changed.");
            if (!model.HasIntentTip) continue;
            if (intent.MouseFilter == Control.MouseFilterEnum.Ignore) { unavailable.Add(path); continue; }
            var targets = IntentTargets.GetValue(intent) as IEnumerable<Creature>
                ?? throw new InvalidOperationException("Displayed intent targets are unavailable.");
            Add([model.GetHoverTip(targets, node.Entity)], path);
        }
        return intents.ToArray();
    }

    private void Add(IEnumerable<IHoverTip> entries, string source)
    {
        foreach (var tip in entries.Select(HoverTipText.From)) AddText(tip, source);
    }

    private void AddText(HoverTipText tip, string source)
    {
        var key = (tip.title, tip.description);
        if (!tips.TryGetValue(key, out var sources)) tips[key] = sources = [];
        if (!sources.Contains(source)) sources.Add(source);
    }
}
