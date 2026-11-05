using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class TreasureInspection
{
    public static NTreasureRoom? Current => RunManager.Instance.DebugOnlyGetState()?.CurrentRoom is TreasureRoom
        && NRun.Instance?.GetNodeOrNull<Node>("%RoomContainer") is { } container
        ? VisibleUi.Descendants<NTreasureRoom>(container).LastOrDefault(r => !r.IsQueuedForDeletion() && r.IsNodeReady()) : null;

    public static bool Exposed(NTreasureRoom room) => ReferenceEquals(Current, room) && RunUi.NonCombatVisible()
        && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0 && !RunUi.CardPreviewsPending()
        && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen) && VisibleUi.Shown(room);

    public static string? InspectionUnavailableReason(NTreasureRoom? room)
    {
        if (room != null && GodotObject.IsInstanceValid(room) && Exposed(room)) return null;
        if (!RunManager.Instance.IsInProgress) return "No local run is available for treasure inspection.";
        if (room == null || !GodotObject.IsInstanceValid(room)) return "No treasure room is available on the current screen.";
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (VisibleUi.Shown(map))
            return map!.IsOpen ? "Close the map with close_map before inspecting the chest."
                : "Wait for the map to finish closing before inspecting the chest.";
        if (CardView.Current != null) return "Close the card browsing page with close_card_view before inspecting the chest.";
        if (CardSelection.Current != null)
            return "Resolve the current card selection before inspecting the chest; inspect_selection shows its choices.";
        if (RewardInspection.Current != null)
            return "Resolve the current reward page before inspecting the chest; inspect_rewards shows its rows.";
        if (RunUi.CardPreviewsPending()) return "Wait for card previews to finish before inspecting the chest.";
        if (RunUi.Transitioning()) return "Wait for the screen transition before inspecting the chest.";
        return "The treasure room is covered by a dialog or another screen.";
    }

    public static NButton Chest(NTreasureRoom room) => room.GetNode<NButton>("%Chest");
    public static NTreasureRoomRelicCollection Collection(NTreasureRoom room) => room.GetNode<NTreasureRoomRelicCollection>("%RelicCollection");
    public static bool Opened(NTreasureRoom room) => PrivateFields.Read(room, "_hasChestBeenOpened") is true;
    private static bool Picking(NTreasureRoom room) => PrivateFields.Read(room, "_isRelicCollectionOpen") is true;

    public static NTreasureRoomRelicHolder? Relic(NTreasureRoom room) => Opened(room) && Picking(room)
        && Collection(room).SingleplayerRelicHolder is { } holder && VisibleUi.Displayed(holder)
        && VisibleUi.Displayed(holder.Relic) && VisibleUi.Displayed(holder.Relic.Icon)
        && holder.Relic.Icon.Texture != null ? holder : null;

    private static bool RelicClickable(NTreasureRoom room) => Relic(room) is { IsEnabled: true } holder
        && VisibleUi.OnScreen(holder) && VisibleUi.OnScreen(holder.Relic.Icon)
        && holder.MouseFilter == Control.MouseFilterEnum.Stop && holder.Modulate.A >= 0.99f
        && Collection(room).Modulate.A >= 0.99f
        && !RewardInspection.Animating(holder, "_initTween")
        && RunManager.Instance.TreasureRoomRelicSynchronizer.GetPlayerVote(
            MegaCrit.Sts2.Core.Context.LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState())!).voteReceived == false;

    public static NProceedButton? Proceed(NTreasureRoom room) => VisibleUi.OnScreen(room.ProceedButton)
        && VisibleUi.Text(room.ProceedButton, "%Label") is { Length: > 0 } ? room.ProceedButton : null;

    public static bool Ready(NTreasureRoom room)
    {
        if (!RunContext.Singleplayer || !Exposed(room) || !RunManager.Instance.ActionQueueSet.IsEmpty || RelicObtainTracker.Pending) return false;
        if (!Opened(room)) return Chest(room).IsEnabled && VisibleUi.OnScreen(Chest(room));
        if (Proceed(room)?.IsEnabled != true) return false;
        return Picking(room) ? RelicClickable(room) : !VisibleUi.Shown(Collection(room));
    }

    public static bool CanLoot(NTreasureRoom room) => Ready(room) && (!Opened(room) || RelicClickable(room));

    public static object? Read(bool full = false) => Read(full, out _);

    public static object Inspect()
    {
        var treasure = Read(full: true, out var unavailable);
        return new { treasure, unavailable_hover_sources = unavailable };
    }

    private static object? Read(bool full, out string[] unavailable)
    {
        unavailable = [];
        if (Current is not { } room) return null;
        if (!Exposed(room)) return new { status = "covered", chest = (string?)null, relic = (object?)null, proceed = (object?)null };
        bool ready = Ready(room);
        string chest = Opened(room) ? "open" : Chest(room).IsEnabled ? "closed" : "opening";
        object? relic = null;
        if (Relic(room) is { } holder)
        {
            var value = new Dictionary<string, object?>
            {
                ["name"] = EnglishCardText.Read(() => EnglishCardText.Plain(holder.Relic.Model.Title.GetFormattedText())),
                ["enabled"] = ready && RelicClickable(room)
            };
            if (full)
            {
                bool hoverable = HoverAccess.CanFocus(holder);
                var details = hoverable ? RelicInspection.Details(holder.Relic.Model, null) : null;
                value["description"] = details?.description;
                value["hover_tips"] = details?.hover_tips ?? [];
                if (!hoverable) unavailable = ["treasure.relic"];
            }
            relic = value;
        }
        var button = Proceed(room);
        object? proceed = button == null ? null : new
        {
            text = EnglishCardText.Read(() => EnglishCardText.Plain((button.IsSkip ? NProceedButton.SkipLoc : NProceedButton.ProceedLoc).GetFormattedText())),
            enabled = ready && button.IsEnabled, skips_remaining = button.IsSkip
        };
        return new { status = "visible", chest, relic, proceed };
    }
}
