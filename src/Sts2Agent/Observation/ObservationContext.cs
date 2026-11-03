using System.Text.Json;
using System.Text.Json.Nodes;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class ObservationContext
{
    public static string Scene(RunResultInspection.Context? ending, EpilogueInspection.Context? epilogue) =>
        ending != null ? "run_result" : epilogue != null ? "epilogue" : CombatManager.Instance.IsInProgress ? "combat"
        : RewardInspection.Current != null ? "rewards"
        : RestSiteInspection.Current != null ? "rest_site"
        : TreasureInspection.Current != null ? "treasure"
        : AncientInspection.Current != null ? "ancient"
        : ShopInspection.Current != null ? "shop"
        : EventInspection.Current != null ? "event"
        : NGame.Instance?.MainMenu != null ? "main_menu" : "unrecognized";

    public static string Visibility(string scene, object? map,
        EpilogueInspection.Context? epilogue, RunResultInspection.Context? ending)
    {
        string status = scene == "combat" ? CombatObservation.Status() : "not_applicable";
        if (scene == "unrecognized" && RunUi.NonCombatVisible()) status = "visible";
        if (scene == "rewards") status = RewardInspection.Exposed(RewardInspection.Current!) ? "visible" : "covered";
        if (scene == "rest_site") status = RestSiteInspection.Exposed(RestSiteInspection.Current!) ? "visible" : "covered";
        if (scene == "treasure") status = TreasureInspection.Exposed(TreasureInspection.Current!) ? "visible" : "covered";
        if (scene == "shop") status = ShopInspection.Exposed(ShopInspection.Current!) ? "visible" : "covered";
        if (scene == "ancient") status = AncientInspection.Exposed(AncientInspection.Current!) ? "visible" : "covered";
        if (scene == "event") status = EventInspection.Exposed(EventInspection.Current!) ? "visible" : "covered";
        if (DivinationInspection.Current is { } board && DivinationInspection.Exposed(board)) status = "visible";
        if (EventConfirmation.Current is { } dialog && EventConfirmation.Exposed(dialog)) status = "visible";
        if (map != null) status = "visible";
        if (epilogue != null && map == null) status = EpilogueInspection.Exposed(epilogue) ? "visible" : "covered";
        if (ending != null) status = RunResultInspection.Exposed(ending) ? "visible" : "covered";
        return status;
    }

    public static Dictionary<string, string> Screen(string scene, string status, bool mapVisible)
    {
        var screen = CardView.Screen(status);
        if (scene == "run_result" || scene == "epilogue" && !mapVisible && CardView.Current == null)
            screen["view"] = scene;
        return screen;
    }

    public static string Inspection(JsonElement snapshot, object details) => ResponseBuilder.Inspection(snapshot, details);
}
