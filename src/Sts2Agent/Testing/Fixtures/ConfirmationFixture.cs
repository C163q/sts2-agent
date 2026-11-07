using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class ConfirmationFixture
{
    public static void OpenUnowned() => NModalContainer.Instance!.Add(NAbandonRunConfirmPopup.Create(null)!);

    public static void Cancel() => EventConfirmation.Contents((NAbandonRunConfirmPopup)NModalContainer.Instance!.OpenModal!).NoButton.ForceClick();

    public static void SetButtons(bool confirm, bool cancel)
    {
        var popup = EventConfirmation.Current ?? throw new InvalidOperationException("A supported Trial confirmation is required.");
        var contents = EventConfirmation.Contents(popup);
        contents.YesButton.SetEnabled(confirm);
        contents.NoButton.SetEnabled(cancel);
    }

    public static void Reopen()
    {
        Cancel();
        EventInspection.Current!.Layout.OptionButtons.Single(b => b.Option.TextKey.EndsWith("DOUBLE_DOWN")).ForceClick();
    }

    public static object Read() => new { abandoned = RunManager.Instance.IsAbandoned,
        ended = EventTaskTracker.RunLost, pending = EventConfirmation.AbandonPending,
        hp = RunManager.Instance.DebugOnlyGetState()?.Players.Single().Creature.CurrentHp };
}
