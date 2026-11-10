using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal sealed class CardMovementJournal : IDisposable
{
    private sealed class DrawContext { public Task? Completion; }
    private sealed record Departure(PileType Pile, string? Name, bool Identified, bool Sole);
    private sealed class Movement(CardModel card, Departure departure, PileType target, TurnEventBuffer.Reservation slot)
    {
        public CardModel Card = card;
        public Departure Departure = departure;
        public PileType Target = target;
        public TurnEventBuffer.Reservation Slot = slot;
        public CanvasItem? Flight;
        public NCard? Node;
        public ulong Frame;
        public bool Anonymous;
        public bool Chosen;
        public DrawContext? Draw;
        public int HistoryCursor;
        public bool Seen;
        public string? Name;
    }
    private static readonly AsyncLocal<bool> Shuffling = new();
    private static readonly AsyncLocal<DrawContext?> Drawing = new();
    private static CardMovementJournal? current;
    private readonly CombatState combat;
    private readonly Player player;
    private readonly TurnEventBuffer buffer;
    private readonly Func<CardModel, int> cardId;
    private readonly Func<CardModel, string?> cardName;
    private readonly Dictionary<CardModel, Departure> departures = [];
    private readonly List<Movement> movements = [];
    private readonly HashSet<CardModel> choices = [];
    private readonly Dictionary<PileType, CardModel> singletons = [];
    private readonly List<Action> cleanup = [];

    public CardMovementJournal(CombatState combat, Player player, TurnEventBuffer buffer,
        Func<CardModel, int> cardId, Func<CardModel, string?> cardName)
    {
        if (current != null) throw new InvalidOperationException("Card movements are already being recorded.");
        this.combat = combat;
        this.player = player;
        this.buffer = buffer;
        this.cardId = cardId;
        this.cardName = cardName;
        current = this;
        if (CardSelection.Current is { Status: "visible" } selection)
            foreach (var card in selection.Selected) choices.Add(card);
        foreach (var type in new[] { PileType.Hand, PileType.Draw, PileType.Discard, PileType.Exhaust, PileType.Play })
        {
            var pile = type.GetPile(player);
            if (Visible && pile.Cards.Count == 1 && CombatCardPiles.Count(type) == 1) singletons[type] = pile.Cards[0];
            void Removed(CardModel card) => Removing(card, pile);
            void Added(CardModel card) => Arrived(card, type);
            pile.CardRemoved += Removed;
            pile.CardAdded += Added;
            cleanup.Add(() => { pile.CardRemoved -= Removed; pile.CardAdded -= Added; });
        }
    }

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.card_movements");
        harmony.Patch(AccessTools.Method(typeof(CardPileCmd), nameof(CardPileCmd.Shuffle)),
            prefix: new HarmonyMethod(typeof(CardMovementJournal), nameof(BeforeShuffle)),
            finalizer: new HarmonyMethod(typeof(CardMovementJournal), nameof(AfterShuffle)));
        harmony.Patch(AccessTools.Method(typeof(CardPileCmd), nameof(CardPileCmd.Draw),
                [typeof(PlayerChoiceContext), typeof(decimal), typeof(Player), typeof(bool)]),
            prefix: new HarmonyMethod(typeof(CardMovementJournal), nameof(BeforeDraw)),
            postfix: new HarmonyMethod(typeof(CardMovementJournal), nameof(DrawTask)),
            finalizer: new HarmonyMethod(typeof(CardMovementJournal), nameof(AfterDraw)));
        harmony.Patch(AccessTools.Method(typeof(NCardFlyVfx), nameof(NCardFlyVfx.Create),
            [typeof(NCard), typeof(PileType), typeof(bool), typeof(string)]),
            postfix: new HarmonyMethod(typeof(CardMovementJournal), nameof(Flying)));
        harmony.Patch(AccessTools.Method(typeof(NCardFlyShuffleVfx), nameof(NCardFlyShuffleVfx.Create)),
            postfix: new HarmonyMethod(typeof(CardMovementJournal), nameof(FlyingBack)));
    }

    // The async native body inherits this context; the caller is restored immediately.
    private static void BeforeShuffle(out bool __state) { __state = Shuffling.Value; Shuffling.Value = true; }
    private static void AfterShuffle(bool __state) => Shuffling.Value = __state;
    private static void BeforeDraw(out DrawContext? __state) { __state = Drawing.Value; Drawing.Value = new(); }
    private static void DrawTask(Task<IEnumerable<CardModel>> __result)
    {
        if (Drawing.Value is { } context) context.Completion = __result;
    }
    private static void AfterDraw(DrawContext? __state) => Drawing.Value = __state;
    public static void Choose(CardModel card) => current?.choices.Add(card);
    private bool Visible => ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
        && CombatObservation.Status() == "visible";

    private static bool Identified(NCard? node) => node?.Visibility == ModelVisibility.Visible && CombatObservation.CardVisible(node);

    private void Removing(CardModel card, CardPile pile)
    {
        departures.Remove(card);
        bool sole = singletons.Remove(pile.Type, out var singleton) && ReferenceEquals(singleton, card);
        if (Shuffling.Value || !ReferenceEquals(card.Owner, player) || !Visible && !choices.Contains(card)) return;
        if (departures.Count < 512)
            departures[card] = new(pile.Type, cardName(card), Identified(NCard.FindOnTable(card)), sole);
    }

    private void Arrived(CardModel card, PileType target)
    {
        singletons.Remove(target);
        if (!departures.Remove(card, out var departure) || Shuffling.Value
            || !Visible && !choices.Contains(card) || departure.Pile == target) return;
        // Existing specialized events already describe these moves.
        if (target == PileType.Exhaust
            || departure.Pile == PileType.Hand && target is PileType.Discard or PileType.Play) return;
        if (buffer.Reserve("card_moved") is { } slot)
            movements.Add(new(card, departure, target, slot) {
                Chosen = choices.Remove(card),
                Draw = departure.Pile == PileType.Draw && target == PileType.Hand ? Drawing.Value : null,
                HistoryCursor = CombatManager.Instance.History.Entries.Count() });
    }

    private static void Flying(NCard __0, PileType __1, bool __2, NCardFlyVfx? __result)
    {
        if (!__2 || __result == null || !NGame.IsMainThread() || current is not { } journal || Shuffling.Value) return;
        var movement = journal.movements.FirstOrDefault(m => ReferenceEquals(m.Card, __0.Model) && m.Target == __1 && m.Flight == null);
        if (movement != null)
        {
            movement.Flight = __result;
            movement.Node = __0;
            movement.Frame = VisibleUi.FrameNumber;
        }
    }

    private static void FlyingBack(CardPile __0, CardPile __1, NCardFlyShuffleVfx? __result)
    {
        if (__result == null || !NGame.IsMainThread() || current is not { } journal || Shuffling.Value
            || !__0.IsCombatPile || !__1.IsCombatPile
            || !ReferenceEquals(__0, __0.Type.GetPile(journal.player))
            || !ReferenceEquals(__1, __1.Type.GetPile(journal.player))) return;
        var movement = journal.movements.FirstOrDefault(m => m.Departure.Pile == __0.Type && m.Target == __1.Type && m.Flight == null);
        if (movement != null)
        {
            movement.Flight = __result;
            movement.Anonymous = true;
            movement.Frame = VisibleUi.FrameNumber;
        }
    }

    public void SampleVisibility()
    {
        if (!Visible) { departures.Clear(); movements.Clear(); singletons.Clear(); return; }
        var room = NCombatRoom.Instance!;
        foreach (var movement in movements.ToArray())
        {
            if (movement.Draw?.Completion?.IsCompleted == true && CombatManager.Instance.History.Entries
                .Skip(movement.HistoryCursor).OfType<CardDrawnEntry>().Any(entry => ReferenceEquals(entry.Card, movement.Card)))
            {
                movements.Remove(movement);
                continue;
            }
            bool displayed = false;
            if (movement.Flight is { } flight)
            {
                if (!GodotObject.IsInstanceValid(flight) || flight.IsQueuedForDeletion()) { movements.Remove(movement); continue; }
                if (VisibleUi.FrameNumber <= movement.Frame) continue;
                displayed = VisibleUi.Shown(flight) && CombatCardPiles.Visible(movement.Departure.Pile) && CombatCardPiles.Visible(movement.Target)
                    && (movement.Anonymous
                        ? movement.Chosen || movement.Departure.Sole || movement.Departure.Identified
                        : Identified(movement.Node) || VisibleUi.Shown(movement.Node)
                            && (movement.Chosen || movement.Departure.Sole || movement.Departure.Identified));
            }
            else if (movement.Target is PileType.Hand or PileType.Play)
            {
                var node = NCard.FindOnTable(movement.Card);
                displayed = Identified(node) && CombatCardPiles.Visible(movement.Departure.Pile)
                    && (movement.Target == PileType.Hand
                        ? room.Ui.Hand.ActiveHolders.Any(holder => ReferenceEquals(holder.CardNode, node))
                        : room.Ui.PlayContainer.IsAncestorOf(node));
            }
            if (!displayed && !movement.Seen) continue;
            movement.Seen = true;
            movement.Name = cardName(movement.Card) ?? movement.Name ?? movement.Departure.Name;
            // A Draw call can include non-draw returns in its hooks; only actual history proves duplication.
            if (movement.Draw != null && movement.Draw.Completion?.IsCompleted != true) continue;
            movement.Slot.Publish(new() { ["card"] = new { id = cardId(movement.Card), name = movement.Name },
                ["from_pile"] = movement.Departure.Pile.ToString().ToLowerInvariant(),
                ["to_pile"] = movement.Target.ToString().ToLowerInvariant() });
            movements.Remove(movement);
        }
    }

    public void Dispose()
    {
        foreach (var unsubscribe in cleanup) unsubscribe();
        movements.Clear(); departures.Clear(); choices.Clear(); singletons.Clear();
        if (ReferenceEquals(current, this)) current = null;
    }
}
