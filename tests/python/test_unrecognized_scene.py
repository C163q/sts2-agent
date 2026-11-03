"""Keep fallback observations distinct from supported room scenes."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_output_boundaries import observation, ReplyClient


def fallback(scene):
    raw = observation()
    raw.update(scene=scene, screen={'status': 'not_applicable'}, turn=None, player=None,
               enemies=None, top_bar=None, buttons=None, available_actions=[])
    return raw


class UnrecognizedSceneTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_fallback_can_be_read_with_every_observation_preset(self):
        tools = GameTools(ReplyClient(fallback('unrecognized')))
        for preset in ('default', 'full', 'summary', 'actions_only', 'top_bar'):
            with self.subTest(preset=preset):
                result = await tools.get_observation({'preset': preset})
                self.assertNotIn('error', result)
                self.assertEqual(result['scene'], 'unrecognized')
                self.assertEqual(result['screen'], {'status': 'not_applicable'})
                self.assertEqual(result['available_actions'], [])
                self.assertEqual(tools.snapshot_id, 'test-state')

    async def test_obsolete_fallback_identifier_is_rejected_before_permission(self):
        tools = GameTools(ReplyClient(fallback('loading_or_noncombat')))
        result = await tools.get_observation({'preset': 'summary'})
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)
