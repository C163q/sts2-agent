using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Map;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class MapInspection
{
    private static readonly FieldInfo Paths = typeof(NMapScreen).GetField("_paths", BindingFlags.Instance | BindingFlags.NonPublic)!;
    private static readonly EnglishText English = new();

    public static string Id(RunState run, MapCoord coord) => $"map:{run.CurrentActIndex + 1}:{coord.row}:{coord.col}";

    public static NMapPoint[] Choices(NMapScreen screen) => MapView.Ready(screen)
        && screen.IsTravelEnabled && !screen.IsDebugTravelEnabled && !NavigationTasks.ChangingAct
        && screen.Drawings.GetLocalDrawingMode() == DrawingMode.None
        ? VisibleUi.Descendants<NMapPoint>(screen).Where(node => VisibleUi.Shown(node)
            && node.State == MapPointState.Travelable && node.IsEnabled)
            .OrderBy(node => node.Point.coord.row).ThenBy(node => node.Point.coord.col).ToArray() : [];

    public static object? Summary(RunState? run)
    {
        var screen = NMapScreen.Instance;
        if (run == null || screen == null || !MapView.Current(screen)) return null;
        var choices = Choices(screen);
        return new { status = "visible", act = run.CurrentActIndex + 1,
            current_node = run.CurrentMapCoord is { } coord ? Id(run, coord) : null,
            can_travel = choices.Length > 0, selectable_nodes = choices.Select(n => Id(run, n.Point.coord)).ToArray() };
    }

    public static Dictionary<string, object?> Read(NMapScreen screen, RunState run, string snapshotId)
    {
        var nodes = VisibleUi.Descendants<NMapPoint>(screen).Where(VisibleUi.Shown)
            .OrderBy(node => node.Point.coord.row).ThenBy(node => node.Point.coord.col).ToArray();
        var coordinates = nodes.Select(node => node.Point.coord).ToHashSet();
        var paths = (Dictionary<(MapCoord, MapCoord), IReadOnlyList<TextureRect>>)Paths.GetValue(screen)!;
        string Id(MapCoord coord) => $"map:{run.CurrentActIndex + 1}:{coord.row}:{coord.col}";
        var choices = Choices(screen).Select(node => Id(node.Point.coord)).ToArray();
        return new()
        {
            ["snapshot_id"] = snapshotId,
            ["scene"] = "map",
            ["screen"] = new { status = "visible", view = "map" },
            ["act"] = run.CurrentActIndex + 1,
            ["current_node"] = run.CurrentMapCoord is { } current && coordinates.Contains(current) ? Id(current) : null,
            ["visited_path"] = run.VisitedMapCoords.Where(coordinates.Contains).Select(Id).ToArray(),
            ["can_travel"] = choices.Length > 0,
            ["selectable_nodes"] = choices,
            ["nodes"] = nodes.Select(node =>
            {
                var result = new Dictionary<string, object?>
                {
                    ["id"] = Id(node.Point.coord), ["row"] = node.Point.coord.row, ["column"] = node.Point.coord.col,
                    ["type"] = Type(node),
                    ["next"] = nodes.Where(child => paths.TryGetValue((node.Point.coord, child.Point.coord), out var segments)
                        && segments.Any(VisibleUi.Shown)).Select(child => Id(child.Point.coord)).ToArray()
                };
                string? name = node switch
                {
                    NAncientMapPoint => English.Name(run.Act.Ancient.Title),
                    NBossMapPoint => English.Name((ReferenceEquals(node.Point, run.Map.SecondBossMapPoint)
                        ? run.Act.SecondBossEncounter : run.Act.BossEncounter)!.Title),
                    _ => null
                };
                if (name != null) result["name"] = name;
                var icon = node.GetNodeOrNull<TextureRect>("%Icon");
                if (result["type"] is "unknown" && VisibleUi.Shown(icon) && IconType(icon) is { } revealed && revealed != "unknown")
                    result["revealed_type"] = revealed;
                if (VisibleUi.Shown(node.GetNodeOrNull<TextureRect>("%QuestIcon"))) result["marked"] = true;
                return result;
            }).ToArray()
        };
    }

    private static string Type(NMapPoint node) => node switch
    {
        NAncientMapPoint => "ancient",
        NBossMapPoint => "boss",
        _ => node.Point.PointType == MapPointType.Unknown ? "unknown"
            : IconType(node.GetNodeOrNull<TextureRect>("%Icon")) ?? "unrecognized"
    };

    private static string? IconType(TextureRect? icon)
    {
        if (!VisibleUi.Shown(icon) || icon!.Texture == null) return null;
        return Path.GetFileNameWithoutExtension(icon.Texture.ResourcePath) switch
        {
            "map_monster" or "map_unknown_monster" => "monster",
            "map_elite" or "map_unknown_elite" => "elite",
            "map_shop" or "map_unknown_shop" => "shop",
            "map_chest" or "map_unknown_chest" => "treasure",
            "map_rest" => "rest_site",
            "map_unknown" => "unknown",
            _ => null
        };
    }
}
