"""Run graphical verifiers in an owned game process, with explicit run groups."""
from scripts._bootstrap import ROOT
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from sts2_mcp.roundtrip_client import Client

CATALOG = json.loads((ROOT / 'tests/game/data/test_scenarios.json').read_text())
SUPPORTED_VERIFIERS = {
    'verify_necrobinder_feedback.py',
    'verify_relic_settling.py',
    'verify_hp_preview.py',
    'verify_screenshots.py',
    'verify_result_option.py',
    'verify_result_inspection.py',
    'verify_presentation_status.py',
    'verify_dialogue_recovery.py',
    'verify_ancient_choice_recovery.py',
    'verify_ancient_inspection.py',
    'verify_confirmation.py',
    'verify_divination_recovery.py',
    'verify_divination_tool_view.py',
    'verify_choose_event_option_review.py',
    'verify_event_inspection.py',
    'verify_buy_item_review.py',
    'verify_close_shop_review.py',
    'verify_open_shop_review.py',
    'verify_shop_inspection_review.py',
    'verify_choose_rest_option_review.py',
    'verify_rest_site_inspection_review.py',
    'verify_proceed_review.py',
    'verify_loot_treasure_review.py',
    'verify_treasure_inspection_review.py',
    'verify_claim_reward_review.py',
    'verify_reward_inspection_review.py',
    'verify_travel_review.py',
    'verify_close_map_review.py',
    'verify_map_summary.py',
    'verify_selection_view_review.py',
    'verify_selection_option_review.py',
    'verify_select_card_review.py',
    'verify_selection_review.py',
    'verify_potion_recovery.py',
    'verify_discard_potion_review.py',
    'verify_potion_discard_queue.py',
    'verify_use_potion_review.py',
    'verify_play_cards.py',
    'verify_play_card_review.py',
    'verify_turn_transitions.py',
    'verify_card_view_close.py',
    'verify_pile_inspection.py',
    'verify_deck_inspection.py',
    'verify_relic_inspection.py',
    'verify_potion_presets.py',
    'verify_display_readers.py',
    'verify_native_dispatch.py',
    'verify_native_responses.py',
    'verify_inspection_errors.py',
    'verify_combatant_presets.py',
    'verify_card_formats.py',
    'verify_ui_context.py',
    'verify_run_result_observation.py',
    'verify_browsable_content.py',
    'verify_top_bar_views.py',
    'verify_selection_observations.py',
    'verify_observation_presets.py',
    'verify_default_presets.py',
    'verify_card_additions.py',
    'verify_selection_upgrades.py',
    'verify_view_availability.py',
    'verify_relic_presets.py',
    'verify_companions.py',
    'verify_damage_attribution.py',
    'verify_action_observations.py', 'verify_kill_settling.py', 'verify_rest_site.py',
    'verify_shop.py', 'verify_rewards.py', 'verify_treasure.py',
    'verify_suite_continuation.py', 'verify_suite_pending.py',
    'verify_selection_scene.py',
    'verify_action_stability.py',
    'verify_observation_sources.py',
    'verify_ancient_stability.py',
    'verify_ancients.py',
    'verify_map_presets.py',
    'verify_reward_alternatives.py',
    'verify_power_text.py',
    'verify_hand_presets.py',
    'verify_selection_presets.py',
    'verify_resource_events.py',
    'verify_inventory_events.py',
    'verify_combat_resources.py',
    'verify_capacity.py',
    'verify_permanent_cards.py',
    'verify_orb_events.py',
    'verify_combat_handoff.py',
}


