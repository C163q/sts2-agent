using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Vfx;
using MegaCrit.Sts2.Core.Nodes.Vfx.Cards;

namespace Sts2Agent;

internal sealed class CardAdditionJournal : IDisposable
{
    private sealed class Addition(TurnEventBuffer.Reservation reservation)
    {
        public TurnEventBuffer.Reservation Reservation { get; } = reservation;
        public ulong Frame { get; } = VisibleUi.FrameNumber;
        public PileType? InitialPile;
        public bool DirectionClosed;
        public Dictionary<string, object?>? Fields;
    }
    private sealed record Flight(CardModel Card, NCard Node, CanvasItem Effect, PileType Pile)
    {
        public ulong Frame { get; } = VisibleUi.FrameNumber;
    }
    private static CardAdditionJournal? current;
    private readonly CombatState combat;
    private readonly Player player;
    private readonly TurnEventBuffer buffer;
    private readonly Func<CardModel, int> cardId;
    private readonly Action<CardModel, string> remember;
    private readonly EnglishText english = new();
    private readonly Dictionary<CardModel, Addition> additions = [];
    private readonly Dictionary<CardModel, (PileType pile, bool moved)> recentArrivals = [];
    private readonly List<Flight> flights = [];
    private ulong arrivalFrame;

    public CardAdditionJournal(CombatState combat, Player player, TurnEventBuffer buffer, Func<CardModel, int> cardId,
        Action<CardModel, string> remember)
    {
        if (current != null) throw new InvalidOperationException("Card additions are already being recorded.");
        this.combat = combat;
        this.player = player;
        this.buffer = buffer;
        this.cardId = cardId;
        this.remember = remember;
        current = this;
    }

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.card_add_destinations");
        harmony.Patch(AccessTools.Method(typeof(NCardFlyVfx), nameof(NCardFlyVfx.Create)),
            postfix: new HarmonyMethod(typeof(CardAdditionJournal), nameof(Flying)));
        harmony.Patch(AccessTools.Method(typeof(NExhaustVfx), nameof(NExhaustVfx.Create)),
            postfix: new HarmonyMethod(typeof(CardAdditionJournal), nameof(Exhausting)));
    }

    private static void Flying(NCard __0, PileType __1, bool __2, NCardFlyVfx? __result)
    {
        if (__2 && __result != null && NGame.IsMainThread()) current?.Witness(__0, __result, __1);
    }
    private static void Exhausting(NCard __0, NExhaustVfx? __result)
    {
        if (__result != null && NGame.IsMainThread()) current?.Witness(__0, __result, PileType.Exhaust);
    }

    private bool Visible => ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
        && CombatObservation.Status() == "visible";

    public void Generated(CardModel card)
    {
        RefreshArrivals();
        if (ReferenceEquals(card.Owner, player) && Visible && !additions.ContainsKey(card)
            && buffer.Reserve("card_added") is { } slot)
        {
            var entry = new Addition(slot);
            // Native Transform writes its generation history immediately after AddInternal.
            if (recentArrivals.Remove(card, out var arrival))
            {
                entry.InitialPile = arrival.pile;
                entry.DirectionClosed = arrival.moved;
            }
            additions.Add(card, entry);
        }
    }

    public void Added(CardModel card, PileType pile)
    {
        if (!Visible || !ReferenceEquals(card.Owner, player)) return;
        if (additions.TryGetValue(card, out var entry))
        {
            if (entry.InitialPile == null) entry.InitialPile = pile;
            else
            {
                entry.DirectionClosed = true;
                flights.RemoveAll(flight => ReferenceEquals(flight.Card, card));
            }
        }
        else
        {
            RefreshArrivals();
            if (recentArrivals.TryGetValue(card, out var arrival)) recentArrivals[card] = (arrival.pile, true);
            else if (recentArrivals.Count < 512) recentArrivals.Add(card, (pile, false));
        }
    }

    private void RefreshArrivals()
    {
        if (arrivalFrame == VisibleUi.FrameNumber) return;
        recentArrivals.Clear();
        arrivalFrame = VisibleUi.FrameNumber;
    }

    private void Witness(NCard node, CanvasItem effect, PileType pile)
    {
        if (Visible && node.Model is { } card && additions.TryGetValue(card, out var entry)
            && !entry.DirectionClosed && entry.InitialPile == pile) flights.Add(new(card, node, effect, pile));
    }

    public void SampleVisibility()
    {
        if (!Visible)
        {
            additions.Clear();
            recentArrivals.Clear();
            flights.Clear();
            return;
        }
        RefreshArrivals();
        var room = NCombatRoom.Instance!;
        foreach (var node in VisibleUi.Descendants<NCard>(NRun.Instance!))
        {
            if (node.Model is not { } card || !additions.TryGetValue(card, out var entry)
                || entry.InitialPile == null || VisibleUi.FrameNumber <= entry.Frame || node.Visibility != ModelVisibility.Visible
                || !CombatObservation.CardVisible(node)) continue;
            if (entry.Fields == null && english.CardName(node) is { } name)
            {
                remember(card, name);
                entry.Fields = entry.Reservation.Publish(new() { ["card"] = new { id = cardId(card), name }, ["pile"] = null });
            }
            if (entry.InitialPile == PileType.Hand && room.Ui.Hand.ActiveHolders.Any(holder =>
                    ReferenceEquals(holder.CardNode, node) && VisibleUi.Shown(holder)))
                Destination(entry, PileType.Hand);
            if (entry.InitialPile == PileType.Play && room.Ui.PlayContainer.IsAncestorOf(node))
                Destination(entry, PileType.Play);
        }
        foreach (var flight in flights.ToArray())
        {
            if (!GodotObject.IsInstanceValid(flight.Effect) || flight.Effect.IsQueuedForDeletion()
                || !GodotObject.IsInstanceValid(flight.Node) || flight.Node.IsQueuedForDeletion())
            {
                flights.Remove(flight);
                continue;
            }
            if (VisibleUi.FrameNumber <= flight.Frame) continue;
            if (!VisibleUi.Shown(flight.Effect) || !VisibleUi.Shown(flight.Node)
                || flight.Node.Visibility != ModelVisibility.Visible)
                flights.Remove(flight);
            else if (additions.TryGetValue(flight.Card, out var entry) && CombatObservation.CardVisible(flight.Node)
                && CombatCardPiles.Visible(flight.Pile))
            {
                Destination(entry, flight.Pile);
                flights.Remove(flight);
            }
            // The exhaust button can first animate into view when the card reaches it.
        }
    }

    private static void Destination(Addition entry, PileType pile)
    {
        if (!entry.DirectionClosed && entry.Fields != null && entry.Fields["pile"] == null)
            entry.Fields["pile"] = pile.ToString().ToLowerInvariant();
    }

    public void Dispose()
    {
        additions.Clear();
        recentArrivals.Clear();
        flights.Clear();
        if (ReferenceEquals(current, this)) current = null;
    }
}
