using Godot;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Vfx;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class EpilogueInspection
{
    internal sealed record Context(TheArchitect Model, NEventLayout Layout);
    public static Context? Current => RunUi.LocalEvent is TheArchitect model
        && NEventRoom.Instance?.Layout is { } layout && ReferenceEquals(model.Node, layout)
        && GodotObject.IsInstanceValid(layout) && layout.IsNodeReady() ? new(model, layout) : null;
    public static bool Exposed(Context context) => ReferenceEquals(Current?.Model, context.Model)
        && RunUi.NonCombatVisible() && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0
        && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen) && VisibleUi.Shown(context.Layout);
    public static NEventOptionButton? Button(Context context) => context.Layout.OptionButtons.FirstOrDefault(EventInspection.Shown);
    public static bool IsProceed(NEventOptionButton button) => button.Option.TextKey == "PROCEED";
    private static bool LineReady(Context context) => CardSelection.Field(context.Model, "_speechBubble") is not NSpeechBubbleVfx bubble
        || bubble.GetNodeOrNull<RichTextLabel>("%Text") is { VisibleRatio: >= 0.999f } label && VisibleUi.OnScreen(label)
            && VisibleUi.Shown(bubble);
    public static bool Ready(Context context) => TreasureInspection.Singleplayer && Exposed(context)
        && !EventTaskTracker.Pending && !NavigationTasks.ChangingAct && LineReady(context)
        && Button(context) is { } button && EventInspection.Clickable(button);
    public static object? Read()
    {
        if (Current is not { } context) return null;
        bool exposed = Exposed(context), ready = Ready(context);
        object? dialogue = null;
        if (exposed && LineReady(context) && CardSelection.Field(context.Model, "_speechBubble") is NSpeechBubbleVfx bubble
            && VisibleUi.Shown(bubble) && CardSelection.Field(context.Model, "_dialogue") is AncientDialogue conversation
            && CardSelection.Field(context.Model, "_currentLineIndex") is int index && index >= 0 && index < conversation.Lines.Count)
        {
            var line = conversation.Lines[index];
            dialogue = EnglishEventText.Read(() => (object)new {
                speaker = EnglishCardText.Plain(line.Speaker == AncientDialogueSpeaker.Ancient
                    ? context.Model.Title.GetFormattedText() : context.Model.Owner!.Character.Title.GetFormattedText()),
                text = EnglishCardText.Plain(line.LineText!.GetFormattedText()) });
        }
        var button = exposed ? Button(context) : null;
        object? ButtonText(bool proceed) => button != null && IsProceed(button) == proceed ? EnglishEventText.Read(() => (object)new {
            text = EnglishCardText.Plain(button.Option.Title.GetFormattedText()), enabled = ready }) : null;
        return new { status = !exposed ? "covered" : ready ? "visible" : "not_ready", dialogue,
            @continue = ButtonText(false), proceed = ButtonText(true) };
    }
}
