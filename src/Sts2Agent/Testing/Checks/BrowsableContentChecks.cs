using System.Text.Json;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.RunHistoryScreen;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;
using MegaCrit.Sts2.Core.Saves.Runs;

namespace Sts2Agent;

internal static class BrowsableContentChecks
{
    public static object Containers() => VisibleUi.Descendants<Control>(NGame.Instance!)
        .Where(node => node is NScrollableContainer or ScrollContainer)
        .Select(node => new { path = node.GetPath().ToString(), type = node.GetType().FullName,
            shown = VisibleUi.Shown(node), on_screen = VisibleUi.OnScreen(node) }).ToArray();

    public static void PrepareResult(RunResultInspection results)
    {
        if (results.Current is not { Root: NGameOverScreen over, Phase: "outcome" }
            || PrivateFields.Read(over, "_serializableRun") is not SerializableRun run
            || PrivateFields.Read(over, "_history") is not RunHistory original)
            throw new InvalidOperationException("Expected an isolated result before its summary.");
        // Debug runs skip normal history and character progress creation.
        foreach (var player in run.Players)
            SaveManager.Instance.Progress.GetOrCreateCharacterStats(player.CharacterId
                ?? throw new InvalidOperationException("The fixture player has no character."));
        var previous = SaveManager.Instance.GetAllRunHistoryNames().ToHashSet();
        RunHistoryUtilities.CreateRunHistoryEntry(run, original.Win, false, RunManager.Instance.NetService.Platform);
        var names = SaveManager.Instance.GetAllRunHistoryNames().ToArray();
        string name = names.FirstOrDefault(name => !previous.Contains(name)) ?? names.Last();
        var loaded = SaveManager.Instance.LoadRunHistory(name);
        if (!loaded.Success) throw new InvalidOperationException("The isolated native history could not be loaded.");
        AccessTools.Field(typeof(NGameOverScreen), "_history").SetValue(over, loaded.SaveData);
    }

    public static async Task PrepareHistory(RunResultInspection results, Func<Task> frame)
    {
        if (results.Current is not { Root: NGameOverScreen over, Phase: "summary" })
            throw new InvalidOperationException("Expected a completed isolated run summary.");
        var history = PrivateFields.Read(over, "_history")
            ?? throw new InvalidOperationException("The native result has no history.");
        // This version disables View Run. Prepare its native page only in the isolated fixture.
        var page = ResourceLoader.Load<PackedScene>(NRunHistory.AssetPaths[0]).Instantiate<NRunHistory>();
        over.AddChild(page);
        AccessTools.Method(typeof(NRunHistory), "DisplayRun").Invoke(page, [history]);
        page.Show();
        page.GetNode<NBackButton>("BackButton").Enable();
        // The starting deck groups into three rows and fits. Add a long native UI fixture.
        var content = page.GetNode<Control>("ScreenContents/Content");
        content.CustomMinimumSize = new Vector2(content.CustomMinimumSize.X, 3000);
        var spacer = new Control { Name = "BrowsableFixture", CustomMinimumSize = new Vector2(500, 1500), Size = new Vector2(500, 1500) };
        spacer.AddChild(new Label { Text = "Scrollable content fixture", Position = new Vector2(60, 1300), Size = new Vector2(400, 40) });
        content.AddChild(spacer);
        for (int i = 0; i < 90; i++)
        {
            await frame();
            if (i >= 10 && results.Current is { Phase: "history" } current && results.Ready(current)) return;
        }
        throw new InvalidOperationException("The native history fixture did not become readable.");
    }

