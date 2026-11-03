using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal static class SovereignBladeInspection
{
    internal sealed record BladeText(int id, string? name);

    public static NSovereignBladeVfx[] VisibleNodes(NCreature owner, Func<CardModel, int> cardId) =>
        owner.GetChildren().OfType<NSovereignBladeVfx>().Where(Visible)
            // Native orbiting reorders siblings when crossing behind the owner.
            .OrderBy(node => cardId(node.Card)).ToArray();

    private static bool Visible(NSovereignBladeVfx node)
    {
        var sprite = node.GetNodeOrNull<Node2D>("SpineSword");
        if (!VisibleUi.Shown(node) || !VisibleUi.Displayed(sprite)
            || Mathf.Abs(sprite!.GetGlobalTransformWithCanvas().Determinant()) <= 0.000001f) return false;
        for (Node? ancestor = sprite.GetParent(); ancestor != null; ancestor = ancestor.GetParent())
            if (ancestor is Control { ClipContents: true } clip
                && !new Rect2(Vector2.Zero, clip.Size).HasPoint(
                    clip.GetGlobalTransformWithCanvas().AffineInverse() * sprite.GetGlobalTransformWithCanvas().Origin)) return false;
        return true;
    }

    public static bool Hoverable(NSovereignBladeVfx node) => Visible(node)
        && VisibleUi.Displayed(node.GetNodeOrNull<Control>("%Hitbox"))
        && node.GetNode<Control>("%Hitbox").MouseFilter != Control.MouseFilterEnum.Ignore
        && PrivateFields.Read(node, "_isAttacking") is false
        && !NTargetManager.Instance.IsInSelection;

    public static BladeText[] Read(NCreature owner, Func<CardModel, int> cardId) =>
        ReadNodes(VisibleNodes(owner, cardId), cardId);

    internal static BladeText[] ReadNodes(NSovereignBladeVfx[] nodes, Func<CardModel, int> cardId) =>
        nodes.Select(node => new BladeText(cardId(node.Card),
            EnglishCardText.Read(() => EnglishCardText.Plain(node.Card.TitleLocString.GetFormattedText())))).ToArray();

    public static bool Pending(NCreature owner) => owner.GetChildren().OfType<NSovereignBladeVfx>()
        .Any(node => RewardInspection.Animating(node, "_attackTween") || RewardInspection.Animating(node, "_scaleTween"));
}
