"""Treasure summaries preserve static data after complete context/hover validation."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_treasure import state
from tests.python.test_tool_contracts import ContractReply


def details():
    raw = state()
    raw['treasure'].update(chest='open', relic={'name': 'Anchor', 'enabled': True,
        'description': 'Start each combat with 10 Block.',
        'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.'}]},
        proceed={'text': 'Skip', 'enabled': True, 'skips_remaining': True})
    return raw


class TreasurePresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_matches_static_observation_and_native_request_has_no_arguments(self):
        client = ContractReply(details()); tools = GameTools(client)
        result = await tools.inspect_treasure({'preset': 'summary'})
        expected = {'status': 'visible', 'chest': 'open', 'relic': {'name': 'Anchor', 'enabled': True},
                    'proceed': {'text': 'Skip', 'enabled': True, 'skips_remaining': True}}
        self.assertEqual(result.get('treasure'), expected)
        self.assertEqual(set(result), {'scene', 'screen', 'treasure'})
        self.assertEqual(client.calls, [{'operation': 'inspect_treasure', 'expected_state': None, 'arguments': None}])
        self.assertEqual(tools.snapshot_id, 'treasure-1')
        for preset in ('full', 'default', 'summary'):
            observed = await GameTools(ContractReply(details())).get_observation({'preset': preset})
            self.assertEqual(observed['treasure'], expected)

    async def test_empty_relic_remains_explicit_in_all_presets(self):
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset):
                result = await GameTools(ContractReply(state())).inspect_treasure({'preset': preset})
                self.assertIn('treasure', result)
                self.assertIn('relic', result['treasure'])
                self.assertIsNone(result['treasure']['relic'])
                self.assertEqual('proceed' in result['treasure'], preset == 'full')

    async def test_contradictory_context_never_returns_content_or_permission(self):
        for screen in ({'status': 'covered', 'view': 'map'}, {'status': 'hidden'},
                       {'status': 'not_ready'}, {'status': 'visible', 'view': 'deck'}):
            for preset in ('full', 'default', 'summary'):
                with self.subTest(screen=screen, preset=preset):
                    raw = details(); raw['screen'] = screen
                    tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'previous'
                    result = await tools.inspect_treasure({'preset': preset})
                    self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                    self.assertIsNone(tools.snapshot_id)

    async def test_unavailable_hover_preserves_static_relic_and_full_default_note(self):
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset):
                raw = details(); raw['treasure']['relic'].update(enabled=False, description=None, hover_tips=[])
                raw['unavailable_hover_sources'] = ['treasure.relic']
                result = await GameTools(ContractReply(raw)).inspect_treasure({'preset': preset})
                self.assertIn('treasure', result)
                relic = result['treasure']['relic']
                self.assertEqual((relic['name'], relic['enabled']), ('Anchor', False))
                self.assertEqual('description' in relic, preset == 'full')
                self.assertEqual('hover_tips' in relic, preset != 'summary')
                if preset != 'summary':
                    self.assertEqual(result['notes']['hover_tips_unavailable']['sources'], ['treasure.relic'])
                else:
                    self.assertNotIn('notes', result)

    async def test_malformed_hover_is_rejected_even_when_summary_would_remove_it(self):
        mutations = [lambda r: r['treasure']['relic'].pop('description'),
            lambda r: r['treasure']['relic'].update(hover_tips=[{'title': 'Missing description'}]),
            lambda r: r['treasure']['relic'].update(description=None, hover_tips=[]),
            lambda r: r.update(unavailable_hover_sources=['treasure.relic']),
            lambda r: r.update(unavailable_hover_sources=['wrong.source']),
            lambda r: (r['treasure']['relic'].update(description=None),
                       r.update(unavailable_hover_sources=['treasure.relic']))]
        for mutate in mutations:
            for preset in ('full', 'summary'):
                with self.subTest(mutate=mutate, preset=preset):
                    raw = copy.deepcopy(details()); mutate(raw)
                    tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'previous'
                    result = await tools.inspect_treasure({'preset': preset})
                    self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                    self.assertIsNone(tools.snapshot_id)

    async def test_local_invalid_arguments_keep_existing_permission_without_ipc(self):
        for args in ({'preset': 'bad'}, {'preset': False}, {'relic_ids': []}):
            client = ContractReply(details()); tools = GameTools(client); tools.snapshot_id = 'previous'
            result = await tools.inspect_treasure(args)
            self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertEqual(tools.snapshot_id, 'previous')
            self.assertEqual(client.calls, [])
