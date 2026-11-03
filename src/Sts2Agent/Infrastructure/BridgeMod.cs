using Godot;
using MegaCrit.Sts2.Core.Modding;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

[ModInitializer(nameof(Initialize))]
public static class BridgeMod
{
    private static readonly CancellationTokenSource Lifetime = new();
    private static FileMailbox? mailbox;
    private static GameAdapter? adapter;
    private static Task? transport;
    private static WorkItem? active;
    private static Task<string>? operation;

    public static void Initialize()
    {
        string? directory = System.Environment.GetEnvironmentVariable("STS2_AGENT_IPC_DIR");
        if (string.IsNullOrWhiteSpace(directory))
        {
            GD.Print("[Sts2Agent] Loaded; STS2_AGENT_IPC_DIR is unset, bridge disabled.");
            return;
        }
        VisibleUi.Initialize();
        EnglishCardText.Initialize();
        EnglishEventText.Initialize();
        EnglishRunResultText.Initialize();
        TurnCapture.Initialize();
        RelicObtainTracker.Initialize();
        EventTaskTracker.Initialize();
        NavigationTasks.Initialize();
        RunResultMotion.Initialize();
        CombatMotion.Initialize();
        EventConfirmation.Initialize();
        DivinationTasks.Initialize();
        CombatJournalScope.Initialize();
        ShopTransactions.Initialize();
        PermanentCardCapture.Initialize();
        OrbCapture.Initialize();
        CardAdditionJournal.Initialize();
        mailbox = new FileMailbox(Path.GetFullPath(directory));
        adapter = new GameAdapter(System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_MODE") == "1");
        transport = Task.Run(() => mailbox.Run(Lifetime.Token));
        Callable.From(Attach).CallDeferred();
        GD.Print("[Sts2Agent] Initialized; mailbox: " + directory);
        GD.Print("[Sts2Agent] User data: " + OS.GetUserDataDir());
    }

    private static void Attach()
    {
        SceneTree tree = NGame.Instance!.GetTree();
        if (DisplayServer.GetName() == "headless")
            tree.ProcessFrame += Pump;
        else
            RenderingServer.FramePostDraw += Pump;
        tree.Root.TreeExiting += () => Lifetime.Cancel();
        GD.Print("[Sts2Agent] Main-thread pump attached.");
    }

    private static void Pump()
    {
        if (transport?.IsFaulted == true)
        {
            GD.PushError("[Sts2Agent] Mailbox stopped: " + transport.Exception);
            NGame.Instance!.GetTree().ProcessFrame -= Pump;
            RenderingServer.FramePostDraw -= Pump;
            return;
        }
        if (active != null)
        {
            if (!operation!.IsCompleted)
                return;
            if (operation.IsFaulted) GD.PushError("[Sts2Agent] Operation failed: " + operation.Exception);
            string response = operation.IsCompletedSuccessfully ? operation.Result
                : FileMailbox.Error(active.Request.Id,
                    operation.Exception?.GetBaseException() is TimeoutException ? "timeout" : "game_error",
                    operation.Exception?.GetBaseException().Message ?? "Operation canceled.");
            active.Completion.TrySetResult(response);
            active = null;
            operation = null;
        }
        if (!mailbox!.Queue.TryDequeue(out WorkItem? next))
            return;
        if (next.Completion.Task.IsCompleted)
            return;
        if (DateTime.UtcNow >= next.Deadline)
        {
            next.Completion.TrySetResult(FileMailbox.Error(next.Request.Id, "expired_request", "Request expired before execution."));
            return;
        }
        active = next;
        operation = adapter!.Execute(next.Request);
    }
}
