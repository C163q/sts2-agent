using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CombatMotion
{
    private static readonly ConditionalWeakTable<NCreature, List<Tween>> UiTweens = new();

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.combat_motion");
        foreach (string method in new[] { nameof(NCreature.AnimDisableUi), nameof(NCreature.AnimEnableUi) })
            harmony.Patch(AccessTools.Method(typeof(NCreature), method),
                postfix: new HarmonyMethod(typeof(CombatMotion), nameof(UiChanged)));
    }

    // Native UI fades have a delay and no retained field; sampling quiet JSON misses them.
    private static void UiChanged(NCreature __instance, Tween __result)
        => UiTweens.GetValue(__instance, _ => []).Add(__result);

    public static bool Pending() => NCombatRoom.Instance is { } room
        && (room.CreatureNodes.Concat(room.RemovingCreatureNodes).Distinct().Any(Pending)
            // Outline JSON stays unchanged until the native half-second fade reaches zero.
            || room.Ui.Hand.ActiveHolders.Any(holder => VisibleUi.Shown(holder)
                && holder.CardNode is { } card && CombatObservation.CardVisible(card)
                && RewardInspection.Animating(card.CardHighlight, "_curTween")));

    private static bool Pending(NCreature node)
    {
        if (!GodotObject.IsInstanceValid(node) || node.IsQueuedForDeletion()) return false;
        bool fading = false;
        if (UiTweens.TryGetValue(node, out var tweens))
        {
            tweens.RemoveAll(t => !GodotObject.IsInstanceValid(t) || !t.IsValid() || !t.IsRunning());
            fading = tweens.Count > 0;
        }
        // A completed death task may remain non-null on creatures that later revive.
        return node.DeathAnimationTask is { IsCompleted: false } || fading
            || RewardInspection.Animating(node, "_intentFadeTween")
            || RewardInspection.Animating(node, "_scaleTween")
            || VisibleUi.Descendants<NCreatureStateDisplay>(node).Any(display => RewardInspection.Animating(display, "_showHideTween"))
            || VisibleUi.Descendants<NHealthBar>(node).Any(bar => RewardInspection.Animating(bar, "_hpLabelFadeTween")
                || RewardInspection.Animating(bar, "_blockTween"))
            || VisibleUi.Descendants<NPower>(node).Any(power => RewardInspection.Animating(power, "_animInTween"));
    }
}
