using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace Sts2Agent;

internal static class HoverAccess
{
    private static readonly PropertyInfo DisabledFocus = typeof(NClickableControl)
        .GetProperty("AllowFocusWhileDisabled", BindingFlags.Instance | BindingFlags.NonPublic)
        ?? throw new MissingMemberException(typeof(NClickableControl).FullName, "AllowFocusWhileDisabled");

    public static bool CanFocus(NClickableControl control) =>
        (control.IsEnabled || (bool)DisabledFocus.GetValue(control)!)
        && (control.MouseFilter != Control.MouseFilterEnum.Ignore || control.FocusMode == Control.FocusModeEnum.All);
}
