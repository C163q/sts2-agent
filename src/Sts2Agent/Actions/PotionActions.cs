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
        var holder = PotionInspection.DisplayedAt(slot);
        return holder?.HasPotion == true ? holder : null;
    }

    public static bool RequiresTarget(PotionModel potion) => potion.TargetType is TargetType.AnyEnemy or TargetType.TargetedNoCreature
        || potion.CanThrowAtAlly();

    public static string? RemovalReason(PotionModel potion)
    {
        if (!potion.Owner.Creature.IsAlive) return "The potion's owner is no longer alive.";
        if (potion.HasBeenRemovedFromState) return "This potion is no longer in the belt.";
        if (potion.IsQueued) return "This potion is already queued; wait for its current action to finish.";
        if (!potion.Owner.CanRemovePotions) return "Potions cannot be removed now.";
        int slot = potion.Owner.GetPotionSlotIndex(potion);
        var holder = Find(slot);
        if (holder == null || !ReferenceEquals(holder.Potion!.Model, potion))
            return "This potion slot is hidden or not ready.";
        return PotionInspection.Interactive(holder) ? null
            : "This potion slot cannot be interacted with; use another slot or wait for it to become available.";
    }

    public static bool Discardable(PotionModel potion) => RemovalReason(potion) == null;

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
        if (RemovalReason(potion) is { } removal) return removal;
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

    public static string? TargetReason(PotionModel potion, bool supplied, bool merchant, uint creatureId, out Creature? target)
    {
        target = null;
        if (RequiresTarget(potion) && !supplied)
            return "This potion requires target_id; inspect_targets can show current targets.";
        if (!RequiresTarget(potion) && supplied)
            return "This potion does not require target_id; omit it.";
        if (!supplied) return null;
        if (potion.TargetType == TargetType.TargetedNoCreature)
            return merchant && MerchantVisible(potion) ? null : "This potion requires the currently exposed merchant as its target.";
        if (merchant) return "This potion requires a creature target, not merchant.";
        target = Targets(potion).FirstOrDefault(creature => creature.CombatId == creatureId);
        return target != null && potion.IsValidTarget(target) ? null
            : "The specified target is not currently available for this potion.";
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
