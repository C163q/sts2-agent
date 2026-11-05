using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class MapView
{
    private static readonly FieldInfo Animation = typeof(NMapScreen).GetField("_tween", BindingFlags.Instance | BindingFlags.NonPublic)!;
    private static readonly FieldInfo ActAnimation = typeof(NMapScreen).GetField("_actAnimTween", BindingFlags.Instance | BindingFlags.NonPublic)!;
    private static readonly FieldInfo InputDisabled = typeof(NMapScreen).GetField("_isInputDisabled", BindingFlags.Instance | BindingFlags.NonPublic)!;

    public static Control? CardPage => NCapstoneContainer.Instance?.CurrentCapstoneScreen is Control screen
        && (screen is NDeckViewScreen || screen is NCardPileScreen pile
            && pile.Pile?.Type is PileType.Draw or PileType.Discard or PileType.Exhaust)
        && screen.IsNodeReady() && VisibleUi.Shown(screen) ? screen : null;

    public static bool Clear(bool allowCardView = false)
    {
        var game = NGame.Instance;
        var global = NRun.Instance?.GlobalUi;
        if (game == null || global == null || !global.IsNodeReady() || !RunManager.Instance.IsInProgress
            || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return false;
        if (global.CapstoneContainer.InUse && !(allowCardView && CardPage != null))
            return false;
        bool rewardsOnly = RunUi.OnlyRewardOverlays();
        return (global.Overlays.ScreenCount == 0 || rewardsOnly || DivinationInspection.OnlyOverlay || CardSelection.BattlefieldOverlay) && NModalContainer.Instance?.OpenModal == null
            && !VisibleUi.Shown(game.InspectCardScreen) && !VisibleUi.Shown(game.InspectRelicScreen)
            && !game.Transition.InTransition
            && !(VisibleUi.Shown(game.Transition) && game.Transition.Material is ShaderMaterial material
                && material.GetShaderParameter("threshold").AsSingle() > 0.000001f)
            && !VisibleUi.Descendants<CanvasItem>(game.Transition).Any(VisibleUi.Shown);
    }

    public static bool Current(NMapScreen screen) => ReferenceEquals(NMapScreen.Instance, screen)
        && GodotObject.IsInstanceValid(screen) && screen.IsNodeReady() && screen.IsOpen
        && VisibleUi.Shown(screen) && !screen.IsTraveling && Clear();

    public static bool Ready(NMapScreen screen) => Current(screen)
        && InputDisabled.GetValue(screen) is false
        && (Animation.GetValue(screen) is not Tween tween || !GodotObject.IsInstanceValid(tween) || !tween.IsRunning())
        && (ActAnimation.GetValue(screen) is not Tween actTween || !GodotObject.IsInstanceValid(actTween) || !actTween.IsRunning())
        && VisibleUi.Descendants<NMapPoint>(screen).Any(VisibleUi.Shown);

    public static NButton? Back(NMapScreen screen) => screen.GetNodeOrNull<NButton>("Back");
    public static bool CanClose(NMapScreen screen) => CloseUnavailableReason(screen) == null;

    public static string? CloseUnavailableReason(NMapScreen? screen)
    {
        if (!RunManager.Instance.IsInProgress || RunManager.Instance.DebugOnlyGetState() == null)
            return "No local run is available for map closing.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Map closing requires a local single-player run.";
        if (screen == null || !GodotObject.IsInstanceValid(screen) || !screen.IsNodeReady())
            return "The map is not ready.";
        if (!screen.IsOpen)
            return VisibleUi.Shown(screen) ? "The map is still closing. Wait for it to finish." : "No map is open.";
        if (screen.IsTraveling) return "Wait for map travel to finish before closing the map.";
        if (!Clear())
        {
            if (CardPage != null)
                return "Close the covering card page with close_card_view before closing the map.";
            if (RunUi.Transitioning()) return "Wait for the screen transition before closing the map.";
            return "The map is covered by a dialog, selection or another detail page.";
        }
        if (!Ready(screen)) return "The map is still preparing. Wait before closing it.";
        var button = Back(screen);
        if (button == null) return "The map has no return button.";
        if (!button.IsEnabled) return "The map return button is disabled.";
        return VisibleUi.OnScreen(button) ? null : "The map return button is not visible.";
    }
}
