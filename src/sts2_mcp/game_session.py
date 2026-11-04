"""Serialize game requests and maintain permission independently of public projection."""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from functools import partial

import anyio

from sts2_mcp.output.action_output import action_result
from sts2_mcp.output.available_tools import GAME_ACTIONS, public_tools
from sts2_mcp.output.divination_details import attach_divination_image
from sts2_mcp.output.error_output import error_result, retained_rejection
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.screenshot_tool import ScreenshotError, ScreenshotStore


@dataclass(frozen=True)
class PermissionTicket:
    token: str | None
    generation: int


class PermissionState:
    def __init__(self):
        self.token = None
        self.generation = 0

    def ticket(self):
        return PermissionTicket(self.token, self.generation)

    def replace(self, token):
        self.token = token
        self.generation += 1


class ExecutionEvidence(Enum):
    UNKNOWN = 'unknown'
    SUBMITTED = 'submitted'
    INTERACTION_STARTED = 'interaction_started'
    UNSUBMITTED_UNCHANGED = 'unsubmitted_ui_unchanged'
    SUCCESS = 'success'


@dataclass(frozen=True)
class GameResponse:
    payload: dict
    token: str | None = None
    evidence: ExecutionEvidence = ExecutionEvidence.UNKNOWN


def can_continue(payload):
    transition = payload.get('transition', {})
    reason = transition.get('stop_reason')
    selection = payload.get('selection')
    ready = reason in {'player_ready', 'action_completed'} and not selection \
        and payload.get('screen', {}).get('status') == 'visible'
    choosing = reason == 'choice_required' and selection is not None \
        and selection.get('status') == 'visible' and selection.get('type') != 'unsupported'
    return transition.get('complete') is True and (ready or choosing) \
        and any(action in GAME_ACTIONS for action in payload.get('available_actions', []))


