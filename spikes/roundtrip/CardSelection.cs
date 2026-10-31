using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;

namespace Sts2Agent;

internal sealed class CardSelection(Control owner, string kind, object key)
{
    public Control Owner { get; } = owner;
    public string Kind { get; } = kind;
    public object Key { get; } = key;
    public bool Supported => Kind != "unsupported";
    public NCardGrid? Grid => Owner is NCardGridSelectionScreen || Kind == "view_cards" ? Owner.GetNodeOrNull<NCardGrid>("%CardGrid") : null;
    public NPeekButton? Eye => Owner is NPlayerHand hand ? hand.PeekButton : Owner.GetNodeOrNull<NPeekButton>("%PeekButton");
    public bool Peeking => Eye?.IsPeeking == true;
    public static bool AwaitingInput => Current is { Status: "visible" or "unsupported" } selection
        && (selection.Kind != "reward" || (selection.Holders.Length == 0 || selection.CanSelect)
            && !RewardInspection.Animating(selection.Owner, "_cardTween")
            && !RewardInspection.Animating(selection.Owner, "_buttonTween"));
    public PileType DisplayingPile => Kind == "combat_pile" && Field(Owner, "_pile") is CardPile pile ? pile.Type : PileType.None;
    public CardSelectorPrefs Prefs => Field(Owner, "_prefs") is CardSelectorPrefs prefs ? prefs : default;
    public CardModel[] Selected => Kind == "bundle" ? (Field(Owner, "_selectedBundle") as NCardBundle)?.Bundle.ToArray() ?? [] : (Field(Owner, "_selectedCards") as IEnumerable<CardModel>)?.ToArray() ?? [];

    internal static object? Field(object instance, string name) => AccessTools.Field(instance.GetType(), name)?.GetValue(instance);
    public static CardSelection? Current
    {
        get
        {
            if (NCapstoneContainer.Instance?.CurrentCapstoneScreen is NSimpleCardsViewScreen view && view.IsNodeReady())
                return new(view, "view_cards", view);
            var overlay = NRun.Instance?.GlobalUi.Overlays.Peek() as Control;
            string? kind = overlay switch
            {
                NChooseACardSelectionScreen => "choose_one", NCardRewardSelectionScreen => "reward",
                NSimpleCardSelectScreen => "grid", NCombatPileCardSelectScreen => "combat_pile",
                NDeckTransformSelectScreen => "deck_transform", NChooseABundleSelectionScreen => "bundle",
                NDeckEnchantSelectScreen => "deck_enchant", NDeckCardSelectScreen => "deck", NDeckUpgradeSelectScreen => "deck_upgrade",
                NCardGridSelectionScreen => "unsupported",
                _ => null
            };
            if (kind != null && overlay != null && GodotObject.IsInstanceValid(overlay) && overlay.IsNodeReady())
            {
                object? source = Field(overlay, "_completionSource");
                if (source?.GetType().GetProperty("Task")?.GetValue(source) is Task { IsCompleted: true }) return null;
                return new(overlay, kind, source ?? overlay);
            }
            var hand = NPlayerHand.Instance;
            if (hand?.IsInCardSelection != true || !hand.IsNodeReady()) return null;
            var completion = Field(hand, "_selectionCompletionSource");
            if (completion?.GetType().GetProperty("Task")?.GetValue(completion) is not Task { IsCompleted: false }) return null;
            return new(hand, hand.CurrentMode switch
                { NPlayerHand.Mode.SimpleSelect => "hand", NPlayerHand.Mode.UpgradeSelect => "hand_upgrade", _ => "unsupported" }, completion);
        }
    }

    // An overlay remains in the stack while its native eye hides the backstop.
    public static bool BattlefieldOverlay => NRun.Instance?.GlobalUi.Overlays.ScreenCount == 1
        && Current is { Peeking: true, Owner: not NPlayerHand };