    public static object Run(RewardInspection rewards, RunResultInspection results, Func<string> observe)
    {
        var checks = new List<(string name, bool passed)>();
        void Check(string name, bool passed) => checks.Add((name, passed));
        string before = observe();
        if (RewardInspection.Current is { } screen && RewardInspection.Exposed(screen))
        {
            JsonElement Read(bool full = false) => JsonSerializer.SerializeToElement(rewards.Read(full));
            var buttons = RewardInspection.Buttons(screen);
            Check("fixture has a reward outside the viewport", buttons.Any(b => !VisibleUi.OnScreen(b.GetNode<Control>("%Label"))));
            Check("basic observation includes every browsable reward", Read().GetProperty("items").GetArrayLength() == 6);
            var label = buttons[0].GetNode<Control>("%Label");
            bool visible = label.Visible;
            try
            {
                label.Hide();
                Check("hidden reward labels stay excluded", Read().GetProperty("items").GetArrayLength() == 5
                    && Read(true).GetProperty("items").GetArrayLength() == 5);
            }
            finally { label.Visible = visible; }
            Color color = screen.Modulate;
            try
            {
                screen.Modulate = new Color(color, 0);
                Check("transparent rewards stay covered", Read().GetProperty("status").GetString() == "covered"
                    && Read().GetProperty("items").ValueKind == JsonValueKind.Null);
            }
            finally { screen.Modulate = color; }
        }
        else if (results.Current is { Root: NRunHistory history })
        {
            JsonElement Read() => JsonSerializer.SerializeToElement(results.Read(full: true));
            var scroll = history.GetNode<NScrollableContainer>("ScreenContents");
            var content = scroll.GetNode<Control>("Content");
            var labels = VisibleUi.Descendants<CanvasItem>(content).Where(VisibleUi.Shown)
                .Where(node => node is Label { Text.Length: > 0 } or RichTextLabel { Text.Length: > 0, VisibleRatio: >= .999f }).ToArray();
            var offscreen = labels.Where(node => !VisibleUi.OnScreen(node)).ToArray();
            string Expected(CanvasItem node) => EnglishEventText.Label(node, node is Label label ? label.Text : ((RichTextLabel)node).Text);
            var expected = offscreen.Select(Expected).Where(text => !string.IsNullOrWhiteSpace(text)).ToArray();
            var texts = Read().GetProperty("texts").EnumerateArray().Select(text => text.GetString()).ToHashSet();
            Check("native history has offscreen readable labels", expected.Length > 0);
            Check("all scrollable history labels are present", expected.All(texts.Contains));
            if (offscreen.Length == 0) throw new InvalidOperationException("The history fixture has no offscreen label.");
            var baseline = Read().GetRawText();
            Vector2 position = content.Position;
            try
            {
                content.Position += new Vector2(0, -1000);
                Check("scroll position does not truncate history", Read().GetRawText() == baseline);
            }
            finally { content.Position = position; }
            var labelNode = history.GetNode<Control>("ScreenContents/Content/BrowsableFixture")
                .GetChildren().OfType<Label>().Single();
            string labelText = Expected(labelNode);
            bool visible = labelNode.Visible;
            try
            {
                labelNode.Hide();
                Check("hidden scrollable labels stay excluded", RunResultInspection.Text(labelNode) == null);
            }
            finally { labelNode.Visible = visible; }
            Color color = labelNode.Modulate;
            try
            {
                labelNode.Modulate = new Color(color, 0);
                Check("transparent scrollable labels stay excluded", RunResultInspection.Text(labelNode) == null);
            }
            finally { labelNode.Modulate = color; }
            Vector2 labelPosition = labelNode.Position;
            try
            {
                labelNode.Position += new Vector2(10000, 0);
                Check("vertical scrolling does not expose horizontal outliers", RunResultInspection.Text(labelNode) == null);
            }
            finally { labelNode.Position = labelPosition; }
            var parent = labelNode.GetParent<Control>();
            bool clipping = parent.ClipContents;
            Vector2 parentSize = parent.Size;
            Vector2 minimumSize = parent.CustomMinimumSize;
            try
            {
                parent.CustomMinimumSize = Vector2.Zero;
                parent.ClipContents = true;
                parent.Size = new Vector2(parentSize.X, 10);
                Check("scrolling does not bypass inner clipping", parent.Size.Y == 10 && RunResultInspection.Text(labelNode) == null);
            }
            finally { parent.ClipContents = clipping; parent.CustomMinimumSize = minimumSize; parent.Size = parentSize; }
            var external = new Label { Text = "Hidden outside the scroll content", Position = new Vector2(0, 10000) };
            try
            {
                history.AddChild(external);
                Check("non-scrollable offscreen text stays excluded", RunResultInspection.Text(external) == null);
            }
            finally { external.Free(); }
            Check("visible fixture labels are identified", labelText.Length > 0);
        }
        else throw new InvalidOperationException("Expected exposed rewards or the native history fixture.");
        Check("checks restore the complete observation", before == observe());
        return new { checks = checks.Select(check => new { check.name, check.passed }).ToArray(), passed = checks.All(check => check.passed) };
    }
}
