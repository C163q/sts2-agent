import asyncio
import logging
from functools import partial

import anyio

from sts2_mcp.tool_registry import TOOLS, SPECS
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.output.player_output import player_result
from sts2_mcp.output.error_output import invalid_request, retained_rejection
from sts2_mcp.output.available_tools import GAME_ACTIONS, public_tools
from sts2_mcp.output.action_output import action_result
from sts2_mcp.output.divination_details import attach_divination_image
from sts2_mcp.screenshot_tool import ScreenshotError, ScreenshotStore


class GameTools:
    PURE_READS = {'get_state', 'inspect_targets', 'inspect_ui', 'inspect_hand', 'inspect_combatants'}
    READ_REJECTIONS = {'invalid_request', 'illegal_action', 'expired_request'}

    def __init__(self, client, controller=None, screenshot_directory=None):
        self.client = client
        self.controller = controller
        self.lock = asyncio.Lock()
        self.snapshot_id = None
        self.screenshots = ScreenshotStore(screenshot_directory) if screenshot_directory is not None else None

    async def invoke(self, name, arguments=None):
        spec = TOOLS[name]
        try:
            request = normalize_request(spec, arguments)
        except ValueError as error:
            if spec.requires_permission or name in {'set_selection_view', 'capture_screenshot'}:
                self.snapshot_id = None
            return invalid_request(str(error))
        if spec.requires_permission:
            payload = await self._action(request.operation, request.native_arguments)
        elif spec.category == 'view':
            payload = await self._change_view(request.operation, request.native_arguments)
        else:
            payload = await self._inspect(request.operation, request.native_arguments)
        return request.project(payload)

    async def _change_view(self, operation, arguments=None):
        async with self.lock:
            self.snapshot_id = None
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request(operation, arguments=arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            self.snapshot_id = snapshot_id
            return payload

    async def _inspect(self, operation, arguments=None):
        async with self.lock:
            previous = self.snapshot_id
            self.snapshot_id = None
            if operation == 'capture_screenshot' and self.screenshots is None:
                return invalid_request('Screenshots are disabled.')
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request(operation, arguments=arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            if (operation in self.PURE_READS and previous is not None
                    and payload.get('error', {}).get('code') in self.READ_REJECTIONS):
                self.snapshot_id = previous
                return retained_rejection(payload)
            if operation != 'capture_screenshot' or previous == snapshot_id:
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

    async def _action(self, operation, arguments=None):
        observed = self.snapshot_id
        async with self.lock:
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
            if 'error' in payload and following == snapshot_id:
                self.snapshot_id = snapshot_id
                return retained_rejection(payload)
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
                payload = decode_success(operation, state, arguments)
            else:
                if not isinstance(response["error"]["code"], str):
                    raise ValueError("Invalid game error.")
                for field in ('message', 'public_message'):
                    if field in response['error'] and not isinstance(response['error'][field], str):
                        raise ValueError('Invalid game error message.')
                if ('action_submitted' in response['error']
                        and type(response['error']['action_submitted']) is not bool):
                    raise ValueError('Invalid action submission status.')
                if (operation == 'play_card' and expected_state is not None
                        and response['error']['code'] in {'invalid_request', 'illegal_action'}
                        and response['error'].get('action_submitted') is False):
                    snapshot_id = expected_state
            if not response['ok']:
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


def _handler(spec):
    async def handle(self, arguments=None):
        return await self.invoke(spec.name, arguments)
    handle.__name__ = spec.name
    handle.__doc__ = spec.description
    handle.supports_output_presets = bool(spec.presets)
    return handle


for _spec in SPECS:
    setattr(GameTools, _spec.name, _handler(_spec))
