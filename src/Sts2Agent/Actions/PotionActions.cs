using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Potions;
using MegaCrit.Sts2.Core.Hooks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Nodes.Potions;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class PotionActions
{
    private static readonly EnglishText English = new();
    public static string? Type(PotionModel potion) => potion.TargetType is TargetType.Self or TargetType.AnyPlayer
        or TargetType.AnyEnemy or TargetType.AllEnemies or TargetType.TargetedNoCreature
        ? TargetInspection.Type(potion.TargetType) : null;

    public static NPotionHolder? Find(int slot)
    {
        var holders = PotionInspection.VisibleHolders();
        return holders != null && slot < holders.Length && holders[slot].HasPotion ? holders[slot] : null;
    }

    public static bool RequiresTarget(PotionModel potion) => potion.TargetType is TargetType.AnyEnemy or TargetType.TargetedNoCreature
        || potion.CanThrowAtAlly();

    public static bool Discardable(PotionModel potion) => potion.Owner.CanRemovePotions
        && potion.Owner.Creature.IsAlive && !potion.IsQueued && !potion.HasBeenRemovedFromState;

    public static Creature[] Targets(PotionModel potion)
    {
        var combat = potion.Owner.Creature.CombatState;
        if (!CombatManager.Instance.IsInProgress || combat == null) return [];
        IEnumerable<Creature> candidates = potion.TargetType switch
        {
            TargetType.Self => [potion.Owner.Creature],
            TargetType.AnyPlayer => potion.CanThrowAtAlly() ? combat.PlayerCreatures.Where(c => c.IsPlayer) : [potion.Owner.Creature],
            TargetType.AnyEnemy or TargetType.AllEnemies or TargetType.RandomEnemy => combat.HittableEnemies,
            TargetType.AnyAlly => combat.PlayerCreatures.Where(c => c != potion.Owner.Creature && c.IsPlayer),
            TargetType.AllAllies => combat.PlayerCreatures.Where(c => c.IsAlive),
            TargetType.Osty => potion.Owner.Osty is { } osty ? [osty] : [],
            _ => []
        };
        return candidates.Where(creature =>
        {
            var node = NCombatRoom.Instance?.GetCreatureNode(creature);
            return creature.CombatId.HasValue && VisibleUi.Shown(node) && VisibleUi.OnScreen(node!.Body)
                && (!RequiresTarget(potion) || creature.IsHittable && potion.IsValidTarget(creature)
                    && Hook.ShouldAllowTargeting(combat, creature, out _));
        }).ToArray();
    }

    public static bool MerchantVisible(PotionModel potion) => potion is FoulPotion
        && potion.TargetType == TargetType.TargetedNoCreature
        && MegaCrit.Sts2.Core.Nodes.NRun.Instance?.GlobalUi.MapScreen.IsOpen == false
        && potion.Owner.RunState.CurrentRoom is { } room
        && FoulPotion.GetFoulPotionMerchantTarget(room).button is { } button
        // The native merchant hitbox has SelfModulate.A == 0; its child visual is rendered normally.
        && button.IsInsideTree() && button.IsVisibleInTree()
        && VisibleUi.Descendants<Godot.CanvasItem>(button).Any(VisibleUi.OnScreen);

    public static string? Reason(PotionModel potion)
    {
        if (!Discardable(potion)) return "Potions cannot be removed now.";
        if (potion.Usage == PotionUsage.Automatic) return "This potion is used automatically.";
        if (potion.Usage is not (PotionUsage.AnyTime or PotionUsage.CombatOnly)
            || Type(potion) == null) return "This potion is unsupported.";
        if (potion.Usage == PotionUsage.CombatOnly && !CombatManager.Instance.IsInProgress)
            return "This potion can only be used in combat.";
        if (!potion.PassesCustomUsabilityCheck) return "This potion cannot be used here.";
        if (RequiresTarget(potion) && (potion.TargetType == TargetType.TargetedNoCreature
            ? !MerchantVisible(potion) : Targets(potion).Length == 0)) return "No valid target.";
        return null;
    }

    public static object Reference(PotionModel potion, int slot) => new { slot_index = slot, name = English.Name(potion.Title) };

    public static object Read(PotionModel potion, int slot, string snapshotId)
    {
        List<object> targets = Targets(potion).Select(creature => (object)new { id = (object)creature.CombatId!.Value,
            kind = creature.IsPlayer ? "player" : creature.IsEnemy ? "enemy" : "ally",
            name = creature.IsPlayer ? English.Name(creature.Player!.Character.Title) : English.Name(creature.Monster!.Title) }).ToList();
        if (!CombatManager.Instance.IsInProgress && potion.TargetType is TargetType.Self or TargetType.AnyPlayer
            && potion.Owner.Creature.IsAlive)
            targets.Add(new { id = "self", kind = "player", name = English.Name(potion.Owner.Character.Title) });
        if (MerchantVisible(potion)) targets.Add(new { id = "merchant", kind = "merchant", name = "Merchant" });
        string? reason = Reason(potion);
        return new { snapshot_id = snapshotId, potion = Reference(potion, slot), usable = reason == null,
            discardable = Discardable(potion), target_type = Type(potion),
            requires_target = RequiresTarget(potion), targets, reason };
    }
}