def load_cases(path):
    cases = json.loads(Path(path).read_text())
    if not isinstance(cases, list) or not cases:
        raise ValueError('A suite must contain cases.')
    names = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'name', 'scenarios', 'steps'}:
            raise ValueError('Expected name, scenarios and steps.')
        name = case['name']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in names or name == 'game':
            raise ValueError('Case names must be unique directory names.')
        names.add(name)
        scenarios = case['scenarios']
        if not isinstance(scenarios, dict) or any(
                key == 'ending' or key not in CATALOG or value not in CATALOG[key]
                for key, value in scenarios.items()):
            raise ValueError('Unknown or process-isolated scenario.')
        if not isinstance(case['steps'], list) or not case['steps']:
            raise ValueError('Each run needs at least one step.')
        step_names = set()
        for step in case['steps']:
            if not isinstance(step, dict) or set(step) != {'name', 'verifier', 'args'}:
                raise ValueError('Expected step name, verifier and args.')
            name = step['name']
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in step_names:
                raise ValueError('Step names must be unique directory names.')
            step_names.add(name)
            verifier = step['verifier']
            if (not isinstance(verifier, str) or verifier not in SUPPORTED_VERIFIERS
                    or not (ROOT / 'tests/game/verifiers' / verifier).is_file()):
                raise ValueError('Verifier must be a repository verification script.')
            args = step['args']
            if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
                raise ValueError('Verifier arguments must be strings.')
            scenario_options = {
                'verify_necrobinder_feedback.py': ('pen_nib', 'soul', 'manual_sources'),
                'verify_screenshots.py': ('gui',),
                'verify_result_option.py': ('basic', 'history'),
                'verify_result_inspection.py': ('wrong_room','history'),
                'verify_presentation_status.py': ('event','ancient','rewards','rest_site','shop','treasure','divination','epilogue','run_result'),
                'verify_dialogue_recovery.py': ('wrong_room','basic','dialogue','default','selection','rewards','stale'),
                'verify_confirmation.py': ('no_dialog','cancel','replacement','unowned','covered','confirm','buttons'),
                'verify_divination_recovery.py': ('no_board','small','big','cleared','covered','finished','rewards','selection','curse','gold','relic','direct'),
                'verify_divination_tool_view.py': ('no_board','playing','finished','rewards','selection'),
                'verify_choose_event_option_review.py': ('no_event','basic','locked','upgrade','reward','trial','crystal','dense_choice','combat','death','rescue','potions'),
                'verify_event_inspection.py': ('no_event','basic','display','locked','glyphs','play'),
                'verify_buy_item_review.py': ('no_shop','basic','remove','courier','cauldron','sozu','hidden_price','nested','choice','fake','choice_timing'),
                'verify_close_shop_review.py': ('no_shop','basic','fake','remove','nested','parasol'),
                'verify_open_shop_review.py': ('no_shop','basic','fake','remove','parasol'),
                'verify_shop_inspection_review.py': ('no_shop','basic','remove','courier','hidden_price','fake','full','nested','parasol','display'),
                'verify_choose_rest_option_review.py': ('no_rest','basic','disabled','selection','rewards','counters','combat','targets'),
                'verify_rest_site_inspection_review.py': ('no_rest','basic','disabled','tent','selection','heal_rewards','dig','display_red','display'),
                'verify_proceed_review.py': ('combat','reward_skip','reward_empty','nested_reward','treasure_skip','treasure_collected','rest','tent','shop','event','ancient','divination','boss1','event_resume','selection','confirmation'),
                'verify_loot_treasure_review.py': ('basic','open','empty','extra','nested','choice','covered','no_treasure','map_pending','display'),
                'verify_treasure_inspection_review.py': ('basic','empty','extra','nested','choice','no_treasure','map_pending','display_red','display'),
                'verify_claim_reward_review.py': ('basic','full','linked','nested','returned','covered','no_rewards','transform','deck_covered','scroll_success','scroll_failure'),
                'verify_reward_inspection_review.py': ('no_rewards','basic','linked','empty','nested','returned','escaped','deck_covered','legacy'),
                'verify_travel_review.py': ('basic', 'flight', 'combat', 'choice', 'shop', 'treasure', 'unknown', 'entry', 'double', 'antler', 'scroll_failure', 'resource_rest', 'resource_unknown', 'resource_combat', 'resource_hidden'),
                'verify_close_map_review.py': ('no_map', 'combat', 'event', 'selection', 'entry', 'divination', 'legacy'),
                'verify_map_summary.py': ('map', 'selection', 'act_entry'),
                'verify_selection_view_review.py': ('no_selection', 'overlay', 'grid', 'hand_upgrade',
                    'covered_deck', 'covered_map', 'noncombat', 'results'),
                'verify_selection_option_review.py': ('no_selection', 'invalid_option', 'disabled', 'battlefield',
                    'covered', 'choose_skip', 'reward_skip', 'grid_manual', 'hand_zero', 'hand_one',
                    'hand_upgrade', 'deck_cancel', 'deck_preview', 'smith', 'multi_upgrade', 'enchant_single',
                    'enchant_multi', 'transform', 'bundle', 'view_cards', 'death', 'victory', 'shop_remove'),
                'verify_select_card_review.py': ('no_selection', 'invalid_candidate', 'covered', 'scroll_race',
                    'choose_one', 'reward', 'grid', 'scroll', 'hand', 'hand_upgrade', 'combat_pile', 'deck', 'smith',
                    'multi_upgrade', 'enchant_single', 'enchant_multi', 'transform', 'bundle', 'view_cards',
                    'chain', 'death', 'victory', 'combat_entry', 'hand_replace', 'grid_manual', 'upgrade_view'),
                'verify_selection_review.py': ('no_selection', 'covered', 'hand_upgrade', 'bundle', 'view_cards'),
                'verify_potion_discard_queue.py': ('choose_one', 'hand', 'pile', 'noncombat_upgrade', 'immediate',
                    'cancel', 'hidden', 'multiple', 'skip', 'pending_reset', 'after_reset', 'card_choice', 'card_pile', 'hand_upgrade', 'fault', 'foreign'),
                'verify_discard_potion_review.py': ('basic', 'default', 'automatic', 'fruit', 'blocked',
                    'replace', 'covered', 'display', 'skill', 'noncombat_event', 'noncombat_rest',
                    'noncombat_shop', 'noncombat_map', 'noncombat_reward', 'merchant_inventory'),
                'verify_potion_recovery.py': tuple(mode for mode in CATALOG['potion'] if mode != 'inspection' and not mode.startswith('discard_'))
                    + ('default', 'covered', 'slot_boundary', 'journal_boundary', 'fake_merchant', 'obtained_boundary', 'journal_hidden', 'map_context', 'slot_interaction'),
                'verify_use_potion_review.py': tuple(mode for mode in CATALOG['potion'] if mode != 'inspection' and not mode.startswith('discard_'))
                    + ('default', 'covered', 'slot_boundary', 'journal_boundary', 'fake_merchant'),
                'verify_play_cards.py': ('admission', 'ordered', 'native_reject', 'default', 'single_entry', 'autoplay', 'pending_reset', 'after_reset', 'diagnostics', 'atomic', 'partial', 'zero', 'energy', 'stars', 'target',
                    'random_exhaust', 'hand_exhaust', 'automatic_hand', 'choose_one', 'immediate_choice',
                    'combat_pile', 'victory', 'death', 'immediate_death'),
                'verify_play_card_review.py': ('queue_ordered', 'queue_energy', 'queue_stars', 'queue_target',
                    'queue_bullet_time', 'queue_survivor_manual', 'queue_survivor_auto', 'queue_dagger_manual', 'queue_dagger_auto',
                    'queue_random_exhaust', 'queue_hand_exhaust', 'queue_automatic_hand', 'queue_choose_one',
                    'queue_combat_pile', 'queue_victory', 'queue_death', 'queue_immediate_death', 'basic', 'energy', 'stars', 'unplayable',
                    'card_logic', 'cancel', 'hand_choice', 'choose_one', 'combat_pile', 'victory', 'death',
                    'covered', 'noncombat', 'random', 'x_cost', 'hook'),
                'verify_turn_transitions.py': ('headbutt_empty', 'headbutt_single', 'headbutt_multiple', 'shining', 'hatchet', 'hatchet_draw', 'knife', 'won', 'lost', 'checks', 'preflight', 'noncombat'),
                'verify_card_view_close.py': ('combat', 'selection', 'battlefield', 'ancient'),
                'verify_pile_inspection.py': ('draw', 'combat', 'selection', 'battlefield'),
                'verify_deck_inspection.py': ('combat', 'context', 'selection', 'shop', 'epilogue'),
                'verify_relic_inspection.py': ('combat', 'context'),
                'verify_potion_presets.py': ('checks', 'combat', 'merchant', 'rest', 'empty', 'map'),
                'verify_native_responses.py': ('combat', 'context', 'divination', 'event_selection'),
                'verify_inspection_errors.py': ('basic', 'energy'),
                'verify_combatant_presets.py': ('basic', 'orbs', 'osty', 'blade', 'selection'),
                'verify_card_formats.py': ('afflictions', 'browse', 'resources'),
                'verify_ui_context.py': ('combat', 'orbs', 'event', 'rest', 'treasure', 'ancient', 'shop', 'rewards', 'selection', 'confirmation', 'divination'),
                'verify_run_result_observation.py': ('history',),
                'verify_browsable_content.py': ('rewards', 'history', 'audit'),
                'verify_top_bar_views.py': ('combat', 'selection', 'event', 'entry', 'confirmation', 'divination'),
                'verify_selection_observations.py': ('grid', 'upgrades'),
                'verify_observation_presets.py': ('combat', 'orbs', 'osty', 'blade', 'enchantments', 'rest', 'event', 'divination', 'native', 'empty_inventory'),
                'verify_default_presets.py': ('combat', 'orbs', 'smith', 'transform', 'divination', 'map', 'event'),
                'verify_card_additions.py': ('hand', 'overflow', 'discard', 'normal', 'enemy', 'reward', 'checks'),
                'verify_view_availability.py': ('event', 'rest', 'treasure', 'reward', 'shop', 'ancient', 'selection', 'combat', 'result', 'confirmation', 'epilogue'),
                'verify_relic_presets.py': ('wax_melt', 'shop'),
                'verify_companions.py': ('osty', 'blade', 'checks', 'blade_checks', 'first'),
                'verify_damage_attribution.py': ('card', 'aoe', 'aoe_lethal', 'doom', 'potion',
                    'fog_natural', 'fog_card', 'fog_cleanup', 'fog_thorns', 'revival'),
                'verify_combat_handoff.py': ('play', 'turn', 'selection', 'choice', 'checks'),
                'verify_orb_events.py': ('play', 'checks', 'chain'),
                'verify_permanent_cards.py': ('genetic', 'cost', 'enchant', 'checks'),
                'verify_capacity.py': ('resources', 'orbs', 'orb_visibility', 'wax_melt'),
                'verify_combat_resources.py': ('spend', 'gain', 'stars', 'star_spend', 'turbo', 'choice', 'fake_merchant', 'visibility', 'reveal_visibility', 'selection_entry'),
                'verify_inventory_events.py': ('smith', 'cook', 'upgrade', 'transform', 'enchant', 'remove', 'shop', 'reward', 'ancient', 'rescue', 'temporary', 'visibility'),
                'verify_resource_events.py': ('event', 'rescue', 'rest', 'cook', 'shop', 'reward', 'ancient',
                    'potion_combat', 'potion_rest', 'combat', 'visibility', 'entry', 'masks'),
                'verify_rest_site.py': CATALOG['rest'], 'verify_shop.py': CATALOG['shop'],
                'verify_rewards.py': CATALOG['reward'], 'verify_treasure.py': CATALOG['treasure'],
                'verify_kill_settling.py': ('card', 'potion', 'phase', 'ui', 'choice', 'energy'),
                'verify_selection_scene.py': ('ancient_bundle', 'rest_smith', 'combat_discovery', 'event_deck', 'shop_remove'),
                'verify_action_stability.py': ('anger', 'turbo', 'blade_dance', 'pommel_strike',
                                              'bloodletting', 'gather_light', 'preview_draw', 'preview_messy'),
                'verify_observation_sources.py': ('map', 'views', 'selection'),
                'verify_ancient_stability.py': ('direct', 'travel', 'travel_action'),
                'verify_ancient_choice_recovery.py': ('no_ancient','basic','default','dialogue','covered','disabled','offscreen','hidden','stale','transform','bundle','nested','touch','hidden_inventory','hidden_top_bar'),
                'verify_ancient_inspection.py': ('basic', 'dialogue', 'touch', 'selection', 'bundle', 'nested', 'safe', 'lethal', 'display', 'no_ancient'),
                'verify_ancients.py': CATALOG['ancient'],
                'verify_map_presets.py': ('flight', 'combat', 'entry', 'double'),
                'verify_reward_alternatives.py': ('paels_wing', 'driftwood'),
                'verify_hand_presets.py': ('basic', 'stars', 'x_cost', 'card_names', 'selection', 'enchantments'),
                'verify_selection_presets.py': ('discovery', 'hand_upgrade', 'smith', 'ancient_multi',
                    'ancient_transform', 'ancient_bundle', 'ancient_pandora', 'event_enchant', 'paels_wing', 'driftwood',
                    'grid', 'combat_pile', 'deck', 'hand'),
                'verify_selection_upgrades.py': ('smith', 'event_upgrade', 'ancient_transform', 'ancient_pandora', 'reward', 'deck', 'multi_upgrade'),
            }
            if args and (verifier not in scenario_options or len(args) != 2
                         or args[0] != '--scenario' or args[1] not in scenario_options[verifier]):
                raise ValueError('Only the verifier scenario argument may be supplied.')
    return cases


