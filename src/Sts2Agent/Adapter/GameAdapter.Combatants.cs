using System.Text.Json;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private string CombatantsRequest(Request request, JsonElement snapshot)
    {
        var level = CombatantInspection.Level.Full;
        if (request.Arguments is { } arguments)
        {
            if (arguments.EnumerateObject().Any(property => property.Name != "level")
                || arguments.TryGetProperty("level", out var supplied)
                    && (supplied.ValueKind != JsonValueKind.String || supplied.GetString() is not ("summary" or "full")))
                return FileMailbox.Error(request.Id, "invalid_request", "Unsupported combatant detail preset.", publicMessage: true);
            if (arguments.TryGetProperty("level", out supplied) && supplied.GetString() == "summary")
                level = CombatantInspection.Level.Summary;
        }
        var player = LocalPlayer;
        string? reason = player == null ? "Combatant inspection requires a local player and an exposed battlefield."
            : CombatantInspection.UnavailableReason(level);
        if (reason != null) return FileMailbox.Error(request.Id, "illegal_action", reason, publicMessage: true);
        string? checks = System.Environment.GetEnvironmentVariable("STS2_AGENT_TEST_COMBATANT_CHECKS");
        if (testMode && checks != null && level == CombatantInspection.Level.Full)
            CombatantInspectionChecks.Run(checks, player!);
        var inspection = CombatantInspection.Read(player, observation.CardId, level);
        return InspectionSuccess(request.Id, snapshot, new
        {
            inspection.player, inspection.enemies, inspection.allies, inspection.hover_tips,
            inspection.unavailable_hover_sources
        });
    }
}
