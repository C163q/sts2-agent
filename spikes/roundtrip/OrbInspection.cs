using Godot;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Orbs;

namespace Sts2Agent;

internal static class OrbInspection
{
    private static readonly EnglishText English = new();
    internal sealed record OrbText(string? name, int? passive, int? evoke);

    public static NOrb[]? VisibleNodes(NCreature node)
    {
        var manager = node.OrbManager;
        if (CombatObservation.Status() != "visible" || !VisibleUi.Shown(manager)) return null;
        // The UI list excludes the old orb that may still be fading after an evoke.
        if (CardSelection.Field(manager!, "_orbs") is not IEnumerable<NOrb> displayed) return null;
        var slots = displayed.ToArray();
        if (slots.Any(slot => !VisibleUi.Shown(slot) || (slot.Model == null
                ? !VisibleUi.OnScreen(slot.GetNodeOrNull<Control>("%Outline"))
                : !VisibleUi.OnScreen(slot.GetNodeOrNull<Control>("Bounds"))
                    || !SpriteVisible(slot)))) return null;
        return slots;
    }

    private static bool SpriteVisible(NOrb slot)
    {
        if (CardSelection.Field(slot, "_sprite") is not Node2D sprite || !VisibleUi.OnScreen(sprite)) return false;
        var transform = sprite.GetGlobalTransformWithCanvas();
        if (Mathf.Abs(transform.Determinant()) <= 0.000001f) return false;
        // The fixed hitbox can remain visible while the animated sprite moves or is clipped.
        for (Node? ancestor = sprite.GetParent(); ancestor != null; ancestor = ancestor.GetParent())
            if (ancestor is Control { ClipContents: true } clip
                && !new Rect2(Vector2.Zero, clip.Size).HasPoint(
                    clip.GetGlobalTransformWithCanvas().AffineInverse() * transform.Origin)) return false;
        return true;
    }

    public static OrbText?[]? Read(NCreature node) => VisibleNodes(node)?.Select(slot => slot.Model == null ? null
        : new OrbText(English.Name(slot.Model.Title), VisibleUi.Number(slot, "%PassiveAmount"),
            VisibleUi.Number(slot, "%EvokeAmount"))).ToArray();

    public static bool Hoverable(NOrb node) => node.IsEnabled && node.MouseFilter != Control.MouseFilterEnum.Ignore;
}
