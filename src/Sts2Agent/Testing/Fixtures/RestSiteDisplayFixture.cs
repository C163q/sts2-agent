using Godot;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class RestSiteDisplayFixture
{
    private static NRestSiteButton? button;
    private static Control? parent, label;
    private static RichTextLabel? description;
    private static Vector2 position, labelPosition;
    private static Control.MouseFilterEnum mouse;
    private static Control.FocusModeEnum focus;
    private static bool enabled, visible, clipped, parentClipped;
    private static Color modulate, descriptionModulate;
    private static string descriptionText = "";
    private static Tween? fade;

    public static void Reset()
    {
        if (fade != null && GodotObject.IsInstanceValid(fade)) fade.Kill();
        if (description != null && GodotObject.IsInstanceValid(description))
        { description.Text = descriptionText; description.Modulate = descriptionModulate; }
        if (button != null && GodotObject.IsInstanceValid(button))
        {
            if (enabled) button.Enable(); else button.Disable();
            button.Position = position;
            button.MouseFilter = mouse;
            button.FocusMode = focus;
            button.Visible = visible;
            button.Modulate = modulate;
            button.ClipContents = clipped;
        }
        if (label != null && GodotObject.IsInstanceValid(label)) label.Position = labelPosition;
        if (parent != null && GodotObject.IsInstanceValid(parent)) parent.ClipContents = parentClipped;
        button = null; parent = null; label = null; description = null; fade = null;
    }

    public static object Set(string mode)
    {
        Reset();
        if (mode == "normal") return new { mode, ready = RestSiteInspection.Current is { } current && RestSiteInspection.Ready(current) };
        var room = RestSiteInspection.Current;
        if (room == null || !RestSiteInspection.Ready(room))
            throw new InvalidOperationException("A ready test rest site is required.");
        button = RestSiteInspection.Buttons(room).Single(b => b.Option.OptionId == "HEAL");
        parent = button.GetParent<Control>();
        label = button.GetNode<Control>("%Label");
        description = room.GetNode<RichTextLabel>("%Description");
        position = button.Position; labelPosition = label.Position;
        mouse = button.MouseFilter; focus = button.FocusMode;
        enabled = button.IsEnabled; visible = button.Visible;
        modulate = button.Modulate; clipped = button.ClipContents;
        parentClipped = parent.ClipContents;
        descriptionText = description.Text; descriptionModulate = description.Modulate;
        switch (mode)
        {
            case "no_hover": button.MouseFilter = Control.MouseFilterEnum.Ignore; button.FocusMode = Control.FocusModeEnum.None; break;
            case "disabled": button.Disable(); break;
            case "offscreen": parent.ClipContents = false; button.Position = new Vector2(-10000, -10000); break;
            case "hidden": button.Visible = false; break;
            case "transparent": button.Modulate = new Color(modulate, 0); break;
            case "clipped": button.ClipContents = true; label.Position = new Vector2(10000, 10000); break;
            case "fade":
                room.SetText(button.Option.Description.GetFormattedText());
                room.FadeOutOptionDescription();
                fade = PrivateFields.Read(room, "_descriptionTween") as Tween;
                break;
            default: throw new ArgumentException("Unknown rest site display mode.");
        }
        return new { mode, ready = RestSiteInspection.Ready(room) };
    }
}
