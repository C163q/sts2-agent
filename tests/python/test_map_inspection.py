import unittest

from sts2_mcp.roundtrip_client import player_result


class MapProjectionTests(unittest.TestCase):
    def test_keeps_graph_and_actual_choices_without_control_metadata(self):
        state = {
            "snapshot_id": "private-token", "scene": "combat", "screen": {"status": "visible", "view": "map"},
            "act": 1, "current_node": "map:1:1:2", "visited_path": ["map:1:0:3", "map:1:1:2"],
            "can_travel": True, "selectable_nodes": ["map:1:2:0", "map:1:2:2"],
            "nodes": [{"id": "map:1:1:2", "row": 1, "column": 2, "type": "monster", "next": ["map:1:2:2"]}],
            "session": "private-session", "seed": "hidden",
        }
        result = player_result({"ok": True, "state": state})
        self.assertEqual(result, {key: value for key, value in state.items()
                                 if key not in {"snapshot_id", "session", "seed"}})
        self.assertNotIn("notes", result)


if __name__ == "__main__":
    unittest.main()
