"""Display progress belongs to page bodies, independently of screen visibility."""
import copy
import unittest
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS
from tests.python.test_events import state as event
from tests.python.test_ancients import state as ancient
from tests.python.test_rewards import state as rewards
from tests.python.test_rest_site import state as rest
from tests.python.test_treasure import state as treasure
from tests.python.test_shop import state as shop
from tests.python.test_divination import state as divination
from tests.python.test_run_ending import state as ending


def disable(value):
    if isinstance(value, dict):
        if 'enabled' in value: value['enabled'] = False
        for child in value.values(): disable(child)
    elif isinstance(value, list):
        for child in value: disable(child)


def output(state, preset='full'):
    request = normalize_request(TOOLS['get_observation'], {'preset': preset})
    return request.project(decode_success(request.operation, state))


class PresentationStatusTests(unittest.TestCase):
    def test_action_navigation_notes_do_not_replace_the_pending_page_note(self):
        from sts2_mcp.output.action_output import action_result
        raw = ancient(); raw['ancient']['status'] = 'not_ready'; disable(raw['ancient'])
        raw['available_actions'] = []
        raw['transition'] = {'stop_reason': 'choice_required', 'complete': True, 'events': []}
        payload = decode_success('get_state', raw)
        payload['transition'] = raw['transition']
        payload['notes']['selection'] = 'Selection pending; close this view to return.'
        result = action_result(payload)
        self.assertIn('selection', result['notes'])
        self.assertEqual(result['notes'].get('presentation', {}).get('sources'), ['ancient'])

    def test_compact_observation_and_close_receipts_preserve_pending_page_note(self):
        raw = ancient(); raw['ancient']['status'] = 'not_ready'
        raw['available_actions'] = ['inspect_ancient']; disable(raw['ancient'])
        for tool, preset in (('get_observation', 'actions_only'), ('get_observation', 'top_bar'),
                             ('close_card_view', 'full'), ('close_card_view', 'default')):
            with self.subTest(tool=tool, preset=preset):
                request = normalize_request(TOOLS[tool], {'preset': preset})
                value = request.project(decode_success(request.operation, copy.deepcopy(raw)))
                self.assertNotIn('ancient', value)
                self.assertEqual(value['available_actions'], ['inspect_ancient'])
                self.assertEqual(value.get('notes', {}).get('presentation', {}).get('sources'), ['ancient'])
                self.assertIn('available actions', value['notes']['presentation']['message'])

    def test_partial_page_contents_keep_explicit_status_and_note_in_all_presets(self):
        for key, factory in (('event', event), ('ancient', ancient), ('rewards', rewards),
                             ('rest_site', rest), ('treasure', treasure), ('shop', shop),
                             ('divination', divination), ('run_result', ending)):
            raw = factory(); raw[key]['status'] = 'not_ready'; raw['available_actions'] = []; disable(raw[key])
            for preset in ('full', 'default', 'summary'):
                with self.subTest(page=key, preset=preset):
                    try: value = output(copy.deepcopy(raw), preset)
                    except ValueError as error: self.fail('Partial page was rejected: ' + str(error))
                    self.assertEqual(value[key]['status'], 'not_ready')
                    self.assertEqual(value['screen']['status'], 'visible')
                    self.assertIn('presentation', value.get('notes', {}))
                    self.assertIn(key, value['notes']['presentation']['sources'])
                    self.assertIn('incomplete', value['notes']['presentation']['message'])
                    if key == 'treasure': self.assertIn('relic', value[key])

    def test_disabled_buttons_do_not_turn_complete_pages_into_partial_contents(self):
        for key, factory in (('event', event), ('ancient', ancient), ('rewards', rewards),
                             ('rest_site', rest), ('treasure', treasure), ('shop', shop), ('run_result', ending)):
            raw = factory(); raw['available_actions'] = []; disable(raw[key])
            value = output(raw)
            self.assertEqual(value[key]['status'], 'visible')
            self.assertNotIn('presentation', value.get('notes', {}))

    def test_partial_ancient_cannot_claim_a_covering_screen(self):
        raw = ancient(); raw['ancient']['status'] = 'not_ready'
        raw['available_actions'] = []; disable(raw['ancient'])
        raw['screen'] = {'status': 'covered', 'view': 'deck'}
        with self.assertRaises(ValueError): output(raw)
