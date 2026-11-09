using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace Sts2Agent;

internal sealed class RunInventoryJournal : IDisposable
{
    public static RunInventoryJournal? Current { get; private set; }
    private readonly Player player;
    private readonly TurnEventBuffer buffer;
    private readonly Func<CardModel, int> cardId;
    private readonly EnglishText english = new();
    private readonly Dictionary<CardModel, string> knownCards = [];
    private readonly Dictionary<RelicModel, string> knownRelics = [];
    private readonly Dictionary<RelicModel, bool> knownMelted = [];
    private readonly HashSet<RelicModel> watchedRelics = [];
    private readonly HashSet<CardModel> watched = [];
    private readonly HashSet<(CardModel card, string type)> numericChanges = [];
    private readonly List<Action> cleanup = [];
    private readonly List<Action> pending = [];

    public RunInventoryJournal(Player player, TurnEventBuffer buffer, Func<CardModel, int> cardId)
    {
        if (Current != null) throw new InvalidOperationException("Inventory is already being recorded.");
        this.player = player;
        this.buffer = buffer;
        this.cardId = cardId;
        SampleVisibility();
        foreach (var card in player.Deck.Cards) Watch(card);
        foreach (var relic in player.Relics) Watch(relic);
        player.Deck.CardAdded += Added;
        player.Deck.CardRemoved += Removed;
        player.RelicObtained += RelicObtained;
        player.RelicRemoved += RelicRemoved;
        player.PotionProcured += PotionObtained;
        Current = this;
    }

    private bool Visible => RunResourceJournal.Current?.TopBarVisible == true;

    private IEnumerable<NCard> VisibleCards()
    {
        if (!Visible || NRun.Instance is not { } run) return [];
        // A native selection covers the room behind it; only its own cards are exposed.
        Node root = CardSelection.Current is { Status: "visible" } selection ? selection.Owner : run;
        return VisibleUi.Descendants<NCard>(root).Where(node => node.Model is { IsMutable: true } model && model.Owner == player
            && node.Visibility == ModelVisibility.Visible && CombatObservation.CardVisible(node));
    }

    public void SampleVisibility()
    {
        if (!Visible)
        {
            knownCards.Clear();
            knownRelics.Clear();
            knownMelted.Clear();
            pending.Clear();
            numericChanges.Clear();
            return;
        }
        foreach (var node in VisibleCards()) Remember(node.Model!, node);
        if (CardSelection.Current is { Status: "visible" } selection)
        {
            if (selection.Kind == "deck_upgrade")
                foreach (var pair in DeckUpgradeSelection.Previews(selection)) Remember(pair.original, pair.before);
            if (selection.Kind == "deck_enchant")
                foreach (var pair in DeckEnchantSelection.Previews(selection)) Remember(pair.original, pair.before);
            if (selection.Kind == "deck_transform")
                foreach (var pair in TransformSelection.Previews(selection)) Remember(pair.original, pair.before);
        }
        var inventory = NRun.Instance!.GlobalUi.RelicInventory;
        knownRelics.Clear();
        var visibleRelics = new HashSet<RelicModel>();
        if (VisibleUi.OnScreen(inventory))
            foreach (var holder in inventory.RelicNodes)
                if (VisibleUi.OnScreen(holder) && VisibleUi.OnScreen(holder.Relic.Icon)
                    && holder.Relic.Icon.Texture != null && english.RelicName(holder.Relic.Model) is { } name)
                {
                    var relic = holder.Relic.Model;
                    knownRelics[relic] = name;
                    visibleRelics.Add(relic);
                    SampleMelted(relic);
                }
        foreach (var relic in knownMelted.Keys.Where(relic => !visibleRelics.Contains(relic)).ToArray())
            knownMelted.Remove(relic);
        foreach (var publish in pending.ToArray()) publish();
    }

    private void Remember(CardModel original, NCard? node)
    {
        if (node?.Visibility == ModelVisibility.Visible && CombatObservation.CardVisible(node)
            && english.CardName(node) is { } name)
        {
            knownCards[original] = name;
            // A combat-only upgrade does not establish the permanent card's upgrade suffix.
            if (original.DeckVersion is { } deck && TracksPermanent(deck) && original.Id.Equals(deck.Id)
                && english.Name(original.TitleLocString) is { } baseName) knownCards.TryAdd(deck, baseName);
        }
    }

