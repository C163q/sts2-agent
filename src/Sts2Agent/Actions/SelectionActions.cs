using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;

namespace Sts2Agent;

internal static class SelectionActions
{
    public static bool Same(CardSelection selection) => CardSelection.Current is { } current
        && ReferenceEquals(current.Owner, selection.Owner) && ReferenceEquals(current.Key, selection.Key);

    public static async Task Click(CardSelection selection, CardModel model, Func<Task> frame)
    {
        if (!selection.CanSelect || !selection.Cards.Contains(model))
            throw new InvalidOperationException("This card cannot be selected.");
        var candidates = selection.Cards;
        var selected = selection.Selected;
        var limits = selection.Limits;
        bool confirmation = selection.Prefs.RequireManualConfirmation;
        bool Unchanged() => Same(selection) && selection.Status == "visible" && !selection.InPreview
            && selection.Cards.SequenceEqual(candidates)
            && selection.Selected.SequenceEqual(selected) && selection.Limits == limits
            && selection.Prefs.RequireManualConfirmation == confirmation;
        NCardHolder? holder = selection.Holders.FirstOrDefault(holder => ReferenceEquals(holder.CardModel, model));
        if (selection.Grid is { } grid && (holder == null || !CardSelection.Clickable(holder)))
        {
            // Follow the native grid layout, then let its virtualized rows catch up before clicking.
            int index = Array.IndexOf(selection.Cards, model);
            int columns = (int)HarmonyLib.AccessTools.Property(grid.GetType(), "Columns").GetValue(grid)!;
            var size = (Vector2)PrivateFields.Read(grid, "_cardSize")!;
            float padding = (float)HarmonyLib.AccessTools.Property(grid.GetType(), "CardPadding").GetValue(grid)!;
            grid.SetScrollPosition(-index / columns * (size.Y + padding));
            for (int i = 0; i < 10; i++)
            {
                // SetScrollPosition jumps directly and bypasses the native drag-update allocation.
                HarmonyLib.AccessTools.Method(grid.GetType(), "AllocateCardHolders").Invoke(grid, null);
                await frame();
                if (!Unchanged()) throw new InvalidOperationException("The selection changed while scrolling.");
                holder = grid.GetCardHolder(model);
                if (holder != null && CardSelection.Clickable(holder)) break;
            }
        }
        if (!Unchanged() || !selection.CanSelect || holder == null || !CardSelection.Clickable(holder))
            throw new InvalidOperationException("The candidate is not clickable.");
        // The native holder emits this signal for mouse/controller selection.
        holder.EmitSignal(NCardHolder.SignalName.Pressed, holder);
    }
}
