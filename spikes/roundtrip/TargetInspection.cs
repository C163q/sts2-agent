using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Hooks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal sealed class TargetInspection(CombatObservation observation)
{
    private readonly EnglishText english = new();

    public CardModel? FindCard(int id) => NPlayerHand.Instance?.ActiveHolders
        .Where(holder => CardSelection.Clickable(holder) && holder.CardNode!.Visibility == ModelVisibility.Visible)
        .Select(holder => holder.CardModel).FirstOrDefault(card => card != null && observation.CardId(card) == id);

    public static string? Type(CardModel card) => card.TargetType == TargetType.TargetedNoCreature ? null : Type(card.TargetType);
    public static string? Type(TargetType type) => type switch
    {
        TargetType.None => "none", TargetType.Self => "self", TargetType.AnyEnemy => "any_enemy",
        TargetType.AllEnemies => "all_enemies", TargetType.RandomEnemy => "random_enemy",
        TargetType.AnyPlayer => "any_player", TargetType.AnyAlly => "any_ally",
        TargetType.AllAllies => "all_allies", TargetType.Osty => "osty",
        TargetType.TargetedNoCreature => "targeted_no_creature", _ => null
    };

    // Self is a single-target potion type, but never an explicit card target.
    public static bool RequiresTarget(CardModel card) => card.TargetType is TargetType.AnyEnemy or TargetType.AnyAlly;

    private static bool Visible(Creature creature)
    {
        var node = NCombatRoom.Instance?.GetCreatureNode(creature);
        return creature.CombatId.HasValue && VisibleUi.Shown(node) && VisibleUi.OnScreen(node!.Body);
    }

    public static Creature[] Targets(CardModel card)
    {
        if (card.CombatState == null) return [];
        IEnumerable<Creature> candidates = card.TargetType switch
        {
            TargetType.Self or TargetType.AnyPlayer => [card.Owner.Creature],
            TargetType.AnyEnemy or TargetType.AllEnemies or TargetType.RandomEnemy => card.CombatState.HittableEnemies,
            TargetType.AnyAlly => card.CombatState.PlayerCreatures.Where(creature => creature != card.Owner.Creature && creature.IsHittable),
            TargetType.AllAllies => card.CombatState.PlayerCreatures.Where(creature => creature.IsAlive),
            TargetType.Osty => card.Owner.Osty is { } osty ? [osty] : [],
            _ => []
        };
        return candidates.Where(Visible).Where(creature => !RequiresTarget(card)
            || card.IsValidTarget(creature) && Hook.ShouldAllowTargeting(card.CombatState, creature, out _)).ToArray();
    }

    public static string? Reason(CardModel card, Creature[] targets)
    {
        if (!card.CanPlay(out UnplayableReason reason, out _))
            return reason.HasFlag(UnplayableReason.EnergyCostTooHigh) ? "Not enough Energy."
                : reason.HasFlag(UnplayableReason.StarCostTooHigh) ? "Not enough Stars."
                : reason.HasFlag(UnplayableReason.NoLivingAllies) ? "No living allies."
                : "This card cannot be played now.";
        return RequiresTarget(card) && targets.Length == 0 ? "No valid target." : null;
    }

    public object Read(CardModel card, string snapshotId)
    {
        var targets = Targets(card);
        string? reason = Reason(card, targets);
        return new { snapshot_id = snapshotId, card = new { id = observation.CardId(card), name = english.Name(card.TitleLocString) },
            playable = reason == null, target_type = Type(card), requires_target = RequiresTarget(card),
            targets = targets.Select(creature => new { id = creature.CombatId!.Value,
                kind = creature.IsPlayer ? "player" : creature.IsEnemy ? "enemy" : "ally",
                name = creature.IsPlayer ? english.Name(creature.Player!.Character.Title) : english.Name(creature.Monster!.Title) }).ToArray(), reason };
    }
}
