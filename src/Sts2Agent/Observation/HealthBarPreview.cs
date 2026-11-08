using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes.Combat;

namespace Sts2Agent;

internal static class HealthBarPreview
{
    internal sealed record Preview(int? poison_damage, int? doom_threshold, string? lethal);
    private sealed record Values(int? PoisonDamage, int DoomAmount);
    private sealed class Frame(NHealthBar bar)
    {
        public NHealthBar Bar { get; } = bar;
        public int? PoisonDamage;
    }
    private static readonly ConditionalWeakTable<NHealthBar, Values> Rendered = new();
    [ThreadStatic] private static Frame? current;

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.health_bar_preview");
        harmony.Patch(AccessTools.Method(typeof(NHealthBar), "RefreshForeground"),
            prefix: new HarmonyMethod(typeof(HealthBarPreview), nameof(Begin)),
            postfix: new HarmonyMethod(typeof(HealthBarPreview), nameof(End)),
            finalizer: new HarmonyMethod(typeof(HealthBarPreview), nameof(Restore)));
        harmony.Patch(AccessTools.Method(typeof(PoisonPower), nameof(PoisonPower.CalculateTotalDamageNextTurn)),
            postfix: new HarmonyMethod(typeof(HealthBarPreview), nameof(PoisonDamage)));
    }

    private static void Begin(NHealthBar __instance, out Frame? __state)
    {
        __state = current;
        current = new Frame(__instance);
    }

    private static void PoisonDamage(int __result)
    {
        if (current != null) current.PoisonDamage = __result;
    }

    private static void End(NHealthBar __instance)
    {
        if (current == null || !ReferenceEquals(current.Bar, __instance))
            throw new InvalidOperationException("Native health bar render context changed.");
        var creature = (Creature)PrivateFields.Read(__instance, "_creature")!;
        Rendered.Remove(__instance);
        Rendered.Add(__instance, new Values(current.PoisonDamage, creature.GetPowerAmount<DoomPower>()));
    }

    private static void Restore(Frame? __state) => current = __state;

    public static Preview? Read(NCreature node)
    {
        var bar = node.GetNodeOrNull<NCreatureStateDisplay>("%HealthBar")?.GetNodeOrNull<NHealthBar>("%HealthBar");
        if (CombatObservation.Health(node) is not { display: "numeric", current: { } hp }
            || !VisibleUi.OnScreen(bar?.HpBarContainer)) return null;
        bool poison = VisibleUi.Displayed(bar!.GetNodeOrNull<Control>("%PoisonForeground"));
        bool doom = VisibleUi.Displayed(bar.GetNodeOrNull<Control>("%DoomForeground"));
        if (!poison && !doom) return null;
        if (!Rendered.TryGetValue(bar, out var values) || poison && !values.PoisonDamage.HasValue)
            throw new InvalidOperationException("Displayed health preview has no native render sample.");
        var label = bar.GetNode<Control>("%HpLabel");
        var color = label.GetThemeColor("font_color");
        string? lethal = poison && color.IsEqualApprox(new Color("76FF40")) ? "poison"
            : doom && color.IsEqualApprox(new Color("FB8DFF")) ? "doom" : null;
        // The green segment covers only HP that can actually be lost.
        return new Preview(poison ? Math.Min(hp, values.PoisonDamage!.Value) : null,
            doom ? values.DoomAmount : null, lethal);
    }
}
