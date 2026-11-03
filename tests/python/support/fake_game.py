"""Deterministic file-mailbox game double; never starts the game."""
import json
import tempfile
import threading
from pathlib import Path


def map_payload():
    return {"scene": "combat", "screen": {"status": "visible", "view": "map"}, "act": 1,
            "current_node": "map:1:1:2", "visited_path": ["map:1:0:3", "map:1:1:2"],
            "can_travel": False, "selectable_nodes": [], "nodes": [
                {"id": "map:1:0:3", "row": 0, "column": 3, "type": "ancient", "name": "Neow", "next": ["map:1:1:2"]},
                {"id": "map:1:1:2", "row": 1, "column": 2, "type": "monster", "next": ["map:1:2:1"]},
                {"id": "map:1:2:1", "row": 2, "column": 1, "type": "unknown", "next": ["map:1:3:3"]},
                {"id": "map:1:2:5", "row": 2, "column": 5, "type": "rest_site", "next": ["map:1:3:3"]},
                {"id": "map:1:3:3", "row": 3, "column": 3, "type": "boss", "name": "Ceremonial Beast", "next": ["map:1:4:3"]},
                {"id": "map:1:4:3", "row": 4, "column": 3, "type": "boss", "name": "The Kin", "next": []},
            ]}


class FakeGame:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.config = self.directory / "mcp-config.json"
        self.config.write_text(json.dumps({"screenshots": {"enabled": False}}))
        self.requests = self.directory / "requests"
        self.responses = self.directory / "responses"
        self.requests.mkdir()
        self.responses.mkdir()
        self.operations = []
        self.turn = 1
        self.screenshot_payload = None
        self.drop_action_response = False
        self.malformed_observation = False
        self.malformed_hand = False
        self.malformed_hand_item = False
        self.hand_extra_state = False
        self.ui_payload = {"scene": "combat", "screen": {"status": "visible"}, "hover_tips": [{
            "title": "Energy", "description": "Your current <Energy> count.",
            "sources": ["player.energy", "player.max_energy"],
        }]}
        self.ui_error = False
        self.potion_payload = {
            "slot_tip": {"title": "Potion Slot", "description": "Use potions during combat."},
            "potion_slots": [
                {"name": "Block Potion", "description": "Gain 12 Block.", "hover_tips": [
                    {"title": "Block", "description": "Prevents damage."}]},
                None,
                {"name": "Block Potion", "description": "Gain 12 Block.", "hover_tips": [
                    {"title": "Block", "description": "Prevents damage."}]},
            ],
        }
        self.potion_error = False
        self.drop_potion_response = False
        self.combatant_payload = {
            "scene": "combat", "screen": {"status": "visible"}, "player": {"powers": [{"name": "Vulnerable", "amount": 2}]},
            "enemies": [{"id": 7, "name": "Twig Slime (M)",
                         "powers": [{"name": "Vulnerable", "amount": 2}],
                         "intents": [{"category": "attack", "value": "11"}]}],
            "hover_tips": [
                {"title": "Vulnerable", "description": "Receive 50% more damage for 2 turns.",
                 "sources": ["player.powers.0", "enemies.0.powers.0"]},
                {"title": "Aggressive", "description": "This enemy intends to Attack for 11 damage.",
                 "sources": ["enemies.0.intents.0"]},
            ],
        }
        self.relic_payload = {"relics": [
            {"name": "Anchor", "counter": None, "description": "Start with 10 Block.", "hover_tips": [
                {"title": "Block", "description": "Prevents damage."}]},
            {"name": "Pen Nib", "counter": 0, "description": "Every 10th Attack.", "hover_tips": []},
            {"name": "Anchor", "counter": None, "description": "Start with 10 Block.", "hover_tips": [
                {"title": "Block", "description": "Prevents damage."}]},
        ]}
        self.deck_open = False
        self.deck_upgrades = False
        self.deck_sort = {"by": "obtained", "descending": False}
        self.deck_payload = {"deck": [
            {"id": "deck:0", "name": "Defend+", "type": "Skill", "rarity": "basic", "visual_card_pool": "ironclad",
             "energy_cost": "1", "star_cost": None, "description": "Gain 8 Block.",
             "hover_tips": [{"title": "Block", "description": "Prevents damage."}]},
            {"id": "deck:1", "name": "Defend+", "type": "Skill", "rarity": "basic", "visual_card_pool": "ironclad",
             "energy_cost": "1", "star_cost": None, "description": "Gain 8 Block.",
             "hover_tips": [{"title": "Block", "description": "Prevents damage."}]},
        ]}
        self.deck_error = False
        self.close_error = False
        self.close_payload = {}
        self.drop_deck_response = False
        self.drop_close_response = False
        self.pile_payload = None
        self.pile_error = False
        self.drop_pile_response = False
        self.pile_open = None
        self.map_payload = map_payload()
        self.map_open = False
        self.map_error = False
        self.close_map_error = False
        self.drop_map_response = False
        self.drop_close_map_response = False
        self.ui_generation = 0
        self.relic_error = False
        self.drop_relic_response = False
        self.combatant_error = False
        self.drop_combatant_response = False
        self.observation_started = threading.Event()
        self.release_observation = threading.Event()
        self.release_observation.set()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stopped.set()
        self.release_observation.set()
        self.thread.join()
        self.temporary.cleanup()

    def token(self):
        return f"state-{self.turn}" + (f"-ui-{self.ui_generation}" if self.ui_generation else "")

    def run(self):
        while not self.stopped.wait(0.002):
            for path in self.requests.glob("*.json"):
                request = json.loads(path.read_text())
                self.operations.append(request)
                operation = request["operation"]
                if operation in {"get_state", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map"}:
                    self.observation_started.set()
                    self.release_observation.wait(timeout=5)
                response = {"id": request["id"], "ok": True}
                if operation == "end_turn":
                    if request.get("expected_state") != self.token():
                        response.update(ok=False, error={"code": "stale_state", "message": "/private/game/path"})
                    elif self.deck_open or self.pile_open or self.map_open:
                        response.update(ok=False, error={"code": "illegal_action", "message": "/private/game/path"})
                    else:
                        self.turn += 1
                if operation == "travel_to_node":
                    if request.get("expected_state") != self.token():
                        response.update(ok=False, error={"code": "stale_state"})
                    elif not self.map_open or request.get("arguments", {}).get("node_id") not in self.map_payload["selectable_nodes"]:
                        response.update(ok=False, error={"code": "illegal_action"})
                    else:
                        self.map_open = False
                        self.ui_generation += 1
                if response["ok"]:
                    response["state"] = {
                        "snapshot_id": self.token(), "schema_version": 3, "language": "en",
                        "session": "fixture", "combat_generation": 1, "scene": "combat",
                        "screen": {"status": "visible"}, "turn": self.turn,
                        "player": {"hp": 80, "max_hp": 80, "hand": []}, "enemies": [],
                        "top_bar": {}, "buttons": {}, "available_actions": ["end_turn", "start_test_combat"],
                        "overlay": {"seed": "private"},
                    }
                if operation in {"end_turn", "travel_to_node"} and response["ok"]:
                    response["state"]["transition"] = {"stop_reason": "player_ready", "complete": True, "events": []}
                if operation == "capture_screenshot" and self.screenshot_payload is not None:
                    response["state"] = {**self.screenshot_payload, "snapshot_id": self.token()}
                if operation == "get_state" and self.deck_open:
                    response["state"].update(screen={"status": "covered", "view": "deck"}, available_actions=[])
                if operation == "get_state" and self.pile_open:
                    response["state"].update(screen={"status": "covered", "view": self.pile_open + "_pile"}, available_actions=[])
                if operation == "get_state" and self.map_open and not (self.deck_open or self.pile_open):
                    response["state"].update(screen={"status": "covered", "view": "map"}, available_actions=[])
                if operation == "inspect_map":
                    if not self.map_open or self.deck_open or self.pile_open:
                        self.ui_generation += 1
                    self.map_open = True
                    self.deck_open = False
                    self.pile_open = None
                    response["state"] = {"snapshot_id": self.token(), **self.map_payload}
                    if self.map_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "close_map":
                    if self.close_map_error or not self.map_open or self.deck_open or self.pile_open:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                    else:
                        self.map_open = False
                        self.ui_generation += 1
                        response["state"].update({"snapshot_id": self.token(), **self.close_payload})
                if operation == "inspect_deck":
                    arguments = request.get("arguments", {})
                    if not self.deck_open:
                        self.ui_generation += 1
                        self.deck_upgrades = False
                        self.deck_sort = {"by": "obtained", "descending": False}
                    self.deck_open = True
                    self.pile_open = None
                    if "view_upgrades" in arguments or "sort_by" in arguments:
                        self.ui_generation += 1
                    self.deck_upgrades = arguments.get("view_upgrades", self.deck_upgrades)
                    if "sort_by" in arguments:
                        self.deck_sort = {"by": arguments["sort_by"], "descending": arguments.get("descending", False)}
                    response["state"] = {"snapshot_id": self.token(), "scene": "combat", "screen": {"status": "covered", "view": "deck"},
                        "view_upgrades": self.deck_upgrades,
                        "sort": self.deck_sort.copy(), **self.deck_payload}
                    if self.deck_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "inspect_pile":
                    previous_deck, previous_pile = self.deck_open, self.pile_open
                    arguments = request.get("arguments", {})
                    pile = arguments["pile"]
                    if self.pile_open != pile: self.ui_generation += 1
                    self.deck_open = False
                    self.pile_open = pile
                    response["state"] = {"snapshot_id": self.token(), "scene": "combat", "pile": pile,
                        "status": "opened",
                        "screen": {"status": "covered", "view": pile + "_pile"}, "message": "Native pile information.",
                        "cards": [{"id": "pile:0", "name": "Defend", "type": "Skill", "rarity": "basic",
                            "visual_card_pool": "ironclad", "energy_cost": "1", "star_cost": None,
                            "description": "Gain 5 Block.", "hover_tips": [{"title": "Block", "description": "Prevents damage."}]}],
                        **(self.pile_payload or {})}
                    if response["state"]["status"] != "opened":
                        self.deck_open, self.pile_open = previous_deck, previous_pile
                    if self.pile_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "close_card_view":
                    if self.close_error or not (self.deck_open or self.pile_open):
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                    else:
                        self.deck_open = False
                        self.pile_open = None
                        self.ui_generation += 1
                        response["state"].update({"snapshot_id": self.token(), **self.close_payload})
                        if self.map_open:
                            response["state"].update(screen={"status": "covered", "view": "map"}, available_actions=[])
                if operation == "get_state" and self.malformed_observation:
                    response.pop("state")
                if operation == "inspect_hand":
                    response["state"] = {
                        "snapshot_id": self.token(),
                        "hand": None if self.malformed_hand else [
                            {"id": card_id, "name": "Defend", "type": "Skill", "description": "Gain 5 Block.",
                             "hover_tips": [{"title": "Block", "description": "Until next turn, prevents damage."}]}
                            for card_id in (9, 2)],
                        "overlay": {"seed": "private"},
                    }
                    if self.malformed_hand_item:
                        response["state"]["hand"] = [None]
                    if self.hand_extra_state:
                        response["state"].update(scene="combat", enemies=[{"intents": [{"category": "attack", "value": "7"}]}],
                                                 available_actions=["end_turn"])
                if operation == "inspect_ui":
                    response["state"] = {"snapshot_id": self.token(), **self.ui_payload}
                    if self.ui_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "inspect_potions":
                    response["state"] = {"snapshot_id": self.token(), **self.potion_payload}
                    if self.potion_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "inspect_relics":
                    response["state"] = {"snapshot_id": self.token(), **self.relic_payload}
                    if self.relic_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if operation == "inspect_combatants":
                    response["state"] = {"snapshot_id": self.token(), **self.combatant_payload}
                    if self.combatant_error:
                        response = {"id": request["id"], "ok": False,
                                    "error": {"code": "illegal_action", "message": "/private/game/path"}}
                if not ((operation == "end_turn" and self.drop_action_response)
                        or (operation == "inspect_potions" and self.drop_potion_response)
                        or (operation == "inspect_combatants" and self.drop_combatant_response)
                        or (operation == "inspect_relics" and self.drop_relic_response)
                        or (operation == "inspect_deck" and self.drop_deck_response)
                        or (operation == "inspect_pile" and self.drop_pile_response)
                        or (operation == "inspect_map" and self.drop_map_response)
                        or (operation == "close_map" and self.drop_close_map_response)
                        or (operation == "close_card_view" and self.drop_close_response)):
                    target = self.responses / path.name
                    temporary = target.with_suffix(".tmp")
                    temporary.write_text(json.dumps(response))
                    temporary.replace(target)
                path.unlink()


