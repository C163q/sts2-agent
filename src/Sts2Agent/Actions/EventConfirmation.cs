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
        && RunContext.Singleplayer && !RunUi.Transitioning() && NGame.Instance?.MainMenu == null
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

    private static string? PageUnavailableReason(NAbandonRunConfirmPopup? popup)
    {
        if (popup == null && NModalContainer.Instance?.OpenModal != null)
            return "This dialog is not a supported Trial confirmation. Resolve it in game before continuing.";
        if (VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen))
            return "The map is open or closing. Use close_map to return to the current room before responding to a Trial confirmation.";
        if (CardView.Current != null)
            return "Close the card browsing page with close_card_view before responding to a Trial confirmation.";
        if (popup == null) return "No supported Trial confirmation is open. Use the current screen's available actions.";
        if (!RunContext.Singleplayer) return "A local single-player run is required for a Trial confirmation.";
        return Exposed(popup) ? null : "The Trial confirmation is opening or covered. Wait for the dialog or return from the covering screen.";
    }

    public static string? ActionUnavailableReason(NAbandonRunConfirmPopup? popup)
    {
        if (PageUnavailableReason(popup) is { } reason) return reason;
        if (!Ready(popup!)) return "Wait for the Trial confirmation animations and pending event or abandon effects to finish.";
        var contents = Contents(popup!);
        return Clickable(popup!, contents.YesButton) || Clickable(popup!, contents.NoButton) ? null
            : "No confirmation button is currently interactive. Wait for an enabled option.";
    }

    public static string? ButtonUnavailableReason(NAbandonRunConfirmPopup popup, NPopupYesNoButton button)
    {
        if (!Ready(popup)) return "Wait for the Trial confirmation and its current effects to finish.";
        if (!VisibleUi.OnScreen(button)) return "This confirmation button is not visible. Read the current dialog before continuing.";
        if (!button.IsEnabled) return "This confirmation button is disabled. Choose an enabled option.";
        return button.MouseFilter == Control.MouseFilterEnum.Ignore
            ? "This confirmation button is not currently interactive. Wait for an enabled option." : null;
    }

    public static bool Clickable(NAbandonRunConfirmPopup popup, NPopupYesNoButton button) =>
        ButtonUnavailableReason(popup, button) == null;

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
