using System.Runtime.CompilerServices;
using System.Text.Json;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private readonly TestScenarioSettings testSettings = new();
    private readonly ConditionalWeakTable<object, TestRunIdentity> testRuns = new();
    private sealed record TestRunIdentity(string Id);
    private bool testResetFailed;

    private object TestSession()
    {
        var run = RunManager.Instance.DebugOnlyGetState();
        return new { process_id = Environment.ProcessId, session = capture.Session,
            run_id = run == null ? null : testRuns.GetValue(run, _ => new(Guid.NewGuid().ToString("N"))).Id };
    }

    private async Task<string> TestRunRequest(Request request)
    {
        if (!testMode || Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE") != "1")
            return FileMailbox.Error(request.Id, "illegal_action", "Reusable fixtures require an isolated test suite.");
        if (request.Operation == "get_test_session")
        {
            if (request.Arguments is { } supplied && supplied.EnumerateObject().Any())
                return FileMailbox.Error(request.Id, "invalid_request", "No arguments are accepted.");
            return Success(request, JsonSerializer.Serialize(TestSession()));
        }
        using var observed = JsonDocument.Parse(Observe());
        if (request.ExpectedState != observed.RootElement.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Observe before changing test lifecycle.");
        if (testResetFailed)
            return FileMailbox.Error(request.Id, "illegal_action", "Cleanup failed; restart the test process.");
        if (request.Operation == "configure_test_run")
        {
            if (RunManager.Instance.IsInProgress || NGame.Instance?.MainMenu == null)
                return FileMailbox.Error(request.Id, "illegal_action", "Configure only at the main menu without a run.");
            try
            {
                if (request.Arguments is not { } config || config.EnumerateObject().Count() != 1
                    || !config.TryGetProperty("scenarios", out var scenarios))
                    throw new ArgumentException("Expected only scenarios.");
                testSettings.Configure(scenarios);
            }
            catch (ArgumentException error) { return FileMailbox.Error(request.Id, "invalid_request", error.Message); }
            return Success(request, JsonSerializer.Serialize(TestSession()));
        }
        if (request.Arguments is { } arguments && arguments.EnumerateObject().Any())
            return FileMailbox.Error(request.Id, "invalid_request", "No arguments are accepted.");
        testResetFailed = true;
        // Native cleanup cancels player choices and disposes the run's action synchronizers.
        var pending = new[] { SelectionFixture.Pending, RewardFixture.Pending, ShopFixture.Pending, TreasureFixture.Pending, CombatHandoffFixture.Pending }
            .Where(task => task != null).Cast<Task>().ToArray();
        await NGame.Instance!.ReturnToMainMenu();
        try { await Task.WhenAll(pending).WaitAsync(TimeSpan.FromSeconds(5)); }
        catch (OperationCanceledException) { }
        if (RunManager.Instance.IsInProgress || NRun.Instance != null || CardSelection.Current != null)
            throw new InvalidOperationException("Native run cleanup is incomplete.");
        MediaFailureFixture.Enabled = false;
        RelicDisplayFixture.Set("normal");
        RelicHoverFixture.SetEnabled(true);
        PotionDisplayFixture.Set("normal");
        SelectionFixture.Pending = null;
        RewardFixture.Reset();
        ShopFixture.Reset();
        TreasureFixture.Reset();
        CombatHandoffFixture.Reset();
        foreach (string owner in new[] { "sts2_agent.test_shop_inventory", "sts2_agent.test_treasure_extra", "sts2_agent.test_treasure_map_pending" })
            new Harmony(owner).UnpatchAll(owner);
        UiChanged();
        await SettledObservation();
        testResetFailed = false;
        return Success(request, JsonSerializer.Serialize(TestSession()));
    }
}
