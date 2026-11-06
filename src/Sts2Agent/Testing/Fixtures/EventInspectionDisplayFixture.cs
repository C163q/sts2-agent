using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Nodes.Events;

namespace Sts2Agent;

internal static class EventInspectionDisplayFixture
{
    private static Action? restore;
    public static object Set(string mode)
    {
        restore?.Invoke(); restore = null;
        if (mode == "normal") return new { mode };
        var context = EventInspection.Current ?? throw new InvalidOperationException("A test event is required.");
        var button = context.Layout.OptionButtons.FirstOrDefault(b => b.Option.HoverTips.Any() && !b.Option.IsLocked)
            ?? context.Layout.OptionButtons.First();
        var parent = button.GetParent<Control>();
        var position = button.Position; bool visible = button.Visible, clipped = parent.ClipContents;
        var color = button.Modulate; var mouse = button.MouseFilter; var focus = button.FocusMode;
        var chosen = typeof(EventOption).GetField("<WasChosen>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic)!;
        bool wasChosen = button.Option.WasChosen;
        restore = () => {
            if (!GodotObject.IsInstanceValid(button)) return;
            button.Position = position; button.Visible = visible; parent.ClipContents = clipped;
            button.Modulate = color; button.MouseFilter = mouse; button.FocusMode = focus;
            chosen.SetValue(button.Option, wasChosen);
        };
        switch (mode)
        {
            case "offscreen": parent.ClipContents = false; button.Position = new Vector2(-10000, -10000); break;
            case "hidden": button.Visible = false; break;
            case "transparent": button.Modulate = new Color(color, 0); break;
            case "clipped": parent.ClipContents = true; button.Position = new Vector2(-10000, -10000); break;
            case "no_hover": button.MouseFilter = Control.MouseFilterEnum.Ignore; button.FocusMode = Control.FocusModeEnum.None; break;
            case "chosen": chosen.SetValue(button.Option, true); break;
            default: throw new ArgumentException("Unknown event display mode.");
        }
        return new { mode, title = button.Option.TextKey, tips = button.Option.HoverTips.Count() };
    }
}