    public bool Exposed
    {
        get
        {
            var game = NGame.Instance;
            var global = NRun.Instance?.GlobalUi;
            if (game == null || global == null || !VisibleUi.Shown(Owner)
                || global.CapstoneContainer.InUse && Kind != "view_cards" || VisibleUi.Shown(global.MapScreen)
                || NModalContainer.Instance?.OpenModal != null
                || VisibleUi.Shown(game.InspectCardScreen) || VisibleUi.Shown(game.InspectRelicScreen)
                || game.Transition.InTransition
                || (VisibleUi.Shown(game.Transition) && game.Transition.Material is ShaderMaterial material
                    && material.GetShaderParameter("threshold").AsSingle() > 0.000001f)
                || VisibleUi.Descendants<CanvasItem>(game.Transition).Any(VisibleUi.Shown)) return false;
            return Kind == "view_cards" ? ReferenceEquals(global.CapstoneContainer.CurrentCapstoneScreen, Owner)
                : Owner is NPlayerHand ? global.Overlays.ScreenCount == 0
                : ReferenceEquals(global.Overlays.Peek(), Owner);
        }
    }

    public string Status => !Exposed ? "covered" : !Supported ? "unsupported" : Peeking ? "battlefield" : "visible";
    public bool CanPeek => Supported && Exposed && Eye is { IsEnabled: true } && VisibleUi.OnScreen(Eye);

    public bool InPreview => Kind == "deck" && VisibleUi.Shown(Owner.GetNodeOrNull<Control>("%PreviewContainer"))
        || DeckUpgradeSelection.Preview(this) != null || DeckEnchantSelection.Preview(this) != null || TransformSelection.Preview(this) != null
        || Kind == "bundle" && VisibleUi.Shown(Owner.GetNodeOrNull<Control>("%BundlePreviewContainer"));

    public NUpgradePreview? UpgradePreview => Kind == "hand_upgrade" && Field(Owner, "_upgradePreview") is NUpgradePreview preview
        && VisibleUi.Shown(preview) ? preview : null;

    public NCard? UpgradeCard(string side) => UpgradePreview is { Card: not null } preview
        ? VisibleUi.Descendants<NCard>(preview.GetNode<Control>(side))
            .FirstOrDefault(card => CombatObservation.CardVisible(card)) : null;

    public NCardHolder[] Holders => Kind is "deck_upgrade" or "deck_enchant" or "deck_transform" && InPreview ? [] : Kind == "bundle" && InPreview
        ? VisibleUi.Descendants<NCardHolder>(Owner.GetNode<Control>("%BundlePreviewContainer")).ToArray()
        : InPreview
        ? VisibleUi.Descendants<NCardHolder>(Owner.GetNode<Control>("%PreviewContainer")).ToArray()
        : Kind == "hand_upgrade"
        ? VisibleUi.Descendants<NHandCardHolder>(((NPlayerHand)Owner).CardHolderContainer).Cast<NCardHolder>()
            .Concat(UpgradePreview is { Card: not null } preview
                ? VisibleUi.Descendants<NCardHolder>(preview.GetNode<Control>("%Before")) : [])
            .Where(holder => VisibleUi.Shown(holder) && holder.CardNode != null).ToArray()
        : Kind == "hand"
        ? VisibleUi.Descendants<NCardHolder>(Owner).Where(holder => VisibleUi.Shown(holder) && holder.CardNode != null).ToArray()
        : Grid != null ? Grid.CurrentlyDisplayedCardHolders.Cast<NCardHolder>().ToArray()
        : VisibleUi.Descendants<NGridCardHolder>(Owner).Cast<NCardHolder>().ToArray();

    public CardModel[] Cards => Grid != null ? CardView.Cards(Owner) : Holders
        .Where(holder => holder.CardModel != null).Select(holder => holder.CardModel!).Distinct().ToArray();

    public (int minimum, int maximum) Limits => Kind == "view_cards" ? (0, 0) : Kind is "choose_one" or "reward" or "bundle" ? (1, 1)
        : Kind == "combat_pile" ? (Math.Min(Prefs.MinSelect, Cards.Length), Math.Min(Prefs.MaxSelect, Cards.Length))
        : (Prefs.MinSelect, Prefs.MaxSelect);

    public string? Prompt => Kind is "choose_one" or "reward"
        ? EnglishCardText.Read(() => EnglishCardText.Plain(new MegaCrit.Sts2.Core.Localization.LocString("gameplay_ui", "CHOOSE_CARD_HEADER").GetFormattedText()))
        : Prefs.Prompt == null ? null : EnglishCardText.Read(() => EnglishCardText.Plain(Prefs.Prompt.GetFormattedText()));