def execute_cases(cases, session, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'report.json'
    if report_path.exists():
        raise FileExistsError(report_path)
    report = {'status': 'running', 'cases': []}
    started = time.monotonic()
    seen_runs = set()
    process = None

    def save():
        report['duration_seconds'] = time.monotonic() - started
        temporary = report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(report_path)

    save()
    for case in cases:
        print(f"Starting test run: {case['name']}", flush=True)
        record = {'name': case['name'], 'scenarios': case['scenarios'], 'steps': [], 'status': 'running'}
        report['cases'].append(record)
        save()
        directory = output / case['name']
        try:
            directory.mkdir()
            begin = time.monotonic()
            identity = session.begin_run(case['scenarios'])
            record['setup_seconds'] = time.monotonic() - begin
            record['setup_phases_seconds'] = getattr(session, 'last_setup', {})
            record['identity'] = identity
            run = identity.get('run_id')
            current_process = (identity.get('process_id'), identity.get('session'))
            if not run or run in seen_runs or process is not None and current_process != process:
                raise RuntimeError('Expected a new run in the same owned game process.')
            seen_runs.add(run)
            process = current_process
            for step in case['steps']:
                entry = {'name': step['name'], 'verifier': step['verifier'], 'status': 'running'}
                record['steps'].append(entry)
                begin = time.monotonic()
                try:
                    entry.update(session.run_step(step, directory / step['name']))
                    if session.identity() != identity:
                        raise RuntimeError('A same-run step unexpectedly replaced the run or process.')
                    entry['status'] = 'passed'
                finally:
                    entry['duration_seconds'] = time.monotonic() - begin
                    save()
            begin = time.monotonic()
            session.reset_run()
            record['cleanup_seconds'] = time.monotonic() - begin
            record['status'] = 'passed'
        except (Exception, KeyboardInterrupt) as error:
            record['status'] = 'failed'
            record['error'] = f'{type(error).__name__}: {error}'
            if record['steps'] and record['steps'][-1]['status'] == 'running':
                record['steps'][-1]['status'] = 'failed'
            report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
            save()
            return report
        save()
    report['status'] = 'passed'
    save()
    return report


class GameSession:
    def __init__(self, work, python=sys.executable, step_timeout=240):
        self.work = Path(work).resolve()
        self.python = python
        self.step_timeout = step_timeout
        self.client = Client(self.work / 'ipc', timeout=140)
        self.game = None

    def __enter__(self):
        self.work.mkdir(parents=True, exist_ok=False)
        started = time.monotonic()
        try:
            self.game = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_roundtrip.py'),
                '--windowed', '--capture', '--suite', '--work-dir', str(self.work)], cwd=ROOT)
            # Requests can wait through initial asset loading; UUIDs and fresh IPC prevent old replies.
            deadline = time.monotonic() + 120
            while not (self.work / 'stdout.log').exists():
                self.check_process()
                if time.monotonic() >= deadline:
                    raise TimeoutError('The test launcher did not initialize its workspace.')
                time.sleep(.1)
            state = self.request('get_state')['state']
            while state['scene'] != 'main_menu':
                self.check_process()
                if time.monotonic() >= deadline:
                    raise TimeoutError('The test game did not reach the main menu.')
                time.sleep(.2)
                state = self.request('get_state')['state']
            self.startup_seconds = time.monotonic() - started
            self.initial_identity = self.identity()
            if self.initial_identity['process_id'] != self.game.pid or self.initial_identity['run_id'] is not None:
                raise RuntimeError('IPC is not connected to the owned game at the main menu.')
            return self
        except BaseException:
            self.close()
            raise

    def check_process(self):
        if self.game.poll() is not None:
            raise RuntimeError(f'The owned game exited: {self.game.returncode}')

    def request(self, operation, token=None, arguments=None):
        self.check_process()
        result = self.client.call(operation, token, arguments=arguments)
        if not result.get('ok'):
            raise RuntimeError(result)
        return result

    def identity(self):
        state = self.request('get_test_session')['state']
        return {key: state[key] for key in ('process_id', 'session', 'run_id')}

    def begin_run(self, scenarios):
        begin = time.monotonic()
        state = self.request('get_state')['state']
        self.request('configure_test_run', state['snapshot_id'], {'scenarios': scenarios})
        state = self.request('get_state')['state']
        configured = time.monotonic()
        self.request('start_test_combat', state['snapshot_id'])
        self.last_setup = {'configure': configured - begin, 'create': time.monotonic() - configured}
        return self.identity()

    def reset_run(self):
        state = self.request('get_state')['state']
        result = self.request('reset_test_run', state['snapshot_id'])['state']
        if result['run_id'] is not None:
            raise RuntimeError('The old test run survived cleanup.')

    def run_step(self, step, directory):
        directory.mkdir()
        environment = {**os.environ, 'PLAY_WINDOWED': '1',
                       'STS2_AGENT_VERIFY_IPC_DIR': str(self.client.directory),
                       'STS2_AGENT_VERIFY_REUSE_RUN': '1'}
        with (directory / 'verifier.log').open('w') as log:
            try:
                module = 'tests.game.verifiers.' + Path(step['verifier']).stem
                verifier = subprocess.Popen([self.python, '-m', module,
                    '--report', str(directory / 'evidence.json'), *step['args']], cwd=ROOT,
                    env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    returncode = verifier.wait(timeout=self.step_timeout)
                finally:
                    # The group contains only this verifier and its MCP children.
                    try:
                        os.killpg(verifier.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        verifier.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        verifier.kill()
                        verifier.wait()
                    finally:
                        # A detached MCP child can outlive its verifier after timeout.
                        try:
                            os.killpg(verifier.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
            finally:
                for name in ('stdout.log', 'game.log', 'observation.png'):
                    source = self.work / name
                    if source.exists():
                        shutil.copy2(source, directory / name)
        if returncode:
            raise RuntimeError(f"{step['verifier']} exited {returncode}; see {directory / 'verifier.log'}")
        evidence = directory / 'evidence.json'
        if not evidence.is_file() or not json.loads(evidence.read_text()):
            raise RuntimeError(f'{step["verifier"]} exited without nonempty JSON evidence.')
        return {'returncode': returncode}

    def close(self):
        begin = time.monotonic()
        if self.game is not None and self.game.poll() is None:
            self.game.terminate()
            try:
                self.game.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.game.kill()
                self.game.wait()
        self.shutdown_seconds = time.monotonic() - begin

    def __exit__(self, *_):
        self.close()


def main():
    parser = argparse.ArgumentParser(description='一个隔离图形进程执行多个测试局；同局步骤须显式成组。')
    parser.add_argument('--suite', type=Path, default=ROOT / 'tests/game/data/gui_suite_smoke.json')
    parser.add_argument('--output', type=Path, required=True, help='新建的证据目录，不得已存在')
    parser.add_argument('--python', default=sys.executable, help='已安装 MCP 依赖的 Python')
    args = parser.parse_args()
    cases = load_cases(args.suite)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'suite.json').write_text(json.dumps(cases, indent=2) + '\n')
    try:
        with GameSession(output / 'game', args.python) as game:
            report = execute_cases(cases, game, output)
            report.update(startup_seconds=game.startup_seconds, process_starts=1, identity=game.initial_identity)
        report['shutdown_seconds'] = game.shutdown_seconds
        mod = ROOT / '.tmp/roundtrip/runtime/mods/Sts2Agent/Sts2Agent.dll'
        report['mod_sha256'] = hashlib.sha256(mod.read_bytes()).hexdigest()
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    except Exception as error:
        (output / 'startup-error.txt').write_text(f'{type(error).__name__}: {error}\n')
        raise
    print(f"{report['status']}: {len(report['cases'])} runs, one game process; {output / 'report.json'}")
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
