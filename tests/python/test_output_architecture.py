"""Dependency checks pin the output boundaries, including function-local imports."""
import ast
import unittest
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[2] / 'src/sts2_mcp/output'


def dependencies():
    graph = {}
    for path in OUTPUT.rglob('*.py'):
        name = 'sts2_mcp.output.' + '.'.join(path.relative_to(OUTPUT).with_suffix('').parts)
        graph[name] = {node.module for node in ast.walk(ast.parse(path.read_text()))
                       if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('sts2_mcp.output.')}
    return graph


class OutputArchitectureTests(unittest.TestCase):
    def test_output_dependencies_are_acyclic_including_local_imports(self):
        graph = dependencies()
        visiting, done = [], set()

        def visit(name):
            if name in done:
                return
            self.assertNotIn(name, visiting, ' -> '.join([*visiting, name]))
            visiting.append(name)
            for dependency in sorted(graph[name]):
                if dependency in graph:
                    visit(dependency)
            visiting.pop()
            done.add(name)

        for name in graph:
            visit(name)

    def test_contracts_and_domain_readers_do_not_import_output_assembly(self):
        graph = dependencies()
        contracts = [name for name in graph if '.contracts.' in name]
        self.assertTrue(contracts, 'Missing pure domain contracts.')
        for name in contracts:
            self.assertTrue(all('.contracts.' in dependency or dependency.endswith('.value_shapes')
                                for dependency in graph[name]), (name, graph[name]))
        forbidden = {'sts2_mcp.output.' + name for name in
                     ('game_output', 'player_output', 'response_pipeline', 'inspection_details', 'presets')}
        for name, imports in graph.items():
            if name.endswith('_details') and not name.endswith('.inspection_details'):
                self.assertFalse(imports & forbidden, (name, imports & forbidden))