class GameSession:
    READ_REJECTIONS = frozenset({'invalid_request', 'illegal_action', 'expired_request'})

    def __init__(self, client, controller=None, screenshot_directory=None):
        self.client = client
        self.controller = controller
        self.lock = asyncio.Lock()
        self.permission = PermissionState()
        self.screenshots = ScreenshotStore(screenshot_directory) if screenshot_directory is not None else None

    async def execute(self, request):
        observed = self.permission.ticket()
        try:
            async with self.lock:
                previous = self.permission.ticket()
                self.permission.replace(None)
                generation = self.permission.generation
                if request.requires_permission and (observed.token is None or observed != previous):
                    return {'error': {
                        'code': 'observation_required',
                        'message': 'Read current state with get_observation or a relevant inspection before acting.',
                        'recovery': 'get_observation'}}
                if error := self._acquire_controller():
                    return error
                response = await self._send(request, observed.token if request.requires_permission else None)
                await anyio.lowlevel.checkpoint_if_cancelled()
                payload = response.payload
                if 'error' in payload:
                    retain = previous.token is not None and (
                        request.effect == 'read' and payload['error']['code'] in self.READ_REJECTIONS
                        and response.evidence not in {ExecutionEvidence.SUBMITTED, ExecutionEvidence.INTERACTION_STARTED}
                        or (request.requires_permission or request.spec.unchanged_view_rejections)
                        and response.evidence is ExecutionEvidence.UNSUBMITTED_UNCHANGED)
                    if retain and self.permission.generation == generation:
                        self.permission.replace(previous.token)
                        payload = retained_rejection(payload)
                    return payload
                # Projection must succeed before its snapshot can authorize another request.
                result = request.project(action_result(payload) if request.returns_transition else payload)
                if self.permission.generation == generation:
                    if not request.refreshes_permission:
                        if previous.token == response.token:
                            self.permission.replace(previous.token)
                    elif not request.requires_permission or can_continue(payload):
                        self.permission.replace(response.token)
                return result
        except asyncio.CancelledError:
            self.permission.replace(None)
            raise
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            self.permission.replace(None)
            logging.getLogger(__name__).warning('Game session failed: %s', error)
            return self._public_error({'code': 'transport_error'}, request)

    def _acquire_controller(self):
        if self.controller is None:
            return None
        try:
            self.controller.acquire()
        except BlockingIOError:
            return {'error': {
                'code': 'controller_busy',
                'message': 'Another MCP connection controls this game. Disconnect it before reading or acting here.',
                'recovery': 'disconnect_other_client'}}
        except OSError as error:
            logging.getLogger(__name__).warning('Controller lock failed: %s', error)
            return {'error': {'code': 'transport_error', 'message': 'The controller lock could not be acquired.',
                              'recovery': 'check_connection', 'outcome': 'unknown'}}
        return None

    @staticmethod
    def _public_error(error, request):
        payload = error_result(error, state_changing=request.effect in {'view', 'action'})
        if payload['error']['recovery'] == 'get_state':
            payload['error']['recovery'] = 'get_observation'
        return payload

    async def _send(self, request, expected_state):
        operation, arguments = request.operation, request.native_arguments
        try:
            native = None if request.effect == 'file' else arguments
            response = await anyio.to_thread.run_sync(
                partial(self.client.call, operation, expected_state, arguments=native,
                        response_options={"include_divination_image": request.media_required}))
            if not isinstance(response, dict) or type(response.get('ok')) is not bool:
                raise ValueError('Invalid game response.')
            facts = response.get('execution')
            if facts is not None:
                fields = ('ui_interaction_started', 'action_submission_observed', 'state_captured')
                if not isinstance(facts, dict) or any(type(facts.get(field)) is not bool for field in fields):
                    raise ValueError('Invalid execution evidence.')
            if not response['ok']:
                error = response['error']
                if not isinstance(error['code'], str):
                    raise ValueError('Invalid game error.')
                for field in ('message', 'public_message'):
                    if field in error and not isinstance(error[field], str):
                        raise ValueError('Invalid game error message.')
                if 'action_submitted' in error and type(error['action_submitted']) is not bool:
                    raise ValueError('Invalid action submission status.')
                if 'ui_unchanged' in error and type(error['ui_unchanged']) is not bool:
                    raise ValueError('Invalid unchanged UI guarantee.')
                evidence = ExecutionEvidence.UNKNOWN
                if facts and facts['ui_interaction_started']: evidence = ExecutionEvidence.INTERACTION_STARTED
                if error.get('action_submitted') is True or facts and facts['action_submission_observed']:
                    evidence = ExecutionEvidence.SUBMITTED
                if error.get('action_submitted') is False and facts and (
                        facts['ui_interaction_started'] or facts['action_submission_observed']):
                    raise ValueError('Contradictory rejection evidence.')
                if error.get('ui_unchanged') is True:
                    if error.get('action_submitted') is True or facts and (
                            facts['ui_interaction_started'] or facts['action_submission_observed']):
                        raise ValueError('Contradictory unchanged UI guarantee.')
                    if request.spec.unchanged_view_rejections and error['code'] in {'invalid_request', 'illegal_action'}:
                        evidence = ExecutionEvidence.UNSUBMITTED_UNCHANGED
                # Only play_card currently guarantees both no submission and no prior UI changes.
                if (request.spec.unsubmitted_rejection_unchanged and expected_state is not None
                        and error['code'] in {'invalid_request', 'illegal_action'}
                        and error.get('action_submitted') is False):
                    evidence = ExecutionEvidence.UNSUBMITTED_UNCHANGED
                return GameResponse(self._public_error(error, request), evidence=evidence)
            state = response['state']
            if not isinstance(state, dict):
                raise ValueError('Invalid game state.')
            token = state['snapshot_id']
            if not isinstance(token, str) or not token:
                raise ValueError('Missing observation token.')
            if request.effect == 'file':
                payload = await anyio.to_thread.run_sync(self.screenshots.save, state, arguments)
            else:
                payload = decode_success(operation, state, arguments)
                if request.media_required:
                    payload = attach_divination_image(payload, state)
                if 'available_actions' in payload:
                    payload['available_actions'] = public_tools(payload['available_actions'])
            return GameResponse(payload, token, ExecutionEvidence.SUCCESS)
        except ScreenshotError as error:
            return GameResponse(self._public_error({'code': error.code}, request))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            code = 'timeout' if isinstance(error, TimeoutError) else 'transport_error'
            logging.getLogger(__name__).warning('Game request failed: %s', error)
            return GameResponse(self._public_error({'code': code}, request))