    internal bool TracksPermanent(CardModel card) => card.IsMutable && ReferenceEquals(card.Owner, player)
        && player.Deck.Cards.Contains(card);

    internal void NumericChanged(CardModel card, string type)
    {
        if (Visible && TracksPermanent(card) && numericChanges.Add((card, type))) Card(type, card);
    }

    internal void EnchantmentChanged(CardModel card)
    {
        if (TracksPermanent(card)) Card("card_enchantment_changed", card);
    }

    private void Defer(string type, Func<Dictionary<string, object?>?> fields, Func<bool>? areaVisible = null)
    {
        if (!Visible || areaVisible?.Invoke() == false || buffer.Reserve(type) is not { } slot) return;
        Action? publish = null;
        publish = () =>
        {
            if (!Visible || areaVisible?.Invoke() == false)
            {
                pending.Remove(publish!);
                return;
            }
            if (fields() is not { } values) return;
            slot.Publish(values);
            pending.Remove(publish!);
        };
        pending.Add(publish);
        publish();
    }

    private void Card(string type, CardModel card)
    {
        if (card.Owner != player) return;
        Defer(type, () => knownCards.TryGetValue(card, out string? name)
            ? new() { ["card"] = new { id = cardId(card), name }, ["pile"] = "deck" } : null);
    }

    private void Added(CardModel card) { Watch(card); Card("card_added", card); }
    private void Removed(CardModel card) => Card("card_removed", card);

    private void Watch(CardModel card)
    {
        if (!watched.Add(card)) return;
        int level = card.CurrentUpgradeLevel;
        void Upgraded()
        {
            int before = level;
            level = card.CurrentUpgradeLevel;
            if (!player.Deck.Cards.Contains(card) || before == level) return;
            Card(level > before ? "card_upgraded" : "card_downgraded", card);
        }
        card.Upgraded += Upgraded;
        cleanup.Add(() => card.Upgraded -= Upgraded);
    }

    private void Watch(RelicModel relic)
    {
        if (!watchedRelics.Add(relic)) return;
        void Status() => SampleMelted(relic);
        relic.StatusChanged += Status;
        cleanup.Add(() => relic.StatusChanged -= Status);
    }

    private void SampleMelted(RelicModel relic)
    {
        var holder = Visible ? NRun.Instance!.GlobalUi.RelicInventory.RelicNodes
            .FirstOrDefault(node => ReferenceEquals(node.Relic.Model, relic) && VisibleUi.OnScreen(node)) : null;
        if (holder == null || RelicInspection.Melted(holder.Relic) is not { } melted)
        {
            knownMelted.Remove(relic);
            return;
        }
        if (melted && knownMelted.TryGetValue(relic, out bool before) && !before
            && english.RelicName(relic) is { } name)
            buffer.Add("relic_melted", new() { ["relic"] = new { name } });
        knownMelted[relic] = melted;
    }

    private void RelicObtained(RelicModel relic)
    {
        Watch(relic);
        Defer("relic_obtained", () =>
            knownRelics.TryGetValue(relic, out string? name) ? new() { ["relic"] = new { name } } : null,
            () => VisibleUi.OnScreen(NRun.Instance?.GlobalUi.RelicInventory));
    }

    private void RelicRemoved(RelicModel relic)
    {
        knownMelted.Remove(relic);
        if (Visible && VisibleUi.OnScreen(NRun.Instance!.GlobalUi.RelicInventory)
            && knownRelics.Remove(relic, out string? name))
            buffer.Add("relic_removed", new() { ["relic"] = new { name } });
    }

    private void PotionObtained(PotionModel potion)
    {
        int slot = player.GetPotionSlotIndex(potion);
        Defer("potion_obtained", () => ReferenceEquals(PotionInspection.DisplayedAt(slot)?.Potion?.Model, potion) && slot >= 0
            && english.Name(potion.Title) is { } name
                ? new() { ["potion"] = new { slot_index = slot, name } } : null,
            () => VisibleUi.OnScreen(NRun.Instance?.GlobalUi.TopBar.PotionContainer));
    }

    public void Dispose()
    {
        player.Deck.CardAdded -= Added;
        player.Deck.CardRemoved -= Removed;
        player.RelicObtained -= RelicObtained;
        player.RelicRemoved -= RelicRemoved;
        player.PotionProcured -= PotionObtained;
        foreach (var unsubscribe in cleanup) unsubscribe();
        pending.Clear();
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