    public IEnumerable<(string id, string? text, NButton button)> Options()
    {
        if (Status != "visible") yield break;
        if (Kind == "bundle")
        {
            if (!InPreview)
            {
                var bundles = Owner.GetNode<Control>("%BundleRow").GetChildren().OfType<NCardBundle>().ToArray();
                for (int i = 0; i < bundles.Length; i++)
                    if (VisibleUi.OnScreen(bundles[i].Hitbox)) yield return ("bundle:" + i, "Choose bundle " + (i + 1), (NButton)bundles[i].Hitbox);
            }
            else
                foreach (var (id, path) in new[] { ("cancel_preview", "%Cancel"), ("confirm", "%Confirm") })
                    if (Owner.GetNodeOrNull<NButton>(path) is { } button && VisibleUi.OnScreen(button)) yield return (id, id == "confirm" ? "Confirm" : "Back", button);
            yield break;
        }
        if (Kind == "reward")
        {
            var alternatives = Field(Owner, "_extraOptions") as IReadOnlyList<CardRewardAlternative>;
            var buttons = Owner.GetNode<Control>("UI/RewardAlternatives").GetChildren().OfType<NCardRewardAlternativeButton>().ToArray();
            for (int i = 0; alternatives != null && i < alternatives.Count && i < buttons.Length; i++)
            {
                if (!VisibleUi.OnScreen(buttons[i])) continue;
                string id = alternatives[i].OptionId.Equals("Skip", StringComparison.OrdinalIgnoreCase) ? "skip" : "alternative:" + i;
                yield return (id, EnglishCardText.Read(() => EnglishCardText.Plain(alternatives[i].Title.GetFormattedText())), buttons[i]);
            }
            yield break;
        }
        var paths = Kind switch
        {
            "view_cards" => new[] { ("confirm", "ConfirmButton") },
            "deck_transform" when InPreview => new[] { ("cancel_preview", "%PreviewContainer/Cancel"), ("confirm", "%PreviewContainer/Confirm") },
            "deck_transform" => new[] { ("cancel", "%Close"), ("confirm", "Confirm") },
            "choose_one" => new[] { ("skip", "SkipButton") },
            "hand" or "hand_upgrade" => new[] { ("confirm", "%SelectModeConfirmButton") },
            "deck" when InPreview => new[] { ("cancel_preview", "%PreviewCancel"), ("confirm", "%PreviewConfirm") },
            "deck" => new[] { ("cancel", "%Close"), ("confirm", "%Confirm") },
            "deck_enchant" when InPreview => new[] { ("cancel_preview", DeckEnchantSelection.Preview(this)!.GetPath() + "/Cancel"),
                ("confirm", DeckEnchantSelection.Preview(this)!.GetPath() + "/Confirm") },
            "deck_enchant" => new[] { ("cancel", "%Close"), ("confirm", "Confirm") },
            "deck_upgrade" when InPreview => new[] { ("cancel_preview", DeckUpgradeSelection.Preview(this)!.GetPath() + "/Cancel"),
                ("confirm", DeckUpgradeSelection.Preview(this)!.GetPath() + "/Confirm") },
            "deck_upgrade" => new[] { ("cancel", "%Close") },
            _ => new[] { ("confirm", "%Confirm") }
        };
        foreach (var (id, path) in paths)
            if (Owner.GetNodeOrNull<NButton>(path) is { } button && VisibleUi.OnScreen(button))
                yield return (id, id switch { "skip" => "Skip", "cancel" => "Cancel", "cancel_preview" => "Back", _ => "Confirm" }, button);
    }

    public bool CanSelect => Kind is not ("bundle" or "view_cards") && Status == "visible" && !InPreview
        && (Kind != "choose_one" || Godot.Time.GetTicksMsec() - (ulong)(Field(Owner, "_openedTicks") ?? 0UL) > 350)
        && (Grid == null || !Grid.IsAnimatingOut) && Holders.Any(Clickable);

    public static bool Clickable(NCardHolder holder) => VisibleUi.Shown(holder)
        && CombatObservation.CardVisible(holder.CardNode) && Field(holder, "_isClickable") is true;
}
