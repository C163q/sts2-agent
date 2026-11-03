using Godot;
using MegaCrit.Sts2.Core.Events.Custom.CrystalSphereEvent;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class DivinationInspection
{
    public static NCrystalSphereScreen? Current => EventInspection.Current?.Model is CrystalSphere
        && NRun.Instance?.GlobalUi.Overlays is { } overlays
        ? VisibleUi.Descendants<NCrystalSphereScreen>(overlays).SingleOrDefault(s => GodotObject.IsInstanceValid(s)
            && !s.IsQueuedForDeletion() && s.IsNodeReady()) : null;

    public static bool OnlyOverlay => Current is { } screen && NRun.Instance?.GlobalUi.Overlays is { ScreenCount: 1 } overlays
        && ReferenceEquals(overlays.Peek(), screen);

    public static bool Exposed(NCrystalSphereScreen screen) => ReferenceEquals(Current, screen) && OnlyOverlay
        && RunUi.NonCombatVisible() && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)
        && VisibleUi.Shown(screen) && VisibleUi.Shown(screen.GetNode<Control>("%Items"))
        && !RewardInspection.Animating(screen, "_fadeTween");

    public static NCrystalSphereCell[] Cells(NCrystalSphereScreen screen) => screen.GetNode<Control>("%Cells")
        .GetChildren().OfType<NCrystalSphereCell>().ToArray();

    public static NDivinationButton Tool(NCrystalSphereScreen screen, string tool) => screen.GetNode<NDivinationButton>(
        tool == "big" ? "%BigDivinationButton" : "%SmallDivinationButton");

    public static NProceedButton? Proceed(NCrystalSphereScreen screen) => screen.GetNode<NProceedButton>("%ProceedButton") is { } button
        && VisibleUi.OnScreen(button) && VisibleUi.Text(button, "%Label") is { Length: > 0 } ? button : null;

    private static CrystalSphereMinigame Model(NCrystalSphereScreen screen) => (CrystalSphereMinigame)PrivateFields.Read(screen, "_entity")!;
    private static bool Finished(NCrystalSphereScreen screen) => !Tool(screen, "big").Visible && Proceed(screen)?.IsEnabled == true;

    private static bool Revealing(NCrystalSphereScreen screen)
    {
        var mask = screen.GetNode<NCrystalSphereMask>("%ScryMask");
        float now = (float)PrivateFields.Read(mask, "_time")!;
        var values = (Godot.Collections.Array<Vector3>)PrivateFields.Read(mask, "_values")!;
        // The target version's scry_reveal shader interpolates gridFadeParams over 0.5 seconds.
        return values.Any(value => value.Z > 0 && now - value.Z < 0.5f)
            || VisibleUi.Descendants<NCrystalSphereItem>(screen).Any(item => RewardInspection.Animating(item, "_tween"));
    }

    public static bool Ready(NCrystalSphereScreen screen) => Exposed(screen) && RunContext.Singleplayer
        && !DivinationTasks.Pending(screen) && !Revealing(screen) && !RunUi.CardPreviewsPending()
        && !RunUi.ResourceMotionPending() && !RelicObtainTracker.Pending && RunManager.Instance.ActionQueueSet.IsEmpty
        && (Finished(screen) ? !EventTaskTracker.Pending : Model(screen).DivinationCount > 0);

    public static bool Playing(NCrystalSphereScreen screen) => Ready(screen) && !Finished(screen);

    public static bool Clickable(NCrystalSphereCell cell) => cell.IsEnabled && cell.Entity.IsHidden
        && cell.MouseFilter == Control.MouseFilterEnum.Stop && cell.FocusMode != Control.FocusModeEnum.None;

    public static Rect2I Bounds(NCrystalSphereScreen screen)
    {
        var cells = Cells(screen);
        if (cells.Length != 121) throw new InvalidOperationException("Unexpected divination grid.");
        var stretch = screen.GetViewport().GetStretchTransform();
        Rect2 bounds = new((stretch * cells[0].GetGlobalTransformWithCanvas()).Origin, Vector2.Zero);
        foreach (var cell in cells)
        {
            var transform = stretch * cell.GetGlobalTransformWithCanvas();
            bounds = bounds.Expand(transform.Origin).Expand(transform * cell.Size);
        }
        return new Rect2I((int)Mathf.Floor(bounds.Position.X), (int)Mathf.Floor(bounds.Position.Y),
            (int)Mathf.Ceil(bounds.End.X) - (int)Mathf.Floor(bounds.Position.X),
            (int)Mathf.Ceil(bounds.End.Y) - (int)Mathf.Floor(bounds.Position.Y));
    }

    public static object? Read()
    {
        if (Current is not { } screen) return null;
        if (!Exposed(screen)) return new { status = "covered", phase = (string?)null, remaining = (int?)null,
            tool = (string?)null, tools = (object?)null, instructions = (object?)null, dialogue = (string?)null,
            grid = (object?)null, proceed = (object?)null };
        var cells = Cells(screen);
        var bounds = Bounds(screen);
        bool ready = Ready(screen), finished = Finished(screen);
        var model = Model(screen);
        return EnglishCardText.Read(() =>
        {
            string Text(string key) => EnglishCardText.Plain(new LocString("events", "CRYSTAL_SPHERE." + key).GetFormattedText());
            bool toolsShown = VisibleUi.OnScreen(Tool(screen, "big")) && VisibleUi.OnScreen(Tool(screen, "small"));
            var dialogue = screen.GetNode<NCrystalSphereDialogue>("%Dialogue");
            var label = dialogue.GetNode<RichTextLabel>("%Text");
            return (object)new {
                status = "visible", phase = finished && ready ? "finished" : ready ? "playing" : "settling",
                remaining = VisibleUi.OnScreen(screen.GetNode<Control>("%DivinationsLeft")) ? (int?)model.DivinationCount : null,
                tool = toolsShown ? model.CrystalSphereTool == CrystalSphereMinigame.CrystalSphereToolType.Big ? "big" : "small" : null,
                tools = toolsShown ? new[] { "big", "small" }.Select(id => new { id,
                    text = Text("button.DIVINATION_LABEL_" + id.ToUpperInvariant()), enabled = ready && Tool(screen, id).IsEnabled }).ToArray() : null,
                instructions = VisibleUi.OnScreen(screen.GetNode<Control>("%Instructions")) ? new {
                    title = Text("minigame.instructions.title"), description = Text("minigame.instructions.description") } : null,
                dialogue = VisibleUi.OnScreen(label) && label.VisibleRatio >= 0.999f && DivinationTasks.Dialogue(dialogue) is { } spoken
                    ? EnglishCardText.Plain(spoken.GetFormattedText()) : null,
                grid = new { columns = 11, rows = 11, covered_rows = Enumerable.Range(0, 11).Select(y => new string(
                    Enumerable.Range(0, 11).Select(x => cells.Single(c => c.Entity.X == x && c.Entity.Y == y).Entity.IsHidden ? '#' : '.').ToArray())).ToArray(),
                    image = new { width = bounds.Size.X, height = bounds.Size.Y } },
                proceed = Proceed(screen) is { } button ? new { text = EnglishCardText.Plain(NProceedButton.ProceedLoc.GetFormattedText()), enabled = ready && button.IsEnabled } : null
            };
        });
    }
}
