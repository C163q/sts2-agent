using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace Sts2Agent;

internal static class PresentationFixture
{
    private static Action? restore;

    public static object Set(string mode, RunResultInspection results)
    {
        restore?.Invoke(); restore = null;
        if (mode == "normal") return new { mode };
        Control root;
        object? tweenOwner = null;
        string? tweenField = null;
        RichTextLabel? text = null;
        if (results.Current is { } result) { root = result.Root; }
        else if (EpilogueInspection.Current is { } epilogue)
        {
            root = epilogue.Layout;
            text = (PrivateFields.Read(epilogue.Model, "_speechBubble") as Node)?.GetNode<RichTextLabel>("%Text");
        }
        else if (DivinationInspection.Current is { } board)
        {
            root = board;
            tweenOwner = root; tweenField = "_fadeTween";
        }
        else if (AncientInspection.Current is { } ancient)
        { root = ancient.Layout; tweenOwner = root; tweenField = "_contentTween"; }
        else if (ShopInspection.Current is { } shop)
        { root = shop.Owner; tweenOwner = shop.Inventory; tweenField = "_inventoryTween"; }
        else if (RewardInspection.Current is { } rewards)
        { root = rewards; tweenOwner = root; tweenField = "_fadeTween"; }
        else if (RestSiteInspection.Current is { } rest)
        { root = rest; tweenOwner = root; tweenField = "_choicesTween"; }
        else if (TreasureInspection.Current is { } treasure)
        { root = TreasureInspection.Collection(treasure); }
        else if (EventInspection.Current is { } currentEvent)
        { root = currentEvent.Layout; text = root.GetNode<RichTextLabel>("%EventDescription"); }
        else throw new InvalidOperationException("A supported exposed page is required.");

        if (mode == "disabled")
        {
            var buttons = VisibleUi.Descendants<NClickableControl>(root).Select(button => (button, button.IsEnabled)).ToArray();
            foreach (var (button, _) in buttons) button.SetEnabled(false);
            restore = () => { foreach (var (button, enabled) in buttons) if (GodotObject.IsInstanceValid(button)) button.SetEnabled(enabled); };
        }
        else if (mode == "partial")
        {
            if (text != null)
            {
                double ratio = text.VisibleRatio;
                text.VisibleRatio = .5f;
                restore = () => { if (GodotObject.IsInstanceValid(text)) text.VisibleRatio = (float)ratio; };
            }
            else
            {
                var alpha = root.Modulate;
                var tween = root.CreateTween();
                tween.TweenProperty(root, "modulate:a", .6f, 60);
                var field = tweenOwner != null ? AccessTools.Field(tweenOwner.GetType(), tweenField!)
                    ?? throw new MissingFieldException(tweenOwner.GetType().FullName, tweenField) : null;
                var previous = field?.GetValue(tweenOwner);
                field?.SetValue(tweenOwner, tween);
                restore = () => {
                    if (GodotObject.IsInstanceValid(tween)) tween.Kill();
                    if (GodotObject.IsInstanceValid(root)) root.Modulate = alpha;
                    field?.SetValue(tweenOwner, previous);
                };
            }
        }
        else throw new ArgumentException("Expected partial, disabled or normal.");
        return new { mode, page = root.GetType().Name };
    }
}
