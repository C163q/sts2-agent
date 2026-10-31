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
        && (Animation.GetValue(screen) is not Tween tween || !GodotObject.IsInstanceValid(tween) || !tween.IsRunning())
        && (ActAnimation.GetValue(screen) is not Tween actTween || !GodotObject.IsInstanceValid(actTween) || !actTween.IsRunning())
        && VisibleUi.Descendants<NMapPoint>(screen).Any(VisibleUi.Shown);

    public static NButton? Back(NMapScreen screen) => screen.GetNodeOrNull<NButton>("Back");
    public static bool CanClose(NMapScreen screen) => Ready(screen)
        && Back(screen) is { IsEnabled: true } button && VisibleUi.OnScreen(button);
}
