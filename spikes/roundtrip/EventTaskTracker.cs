using System.Reflection;
using HarmonyLib;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class EventTaskTracker
{
    private static readonly List<(IRunState? run, Task task)> Tasks = [];
    private static IRunState? lostRun;
    public static bool RunLost => lostRun != null && ReferenceEquals(lostRun, RunManager.Instance.DebugOnlyGetState());

    public static bool Pending
    {
        get
        {
            Tasks.RemoveAll(t => t.task.IsCompleted || !ReferenceEquals(t.run, RunManager.Instance.DebugOnlyGetState()));
            return Tasks.Count > 0;
        }
    }

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.event_tasks");
        var methods = new HashSet<MethodInfo> {
            AccessTools.Method(typeof(EventOption), nameof(EventOption.Chosen)),
            AccessTools.Method(typeof(EventModel), nameof(EventModel.BeginEvent)),
            AccessTools.Method(typeof(EventRoom), nameof(EventRoom.EnterInternal)) };
        // ResumeEvents launches virtual Resume tasks without adding them to pending option tasks.
        foreach (var type in typeof(EventModel).Assembly.GetTypes().Where(t => typeof(EventModel).IsAssignableFrom(t)))
            foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)
                .Where(m => !m.IsAbstract && m.Name is nameof(EventModel.Resume) or nameof(EventModel.AfterEventStarted)))
                methods.Add(method);
        foreach (var method in methods)
            harmony.Patch(method, postfix: new HarmonyMethod(typeof(EventTaskTracker), nameof(Started)));
        harmony.Patch(AccessTools.Method(typeof(RunManager), nameof(RunManager.OnEnded)),
            postfix: new HarmonyMethod(typeof(EventTaskTracker), nameof(Ended)));
    }

    private static void Started(Task __result)
    {
        if (!__result.IsCompleted) Tasks.Add((RunManager.Instance.DebugOnlyGetState(), __result));
    }

    private static void Ended(bool __0)
    {
        if (!__0) lostRun = RunManager.Instance.DebugOnlyGetState();
    }
}
