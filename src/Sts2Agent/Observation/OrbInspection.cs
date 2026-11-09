using Godot;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Orbs;

namespace Sts2Agent;

internal static class OrbInspection
{
    private static readonly EnglishText English = new();
    internal sealed record OrbText(int slot_index, string? name, int? passive, int? evoke);

    public static NOrb[]? VisibleNodes(NCreature node)
    {
        var slots = DisplayedNodes(node);
        return slots != null && slots.All(slot => SlotVisible(slot)) ? slots : null;
    }

    internal static NOrb[]? DisplayedNodes(NCreature node)
    {
        var manager = node.OrbManager;
        if (CombatObservation.Status() != "visible" || !VisibleUi.Shown(manager)) return null;
        // The UI list excludes the old orb that may still be fading after an evoke.
        if (PrivateFields.Read(manager!, "_orbs") is not IEnumerable<NOrb> displayed) return null;
        return displayed.ToArray();
    }

    internal static bool SlotVisible(NOrb slot, bool entering = false) => VisibleUi.Shown(slot) && (slot.Model == null
        ? VisibleUi.Displayed(slot.GetNodeOrNull<Control>("%Outline"))
        : VisibleUi.Displayed(slot.GetNodeOrNull<Control>("Bounds")) && SpriteVisible(slot, entering));

    private static bool SpriteVisible(NOrb slot, bool entering)
    {
        if (PrivateFields.Read(slot, "_sprite") is not Node2D sprite || !VisibleUi.Displayed(sprite)) return false;
        var transform = sprite.GetGlobalTransformWithCanvas();
        if (Mathf.Abs(transform.Determinant()) <= 0.000001f
            && !(entering && RewardInspection.Animating(slot, "_curTween"))) return false;
        // The fixed hitbox can remain visible while the animated sprite moves or is clipped.
        for (Node? ancestor = sprite.GetParent(); ancestor != null; ancestor = ancestor.GetParent())
            if (ancestor is Control { ClipContents: true } clip
                && !new Rect2(Vector2.Zero, clip.Size).HasPoint(
                    clip.GetGlobalTransformWithCanvas().AffineInverse() * transform.Origin)) return false;
        return true;
    }

    public static OrbText?[]? Read(NCreature node) => ReadSlots(VisibleNodes(node));

    // Native slots start at the right; public arrays follow the screen from left to right.
    internal static int ArrayIndex(int slotIndex, int capacity) => capacity - 1 - slotIndex;

    internal static OrbText?[]? ReadSlots(NOrb[]? slots) => slots?.Select((slot, index) => slot.Model == null ? null
        : new OrbText(index, English.Name(slot.Model.Title), VisibleUi.DisplayedNumber(slot, "%PassiveAmount"),
            VisibleUi.DisplayedNumber(slot, "%EvokeAmount"))).Reverse().ToArray();

    public static bool Hoverable(NOrb node) => node.IsEnabled && node.MouseFilter != Control.MouseFilterEnum.Ignore;
}
