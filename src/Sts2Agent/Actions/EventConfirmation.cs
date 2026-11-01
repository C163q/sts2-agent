using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class EventConfirmation
{
    private sealed record Origin(Trial Event, IRunState Run);
    private static readonly ConditionalWeakTable<NAbandonRunConfirmPopup, Origin> Origins = new();
    private static Task? abandonTask;
    private static IRunState? abandonRun;

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.event_confirmation");
        harmony.Patch(AccessTools.Method(typeof(Trial), "DoubleDown"),
            prefix: new HarmonyMethod(typeof(EventConfirmation), nameof(BeforeOpen)),
            postfix: new HarmonyMethod(typeof(EventConfirmation), nameof(Opened)));
        harmony.Patch(AccessTools.Method(typeof(RunManager), "AbandonInternal"),
            postfix: new HarmonyMethod(typeof(EventConfirmation), nameof(AbandonStarted)));
    }

    private static void BeforeOpen(out object? __state) => __state = NModalContainer.Instance?.OpenModal;

    private static void Opened(Trial __instance, object? __state)
    {
        if (__state == null && NModalContainer.Instance?.OpenModal is NAbandonRunConfirmPopup popup
            && ReferenceEquals(EventInspection.Current?.Model, __instance)
            && RunManager.Instance.DebugOnlyGetState() is { } run)
            Origins.Add(popup, new(__instance, run));
    }

    private static void AbandonStarted(Task __result)
    {
        abandonRun = RunManager.Instance.DebugOnlyGetState();
        abandonTask = __result;
    }

    public static bool AbandonPending => ReferenceEquals(abandonRun, RunManager.Instance.DebugOnlyGetState())
        && abandonTask is { IsCompleted: false };

    public static NAbandonRunConfirmPopup? Current => NModalContainer.Instance?.OpenModal is NAbandonRunConfirmPopup popup
        && Origins.TryGetValue(popup, out var origin) && ReferenceEquals(origin.Run, RunManager.Instance.DebugOnlyGetState())
        && ReferenceEquals(origin.Event, EventInspection.Current?.Model)
        && GodotObject.IsInstanceValid(popup) && popup.IsNodeReady() && !popup.IsQueuedForDeletion() ? popup : null;

    public static NVerticalPopup Contents(NAbandonRunConfirmPopup popup) => popup.GetNode<NVerticalPopup>("VerticalPopup");

    public static bool Exposed(NAbandonRunConfirmPopup popup) => ReferenceEquals(Current, popup)
        && TreasureInspection.Singleplayer && !RunUi.Transitioning() && NGame.Instance?.MainMenu == null
        && NRun.Instance?.GlobalUi is { } global && !global.CapstoneContainer.InUse && global.Overlays.ScreenCount == 0
        && !global.MapScreen.IsOpen && !global.MapScreen.IsTraveling
        && !VisibleUi.Shown(NGame.Instance!.InspectCardScreen) && !VisibleUi.Shown(NGame.Instance.InspectRelicScreen)
        && VisibleUi.Text(Contents(popup), "Header") is { Length: > 0 }
        && VisibleUi.Text(Contents(popup), "Description") is { Length: > 0 }
        && VisibleUi.Text(Contents(popup).YesButton, "%Label") is { Length: > 0 }
        && VisibleUi.Text(Contents(popup).NoButton, "%Label") is { Length: > 0 };

    public static bool Ready(NAbandonRunConfirmPopup popup) => Exposed(popup)
        && !RewardInspection.Animating(popup, "_tween") && !BackdropAnimating
        && !EventTaskTracker.Pending && !AbandonPending;

    public static bool BackdropAnimating => NModalContainer.Instance is { } modal
        && RewardInspection.Animating(modal, "_backstopTween");

    public static bool Clickable(NAbandonRunConfirmPopup popup, NPopupYesNoButton button) => Ready(popup)
        && VisibleUi.OnScreen(button) && button.IsEnabled && button.MouseFilter != Control.MouseFilterEnum.Ignore;

    public static object? Read()
    {
        if (Current is not { } popup || !Exposed(popup)) return null;
        return EnglishCardText.Read(() => (object)new {
            status = "visible", type = "abandon_run",
            title = Text("ABANDON_RUN_CONFIRMATION.header"), description = Text("ABANDON_RUN_CONFIRMATION.body"),
            options = new[] {
                new { id = "confirm", text = Text("GENERIC_POPUP.confirm"), enabled = Clickable(popup, Contents(popup).YesButton) },
                new { id = "cancel", text = Text("GENERIC_POPUP.cancel"), enabled = Clickable(popup, Contents(popup).NoButton) }
            }
        });
    }

    private static string Text(string key) => EnglishCardText.Plain(new LocString("main_menu_ui", key).GetFormattedText());
}
