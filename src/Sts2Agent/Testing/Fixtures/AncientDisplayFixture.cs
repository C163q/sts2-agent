using Godot;
using MegaCrit.Sts2.Core.Nodes.Events;

namespace Sts2Agent;

internal static class AncientDisplayFixture
{
    private static Action? restore;

    public static object Set(string mode)
    {
        restore?.Invoke(); restore = null;
        if (mode == "normal") return new { mode, title = (string?)null };
        var context = AncientInspection.Current ?? throw new InvalidOperationException("A test ancient is required.");
        var button = context.Layout.OptionButtons.First(b => !b.Option.IsProceed && !b.Option.IsLocked
            && (b.Option.Relic is { } relic ? EnglishRelicText.ExtraTips(relic) : b.Option.HoverTips).Any());
        var parents = new List<(Control control, bool clipped)>();
        for (Node? ancestor = button.GetParent(); ancestor != null; ancestor = ancestor.GetParent())
        {
            if (ancestor is Control control) parents.Add((control, control.ClipContents));
            if (ancestor == context.Layout) break;
        }
        var position = button.Position; var color = button.Modulate;
        var mouse = button.MouseFilter; var focus = button.FocusMode;
        bool visible = button.Visible, enabled = button.IsEnabled;
        restore = () => {
            if (!GodotObject.IsInstanceValid(button)) return;
            button.SetEnabled(enabled); button.Position = position; button.Modulate = color;
            button.MouseFilter = mouse; button.FocusMode = focus; button.Visible = visible;
            foreach (var (control, clipped) in parents)
                if (GodotObject.IsInstanceValid(control)) control.ClipContents = clipped;
        };
        switch (mode)
        {
            case "offscreen":
                foreach (var (control, _) in parents) control.ClipContents = false;
                button.Position = new Vector2(-10000, -10000); break;
            case "clipped": button.GetParent<Control>().ClipContents = true; button.Position = new Vector2(-10000, -10000); break;
            case "hidden": button.Visible = false; break;
            case "transparent": button.Modulate = new Color(color, 0); break;
            case "disabled": button.SetEnabled(false); break;
            case "no_hover": button.MouseFilter = Control.MouseFilterEnum.Ignore; button.FocusMode = Control.FocusModeEnum.None; break;
            case "controller_only": button.MouseFilter = Control.MouseFilterEnum.Ignore; button.FocusMode = Control.FocusModeEnum.All; break;
            default: throw new ArgumentException("Unknown ancient display mode.");
        }
        return new { mode, title = button.Option.TextKey };
    }
}
