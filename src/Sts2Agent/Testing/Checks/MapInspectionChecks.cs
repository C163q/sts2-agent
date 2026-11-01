using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Assets;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Map;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Unlocks;

namespace Sts2Agent;

internal static class MapInspectionChecks
{
    public static async Task<object> Run(GameAdapter adapter, string path)
    {
        var game = NGame.Instance!;
        var run = RunManager.Instance.DebugOnlyGetState()!;
        var map = NMapScreen.Instance!;
        var player = LocalContext.GetMe(run)!;
        List<object> results = [], calls = [], samples = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        async Task Wait(Func<bool> ready)
        {
            var deadline = DateTime.UtcNow.AddSeconds(8);
            while (!ready())
            {
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Map test did not settle.");
                await game.ToSignal(game.GetTree(), SceneTree.SignalName.ProcessFrame);
            }
        }
        async Task<JsonElement> Call(string operation, object? args = null)
        {
            using var response = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), operation,
                null, args == null ? null : JsonSerializer.SerializeToElement(args))));
            var result = response.RootElement.Clone();
            calls.Add(new { operation, arguments = args, response = result });
            return result;
        }
        async Task<JsonElement> Inspect(string? name = null)
        {
            var response = await Call("inspect_map");
            if (!response.GetProperty("ok").GetBoolean()) throw new InvalidOperationException("Map test inspection failed: " + response);
            var state = response.GetProperty("state");
            if (name != null) samples.Add(new { name, state });
            return state;
        }
        async Task Close()
        {
            await Wait(() => MapView.CanClose(map));
            var response = await Call("close_map");
            if (!response.GetProperty("ok").GetBoolean()) throw new InvalidOperationException("Map test close failed: " + response);
            await Wait(() => !VisibleUi.Shown(map));
        }
        string[] Choices(JsonElement state) => state.GetProperty("selectable_nodes").EnumerateArray().Select(x => x.GetString()!).ToArray();
        string Id(MapCoord coord) => $"map:{run.CurrentActIndex + 1}:{coord.row}:{coord.col}";
        string RngState() => JsonSerializer.Serialize(run.Rng.ToSerializable());
        void Capture(string name)
        {
            if (DisplayServer.GetName() != "headless")
                TestCapture.Save(Path.Combine(Path.GetDirectoryName(path)!, "map-" + name + ".png"));
        }
        try
        {
            string initialRng = RngState();
            var before = adapter.Observe();
            foreach (string operation in new[] { "inspect_map", "close_map" })
            {
                var invalid = await Call(operation, new { act = 2 });
                Check("arguments_rejected_before_ui", !invalid.GetProperty("ok").GetBoolean()
                    && invalid.GetProperty("error").GetProperty("code").GetString() == "invalid_request"
                    && adapter.Observe() == before && !map.IsOpen);
            }
            var state = await Inspect("map-combat");
            Check("combat_has_no_selectable_nodes", !state.GetProperty("can_travel").GetBoolean() && Choices(state).Length == 0);
            var points = VisibleUi.Descendants<NMapPoint>(map).Where(VisibleUi.Shown).ToArray();
            Check("entire_map_includes_nodes_outside_viewport", state.GetProperty("nodes").GetArrayLength() == points.Length
                && points.Any(p => !VisibleUi.OnScreen(p)));
            Check("tutorial_start_matches_monster_icon", state.GetProperty("nodes")[0].GetProperty("type").GetString() == "monster");
            Check("future_unknown_nodes_remain_unknown", state.GetProperty("nodes").EnumerateArray()
                .Where(n => n.GetProperty("type").GetString() == "unknown").Any()
                && state.GetProperty("nodes").EnumerateArray().All(n => !n.TryGetProperty("revealed_type", out _)));
            string token = state.GetProperty("snapshot_id").GetString()!;
            string first = state.GetRawText();
            Check("repeated_read_preserves_page_and_token", (await Inspect()).GetRawText() == first && map.IsOpen);
            Check("one_named_boss_is_terminal", state.GetProperty("nodes").EnumerateArray()
                .Where(n => n.GetProperty("type").GetString() == "boss").Single() is var boss
                && boss.GetProperty("next").GetArrayLength() == 0 && boss.GetProperty("name").GetString()!.Length > 0);
            Capture("combat");
            await Call("inspect_deck");
            var deck = CardView.Current;
            var rejected = await Call("close_map");
            Check("close_map_does_not_close_covering_deck", !rejected.GetProperty("ok").GetBoolean()
                && ReferenceEquals(CardView.Current, deck) && map.IsOpen);
            await Inspect();
            Check("inspect_map_uses_native_button_to_expose_map", CardView.Current == null && map.IsOpen);
            rejected = await Call("close_card_view");
            Check("close_card_view_does_not_close_map", !rejected.GetProperty("ok").GetBoolean() && map.IsOpen);
            await Close();
            await Call("inspect_deck");
            await Inspect();
            Check("map_opens_from_deck_and_replaces_it", CardView.Current == null && map.IsOpen);
            await Close();

            foreach (string mode in new[] { "closed", "covered" })
            {
                bool interrupted = false;
                void Interrupt()
                {
                    if (interrupted || !map.IsOpen) return;
                    interrupted = true;
                    if (mode == "closed") map.Close();
                    else NRun.Instance!.GlobalUi.TopBar.Deck.ForceClick();
                }
                RenderingServer.FramePreDraw += Interrupt;
                try
                {
                    var response = await Call("inspect_map");
                    Check("human_" + mode + "_is_not_undone", interrupted && !response.GetProperty("ok").GetBoolean()
                        && response.GetProperty("error").GetProperty("code").GetString() == "illegal_action"
                        && (mode == "closed" ? !map.IsOpen : CardView.Current != null && map.IsOpen));
                }
                finally { RenderingServer.FramePreDraw -= Interrupt; }
                if (CardView.Current is { } covering)
                {
                    await Wait(() => CardView.CanClose(covering));
                    await Call("close_card_view");
                }
                if (map.IsOpen) await Close();
                await Wait(() => !VisibleUi.Shown(map));
            }
            Check("browsing_keeps_rng", RngState() == initialRng);

            foreach (string mode in new[] { "reopened", "covered" })
            {
                await Inspect();
                bool interrupted = false;
                void InterruptClosing()
                {
                    if (interrupted || map.IsOpen || VisibleUi.Shown(map)) return;
                    interrupted = true;
                    if (mode == "reopened") NRun.Instance!.GlobalUi.TopBar.Map.ForceClick();
                    else NRun.Instance!.GlobalUi.TopBar.Deck.ForceClick();
                }
                RenderingServer.FramePreDraw += InterruptClosing;
                try
                {
                    var response = await Call("close_map");
                    Check("human_" + mode + "_during_close_settle_is_preserved", interrupted
                        && !response.GetProperty("ok").GetBoolean()
                        && response.GetProperty("error").GetProperty("code").GetString() == "illegal_action"
                        && (mode == "reopened" ? map.IsOpen : CardView.Current != null));
                }
                finally { RenderingServer.FramePreDraw -= InterruptClosing; }
                if (CardView.Current is { } covering)
                {
                    await Wait(() => CardView.CanClose(covering));
                    await Call("close_card_view");
                }
                if (map.IsOpen) await Close();
                await Wait(() => !VisibleUi.Shown(map));
            }

            var start = run.Map.StartingMapPoint;
            var originalType = start.PointType;
            start.PointType = MapPointType.Unknown;
            map.SetMap(run.Map, run.Rng.Seed, clearDrawings: false);
            state = await Inspect("map-revealed-question");
            var revealed = state.GetProperty("nodes")[0];
            Check("visited_question_uses_native_revealed_icon", revealed.GetProperty("type").GetString() == "unknown"
                && revealed.GetProperty("revealed_type").GetString() == "monster"
                && state.GetProperty("current_node").GetString() == Id(start.coord)
                && state.GetProperty("visited_path")[0].GetString() == Id(start.coord));
            await Close();
            start.PointType = originalType;
            map.SetMap(run.Map, run.Rng.Seed, clearDrawings: false);

            // Finish only this disposable fixture and use the native reward/proceed flow.
            var source = run.Map.GetAllMapPoints().First(p => p.coord.row > 0 && p.Children.Count > 0
                && run.Map.GetPointsInRow(p.coord.row + 1).Any(q => !p.Children.Contains(q)));
            run.AddVisitedMapCoord(source.coord);
            await CreatureCmd.Kill(CombatManager.Instance.DebugOnlyGetState()!.Enemies.ToArray(), force: true);
            await CombatManager.Instance.CheckWinCondition();
            await Wait(() => VisibleUi.Descendants<NRewardsScreen>(NRun.Instance!.GlobalUi).Any());
            var rewards = VisibleUi.Descendants<NRewardsScreen>(NRun.Instance!.GlobalUi).Single();
            var proceed = rewards.GetNode<NButton>("ProceedButton");
            await Wait(() => proceed.IsEnabled && VisibleUi.OnScreen(proceed));
            proceed.ForceClick();
            await Wait(() => MapView.Ready(map));
            Check("native_map_can_cover_retained_reward_screen", NRun.Instance!.GlobalUi.Overlays.ScreenCount == 1
                && NRun.Instance.GlobalUi.Overlays.Peek() is NRewardsScreen);
            string selectionRng = RngState();
            var connected = source.Children.OrderBy(p => p.coord.col).Select(p => Id(p.coord)).ToArray();
            state = await Inspect("map-connected");
            Check("selection_phase_matches_native_connected_nodes", state.GetProperty("can_travel").GetBoolean()
                && Choices(state).SequenceEqual(connected));
            var boots = await RelicCmd.Obtain<WingedBoots>(player);
            await Close();
            state = await Inspect("map-winged-boots");
            var nextRow = run.Map.GetPointsInRow(source.coord.row + 1).OrderBy(p => p.coord.col).Select(p => Id(p.coord)).ToArray();
            Check("winged_boots_exposes_unconnected_next_row", Choices(state).SequenceEqual(nextRow)
                && Choices(state).Except(connected).Any());
            Check("winged_boots_does_not_rewrite_graph", state.GetProperty("nodes").EnumerateArray()
                .Single(n => n.GetProperty("id").GetString() == Id(source.coord)).GetProperty("next").EnumerateArray()
                .Select(n => n.GetString()).SequenceEqual(connected));
            await Inspect();
            Check("view_does_not_consume_boots_or_rng", boots.TimesUsed == 0 && RngState() == selectionRng);
            Capture("winged-boots");
            boots.TimesUsed = 3;
            await Close();
            state = await Inspect("map-boots-exhausted");
            Check("exhausted_boots_restore_connected_choices", Choices(state).SequenceEqual(connected));
            map.Drawings.SetDrawingModeLocal(DrawingMode.Drawing);
            state = await Inspect();
            Check("drawing_mode_suppresses_choices", !state.GetProperty("can_travel").GetBoolean() && Choices(state).Length == 0);
            map.Drawings.SetDrawingModeLocal(DrawingMode.None);
            await RelicCmd.Remove(boots);

            await Close();
            await RunManager.Instance.EnterRoomDebug(RoomType.RestSite, showTransition: false);
            await Wait(() => MapView.Clear() && NRun.Instance!.GlobalUi.TopBar.Deck.IsEnabled);
            NRun.Instance!.GlobalUi.TopBar.Deck.ForceClick();
            await Wait(() => NCapstoneContainer.Instance?.CurrentCapstoneScreen is NDeckViewScreen);
            await Inspect("map-from-noncombat-deck");
            Check("map_replaces_noncombat_deck", NCapstoneContainer.Instance?.CurrentCapstoneScreen == null && map.IsOpen);
            await Close();
            // The first-run room set intentionally omits its Ancient.
            run.Act.GenerateRooms(new Rng(4321, "map_rooms_fixture"), UnlockState.all);
            var second = run.Act.AllBossEncounters.First(e => e.Id != run.Act.BossEncounter.Id);
            run.Act.SetSecondBossEncounter(second);
            await PreloadManager.LoadActAssets(run.Act);
            var doubleMap = new StandardActMap(new Rng(1234, "map_inspection_fixture"), run.Act, false, false, hasSecondBoss: true);
            run.Map = doubleMap;
            run.ClearVisitedMapCoordsDebug();
            map.SetMap(doubleMap, run.Rng.Seed, clearDrawings: true);
            state = await Inspect("map-double-boss");
            var bosses = state.GetProperty("nodes").EnumerateArray().Where(n => n.GetProperty("type").GetString() == "boss").ToArray();
            Check("two_named_bosses_are_sequential", bosses.Length == 2
                && bosses[0].GetProperty("next").EnumerateArray().Select(x => x.GetString()).SequenceEqual(new[] { bosses[1].GetProperty("id").GetString() })
                && bosses[1].GetProperty("next").GetArrayLength() == 0
                && bosses.All(b => b.GetProperty("name").GetString()!.Length > 0));
            Check("ordinary_act_has_named_ancient_start", state.GetProperty("nodes")[0].GetProperty("type").GetString() == "ancient"
                && state.GetProperty("nodes")[0].GetProperty("name").GetString()!.Length > 0);
            Capture("double-boss");
            run.Acts[1].GenerateRooms(new Rng(5432, "map_act_2_rooms_fixture"), UnlockState.all);
            await RunManager.Instance.SetActInternal(1);
            state = await Inspect("map-act-2");
            Check("act_change_uses_current_map_and_new_ids", state.GetProperty("act").GetInt32() == 2
                && state.GetProperty("nodes").EnumerateArray().All(n => n.GetProperty("id").GetString()!.StartsWith("map:2:", StringComparison.Ordinal)));
            var cannotClose = await Call("close_map");
            Check("mandatory_start_map_has_no_forced_close", !cannotClose.GetProperty("ok").GetBoolean() && map.IsOpen);
        }
        finally
        {
            System.IO.File.WriteAllText(path, JsonSerializer.Serialize(new { results, calls, samples }, new JsonSerializerOptions { WriteIndented = true }));
        }
        return new { results };
    }
}
