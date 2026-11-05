"""Grouped maps retain scope and native choices without implying connections."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.support.fake_game import map_payload
from tests.python.test_map_travel import map_observation
from tests.python.test_tool_contracts import ContractReply


def native_observation():
    state = map_observation()
    graph = map_payload()
    graph.update(can_travel=True, selectable_nodes=['map:1:2:1', 'map:1:2:5'])
    state.update(schema_version=41, map={'status': 'visible', **{k:v for k,v in graph.items()
        if k not in {'scene', 'screen'}}})
    return state


class GroupedMapTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_preserves_scope_choices_and_omits_all_details(self):
        graph = map_payload()
        graph.update(can_travel=True, selectable_nodes=['map:1:2:1', 'map:1:2:5'])
        graph['nodes'][2].update(revealed_type='monster', marked=True)
        for depth, expected in [(0, {'ancient':['map:1:0:3'], 'monster':['map:1:1:2'],
                'unknown':['map:1:2:1'], 'rest_site':['map:1:2:5'], 'boss':['map:1:3:3', 'map:1:4:3']}),
                (1, {'monster':['map:1:1:2'], 'unknown':['map:1:2:1']}),
                (2, {'monster':['map:1:1:2'], 'unknown':['map:1:2:1'], 'boss':['map:1:3:3']})]:
            tools = GameTools(ContractReply({'snapshot_id':'map-token', **graph}))
            result = await tools.inspect_map({'preset':'summary', 'max_steps':depth})
            self.assertNotIn('error', result)
            self.assertEqual(result['nodes_by_type'], expected)
            self.assertEqual(result['selectable_nodes'], graph['selectable_nodes'])
            self.assertEqual(set(result), {'scene', 'screen', 'act', 'current_node', 'can_travel',
                'selectable_nodes', 'nodes_by_type'} | ({'max_steps'} if depth else set()))
            self.assertEqual(tools.snapshot_id, 'map-token')

    async def test_entry_summary_uses_lowest_row_and_default_null_rules(self):
        graph = map_payload()
        graph.update(current_node=None, visited_path=[])
        tools = GameTools(ContractReply({'snapshot_id':'map-token', **graph}))
        result = await tools.inspect_map({'preset':'summary', 'max_steps':1})
        self.assertNotIn('error', result)
        self.assertEqual(result['nodes_by_type'], {'ancient':['map:1:0:3']})
        self.assertNotIn('current_node', result)

    async def test_observation_presets_share_entire_graph_and_note(self):
        original = native_observation()
        for preset in ['full', 'default', 'summary', 'actions_only', 'top_bar']:
            tools = GameTools(ContractReply(original))
            result = await tools.get_observation({'preset':preset})
            self.assertNotIn('error', result)
            if preset in ['actions_only', 'top_bar']:
                self.assertNotIn('map', result)
                self.assertNotIn('map', result.get('notes', {}))
                continue
            self.assertEqual(result['map']['nodes_by_type']['boss'], ['map:1:3:3', 'map:1:4:3'])
            self.assertEqual(set(result['map']), {'status', 'act', 'current_node', 'can_travel',
                'selectable_nodes', 'nodes_by_type'})
            self.assertEqual(result['notes']['map'], 'Map connections omitted; use inspect_map for details.')
        self.assertEqual(original, native_observation())

    async def test_new_schema_cannot_hide_a_broken_graph_behind_any_preset(self):
        for preset in ['full', 'summary', 'actions_only', 'top_bar']:
            for corruption in ['bad_edge', 'missing_nodes', 'missing_path']:
                state = native_observation()
                if corruption == 'bad_edge': state['map']['nodes'][-1]['next'] = ['map:9:9:9']
                elif corruption == 'missing_nodes': state['map'].pop('nodes')
                else: state['map'].pop('visited_path')
                tools = GameTools(ContractReply(state)); tools.snapshot_id = 'previous'
                result = await tools.get_observation({'preset':preset})
                self.assertEqual(result.get('error', {}).get('code'), 'transport_error', (preset, corruption, result))
                self.assertIsNone(tools.snapshot_id)

    async def test_no_map_has_no_map_note(self):
        state = native_observation()
        state.update(map=None, available_actions=[], screen={'status':'covered', 'view':'deck'})
        result = await GameTools(ContractReply(state)).get_observation({'preset':'full'})
        self.assertNotIn('error', result)
        self.assertNotIn('map', result.get('notes', {}))

    async def test_map_rejection_retains_only_explicit_unchanged_permission(self):
        for guaranteed, retain in [(True, True), (False, False), (None, False)]:
            error = {'code':'illegal_action', 'public_message':'Return from the card selection before opening the map.'}
            if guaranteed is not None: error['ui_unchanged'] = guaranteed
            tools = GameTools(ContractReply({}, error)); tools.snapshot_id = 'previous'
            result = await tools.inspect_map()
            self.assertEqual(tools.snapshot_id, 'previous' if retain else None)
            self.assertEqual(result['error']['recovery'], 'choose_legal_action' if retain else 'get_observation')
            self.assertEqual(result['error']['message'], error['public_message'])
        tools = GameTools(ContractReply({}, {'code':'illegal_action', 'ui_unchanged':True}))
        await tools.inspect_map()
        self.assertIsNone(tools.snapshot_id)

    async def test_corrupt_details_are_validated_before_summary_filtering(self):
        graph = map_payload()
        graph['nodes'][-1]['type'] = 'secret'
        result = await GameTools(ContractReply({'snapshot_id':'token', **graph})).inspect_map({'preset':'summary', 'max_steps':1})
        self.assertEqual(result.get('error', {}).get('code'), 'transport_error')

    async def test_interaction_evidence_cannot_claim_an_unchanged_rejection(self):
        class Interacted(ContractReply):
            def call(self, *args, **kwargs):
                result = super().call(*args, **kwargs)
                result['execution'] = {'ui_interaction_started':True,
                    'action_submission_observed':False, 'state_captured':True}
                return result
        tools = GameTools(Interacted({}, {'code':'illegal_action', 'ui_unchanged':True}))
        tools.snapshot_id = 'previous'
        result = await tools.inspect_map()
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_full_entry_keeps_null_and_other_presets_use_public_null_rules(self):
        state = native_observation()
        state['map'].update(current_node=None, visited_path=[])
        for preset in ['full', 'default', 'summary']:
            result = await GameTools(ContractReply(state)).get_observation({'preset':preset})
            self.assertNotIn('error', result)
            self.assertEqual('current_node' in result['map'], preset == 'full')
            self.assertEqual(len(result['map']['nodes_by_type']['boss']), 2)

    async def test_native_map_room_context_is_shared_by_observation_and_map_details(self):
        state = native_observation(); state['scene'] = 'map'
        result = await GameTools(ContractReply(state)).get_observation({'preset':'full'})
        self.assertNotIn('error', result)
        self.assertEqual(result['scene'], 'map')
        self.assertTrue(result['map']['can_travel'])
        graph = map_payload(); graph['scene'] = 'map'
        result = await GameTools(ContractReply({'snapshot_id':'token', **graph})).inspect_map({'preset':'summary'})
        self.assertNotIn('error', result)
        self.assertEqual(result['scene'], 'map')
