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

    public static NButton Chest(NTreasureRoom room) => room.GetNode<NButton>("%Chest");
    public static NTreasureRoomRelicCollection Collection(NTreasureRoom room) => room.GetNode<NTreasureRoomRelicCollection>("%RelicCollection");
    public static bool Opened(NTreasureRoom room) => CardSelection.Field(room, "_hasChestBeenOpened") is true;
    private static bool Picking(NTreasureRoom room) => CardSelection.Field(room, "_isRelicCollectionOpen") is true;

    public static NTreasureRoomRelicHolder? Relic(NTreasureRoom room) => Opened(room) && Picking(room)
        && Collection(room).SingleplayerRelicHolder is { } holder && VisibleUi.OnScreen(holder)
        && VisibleUi.OnScreen(holder.Relic.Icon) && holder.Relic.Icon.Texture != null ? holder : null;

    private static bool RelicClickable(NTreasureRoom room) => Relic(room) is { IsEnabled: true } holder
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

    public static object? Read(bool full = false)
    {
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
                var details = RelicInspection.Details(holder.Relic.Model, null);
                value["description"] = details.description;
                value["hover_tips"] = details.hover_tips;
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
