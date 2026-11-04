using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace Sts2Agent;

internal sealed class PileInspection
{
    internal sealed record View(string? snapshot_id, string pile, string status, string message,
        Dictionary<string, object?>[] cards);
    private static readonly FieldInfo EmptyMessage = typeof(NCombatCardPile).GetField("_emptyPileMessage",
        BindingFlags.Instance | BindingFlags.NonPublic)!;
    private readonly CardIdentityMap<CardModel> ids = new();
    private object? combat;

    public static NCardPileScreen? Current(PileOptions options) => CardView.Current is NCardPileScreen screen
        && screen.Pile.Type == options.Type ? screen : null;

    public static LocString? EmptyTip(NCombatCardPile button) => EmptyMessage.GetValue(button) as LocString;

    public static bool InformationVisible(NCardPileScreen screen) =>
        VisibleUi.OnScreen(screen.GetNodeOrNull<Control>("%BottomLabel"));

    public View Read(NCardPileScreen screen, PileOptions options, string? snapshotId = null, bool full = true)
    {
        if (!ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState()))
        {
            combat = CombatManager.Instance.DebugOnlyGetState();
            ids.Clear();
        }
        if (!InformationVisible(screen))
            throw new InvalidOperationException("The pile information is not visible.");
        return EnglishCardText.Read(() => new View(snapshotId, options.Pile, "opened",
            EnglishCardText.Plain(new LocString("gameplay_ui", options.Pile.ToUpperInvariant() + "_PILE_INFO").GetFormattedText()),
            CardView.Cards(screen).Select(card => BrowsedCard.Read(card, "pile:" + ids.Get(card),
                options.Type, false, full, appearance: true)).ToArray()));
    }

    public static object Result(PileOptions options, string status, string snapshotId, string message,
        object? cards, string? reason = null)
    {
        var result = new Dictionary<string, object?>
        {
            ["snapshot_id"] = snapshotId, ["pile"] = options.Pile,
            ["status"] = status,
            ["message"] = message, ["cards"] = cards
        };
        if (reason != null) result["reason"] = reason;
        return result;
    }
}
