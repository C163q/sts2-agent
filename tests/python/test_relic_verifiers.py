"""Keep standalone inspection verification usable with current gameplay responses."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.game.verifiers import verify_relics
from tests.python.test_output_boundaries import observation


class RelicVerifierTests(unittest.TestCase):
    def test_file_verifier_accepts_context_static_state_and_unavailable_help(self):
        static = {'name': 'Pen Nib', 'counter': 0, 'melted': None, 'grayed_out': True, 'pulsing': False}
        state = observation()
        state.update(schema_version=37)
        state['top_bar']['relics'] = [static]
        raw = {'ok': True, 'state': {'schema_version': 37, 'snapshot_id': 'test-state',
            'scene': 'combat', 'screen': {'status': 'visible'},
            'relics': [{**static, 'description': None, 'hover_tips': []}],
            'unavailable_hover_sources': ['relics.0']}}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with patch('sys.argv', ['verify_relics', '--ipc-dir', directory, '--output', str(target/'full.json'),
                                   '--report', str(target/'report.json')]), \
                    patch.object(verify_relics, 'Client') as factory:
                factory.return_value.call.side_effect = [
                    {'ok': True, 'state': copy.deepcopy(state)}, raw, copy.deepcopy(raw),
                    {'ok': True, 'state': copy.deepcopy(state)}]
                verify_relics.main()
            value = json.loads((target/'full.json').read_text())
            self.assertEqual(value['scene'], 'combat')
            self.assertEqual(value['notes']['hover_tips_unavailable']['sources'], ['relics.0'])
            self.assertIs(value['relics'][0]['grayed_out'], True)
            self.assertIs(value['relics'][0]['pulsing'], False)
            self.assertIsNone(value['relics'][0]['description'])
