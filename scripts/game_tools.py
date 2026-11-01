import asyncio
import logging
from functools import partial

import anyio

from run_ending_details import option_arguments
from deck_details import deck_arguments
from inspection_details import inspection_details
from map_details import map_arguments, map_preset, travel_arguments
from pile_details import pile_arguments
from player_output import player_result
from selection_details import selection_arguments
from card_play_details import card_play_arguments
from potion_action_details import potion_arguments
from reward_details import reward_arguments
from rest_site_details import rest_option_arguments
from treasure_details import loot_arguments
from shop_details import shop_arguments
from ancient_details import ancient_arguments
from event_details import event_arguments
from confirmation_details import confirmation_arguments
from divination_details import attach_divination_image, divination_arguments
from screenshot_tool import ScreenshotError, ScreenshotStore, screenshot_arguments
from observation_presets import observation_preset, preset_arguments
from available_tools import GAME_ACTIONS, public_tools
from action_output import action_result


class GameTools:
    def __init__(self, client, controller=None, screenshot_directory=None):
        self.client = client
        self.controller = controller
        self.lock = asyncio.Lock()
        self.snapshot_id = None
        self.screenshots = ScreenshotStore(screenshot_directory) if screenshot_directory is not None else None

    async def get_observation(self, arguments=None):
        async with self.lock:
            self.snapshot_id = None
            try:
                preset = preset_arguments(arguments)
            except ValueError:
                return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request("get_state")
            await anyio.lowlevel.checkpoint_if_cancelled()
            self.snapshot_id = snapshot_id
            return observation_preset(payload, preset)

    async def inspect_run_result(self):
        return await self._inspect('inspect_run_result')

    async def run_result_option(self, arguments=None):
        return await self._action('run_result_option', arguments)

    async def inspect_hand(self):
        return await self._inspect("inspect_hand")

    async def inspect_rewards(self):
        return await self._inspect('inspect_rewards')

    async def inspect_event(self):
        return await self._inspect('inspect_event')

    async def choose_event_option(self, arguments=None):
        return await self._action('choose_event_option', arguments)

    async def respond_to_confirmation(self, arguments=None):
        return await self._action('respond_to_confirmation', arguments)

    async def set_divination_tool(self, arguments=None):
        return await self._action('set_divination_tool', arguments)

    async def divine(self, arguments=None):
        return await self._action('divine', arguments)

    async def inspect_ancient(self):
        return await self._inspect('inspect_ancient')

    async def choose_ancient_option(self, arguments=None):
        return await self._action('choose_ancient_option', arguments)

    async def advance_dialogue(self, arguments=None):
        return await self._action('advance_dialogue', arguments)

    async def inspect_shop(self):
        return await self._inspect('inspect_shop')

    async def open_shop(self, arguments=None):
        return await self._action('open_shop', arguments)

    async def close_shop(self, arguments=None):
        return await self._action('close_shop', arguments)

    async def buy_item(self, arguments=None):
        return await self._action('buy_item', arguments)

    async def inspect_treasure(self):
        return await self._inspect('inspect_treasure')

    async def loot_treasure(self, arguments=None):
        return await self._action('loot_treasure', arguments)

    async def inspect_rest_site(self):
        return await self._inspect('inspect_rest_site')

    async def choose_rest_option(self, arguments=None):
        return await self._action('choose_rest_option', arguments)

    async def claim_reward(self, arguments=None):
        return await self._action('claim_reward', arguments)

    async def proceed(self, arguments=None):
        return await self._action('proceed', arguments)

    async def capture_screenshot(self, arguments=None):
        return await self._inspect("capture_screenshot", arguments)

    async def inspect_selection(self):
        return await self._inspect("inspect_selection")

    async def inspect_targets(self, arguments=None):
        return await self._inspect("inspect_targets", arguments)

    async def play_card(self, arguments=None):
        return await self._action("play_card", arguments)

    async def use_potion(self, arguments=None):
        return await self._action("use_potion", arguments)

    async def discard_potion(self, arguments=None):
        return await self._action("discard_potion", arguments)

    async def set_selection_view(self, arguments=None):
        return await self._change_view("set_selection_view", arguments, validate_selection=True)

    async def select_card(self, arguments=None):
        return await self._selection_action("select_card", arguments)

    async def selection_option(self, arguments=None):
        return await self._selection_action("selection_option", arguments)

    async def _selection_action(self, operation, arguments):
        return await self._action(operation, arguments, validate_selection=True)

    async def inspect_ui(self):
        return await self._inspect("inspect_ui")

    async def inspect_potions(self):
        return await self._inspect("inspect_potions")

    async def inspect_combatants(self):
        return await self._inspect("inspect_combatants")

    async def inspect_relics(self):
        return await self._inspect("inspect_relics")

    async def inspect_deck(self, arguments=None):
        try:
            arguments = deck_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view("inspect_deck", arguments)

    async def close_card_view(self):
        return await self._change_view("close_card_view")

    async def travel_to_node(self, arguments=None):
        return await self._action('travel_to_node', arguments)

    async def inspect_map(self, arguments=None):
        try:
            options = map_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return map_preset(await self._change_view('inspect_map'), **options)

    async def close_map(self, arguments=None):
        if arguments is not None and (not isinstance(arguments, dict) or arguments):
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view('close_map')

    async def inspect_pile(self, arguments=None):
        try:
            arguments = pile_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view("inspect_pile", arguments)

    async def _change_view(self, operation, arguments=None, validate_selection=False):
        async with self.lock:
            self.snapshot_id = None
            if validate_selection:
                try:
                    arguments = selection_arguments(operation, arguments)
                except ValueError:
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request(operation, arguments=arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            self.snapshot_id = snapshot_id
            return payload

    async def _inspect(self, operation, arguments=None):
        async with self.lock:
            previous, self.snapshot_id = self.snapshot_id, None
            if operation == "capture_screenshot":
                try:
                    if self.screenshots is None:
                        raise ValueError("Screenshots are disabled.")
                    arguments = screenshot_arguments(arguments)
                except ValueError:
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if operation == "inspect_targets":
                try:
                    arguments = card_play_arguments(operation, arguments)
                except ValueError:
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request(operation, arguments=arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            if operation != "capture_screenshot" or previous == snapshot_id:
                self.snapshot_id = snapshot_id
            return payload

    def _acquire_controller(self):
        if self.controller is None:
            return None
        try:
            self.controller.acquire()
        except BlockingIOError:
            return {"error": {
                "code": "controller_busy",
                "message": "Another MCP connection controls this game. Disconnect it before reading or acting here.",
                "recovery": "disconnect_other_client",
            }}
        except OSError as error:
            logging.getLogger(__name__).warning("Controller lock failed: %s", error)
            return player_result({"ok": False, "error": {"code": "transport_error"}})
        return None

    async def end_turn(self, arguments=None):
        return await self._action("end_turn", arguments)

    async def _action(self, operation, arguments=None, validate_selection=False):
        observed = self.snapshot_id
        async with self.lock:
            if operation == 'travel_to_node':
                try:
                    arguments = travel_arguments(arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == 'respond_to_confirmation':
                try:
                    arguments = confirmation_arguments(arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation in {'set_divination_tool', 'divine'}:
                try:
                    arguments = divination_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == 'run_result_option':
                try:
                    arguments = option_arguments(arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == 'choose_event_option':
                try:
                    arguments = event_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation in {'choose_ancient_option', 'advance_dialogue'}:
                try:
                    arguments = ancient_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation in {'open_shop', 'close_shop', 'buy_item'}:
                try:
                    arguments = shop_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == 'loot_treasure':
                try:
                    arguments = loot_arguments(arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == 'choose_rest_option':
                try:
                    arguments = rest_option_arguments(arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation in {'claim_reward', 'proceed'}:
                try:
                    arguments = reward_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
            if operation == "end_turn":
                if arguments is not None and (not isinstance(arguments, dict) or arguments):
                    self.snapshot_id = None
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
                arguments = None
            if operation in {"use_potion", "discard_potion"}:
                try:
                    arguments = potion_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if operation == "play_card":
                try:
                    arguments = card_play_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if validate_selection:
                try:
                    arguments = selection_arguments(operation, arguments)
                except ValueError:
                    self.snapshot_id = None
                    return player_result({"ok": False, "error": {"code": "invalid_request"}})
            if self.snapshot_id is None or self.snapshot_id != observed:
                self.snapshot_id = None
                return {"error": {
                    "code": "observation_required",
                    "message": "Read current state with get_observation or a relevant inspection before acting.",
                    "recovery": "get_observation",
                }}
            snapshot_id, self.snapshot_id = self.snapshot_id, None
            payload, following = await self._request(operation, snapshot_id, arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            transition = payload.get("transition", {})
            reason = transition.get("stop_reason")
            selection = payload.get("selection")
            ready = reason in {"player_ready", "action_completed"} and not selection \
                and payload.get("screen", {}).get("status") == "visible"
            choosing = reason == "choice_required" and selection is not None \
                and selection.get("status") == "visible" and selection.get("type") != "unsupported"
            if following is not None and transition.get("complete") is True \
                    and any(action in GAME_ACTIONS for action in payload.get("available_actions", [])) and (ready or choosing):
                self.snapshot_id = following
            return action_result(payload)

    async def _request(self, operation, expected_state=None, arguments=None):
        try:
            request_arguments = None if operation == "capture_screenshot" else arguments
            response = await anyio.to_thread.run_sync(partial(self.client.call, operation, expected_state, arguments=request_arguments))
            if not isinstance(response, dict) or type(response.get("ok")) is not bool:
                raise ValueError("Invalid game response.")
            snapshot_id = None
            if response["ok"]:
                state = response["state"]
                snapshot_id = state["snapshot_id"]
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    raise ValueError("Missing observation token.")
                if operation == "capture_screenshot":
                    payload = await anyio.to_thread.run_sync(self.screenshots.save, state, arguments)
                    return payload, snapshot_id
                response = {"ok": True, "state": inspection_details(operation, state, arguments)}
            else:
                if not isinstance(response["error"]["code"], str):
                    raise ValueError("Invalid game error.")
            payload = player_result(response, operation=operation)
            if response['ok']:
                payload = attach_divination_image(payload, state)
            if response['ok'] and 'available_actions' in payload:
                payload['available_actions'] = public_tools(payload['available_actions'])
        except ScreenshotError as error:
            payload = player_result({"ok": False, "error": {"code": error.code}})
            snapshot_id = None
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            code = "timeout" if isinstance(error, TimeoutError) else "transport_error"
            logging.getLogger(__name__).warning("Game request failed: %s", error)
            payload = player_result({"ok": False, "error": {"code": code}})
            snapshot_id = None
        if "error" in payload and payload["error"]["recovery"] == "get_state":
            payload["error"]["recovery"] = "get_observation"
        return payload, snapshot_id
