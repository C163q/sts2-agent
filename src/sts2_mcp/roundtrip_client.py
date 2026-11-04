from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.tool_registry import NATIVE_TOOLS
from sts2_mcp.request_arguments import normalize_request
import argparse
import json
import os
import time
import uuid
from pathlib import Path


from sts2_mcp.output.player_output import (
    CARD_VALUE_NOTE, ENEMY_ATTACK_INTENT_NOTE, player_result, share_hand_tips,
    share_indexed_tips, share_potion_tips,
)


class Client:
    def __init__(self, directory, timeout=40):
        self.directory = Path(directory)
        self.timeout = timeout

    def call(self, operation, expected_state=None, request_id=None, arguments=None, *, response_options=None):
        request_id = request_id or uuid.uuid4().hex
        if len(request_id) != 32 or uuid.UUID(hex=request_id).hex != request_id:
            raise ValueError("Request id must be a lowercase UUID hex string.")
        request = {"id": request_id, "operation": operation}
        if expected_state is not None:
            request["expected_state"] = expected_state
        if arguments is not None:
            request["arguments"] = arguments
        if response_options is not None:
            request["response_options"] = response_options
        requests = self.directory / "requests"
        responses = self.directory / "responses"
        requests.mkdir(parents=True, exist_ok=True)
        responses.mkdir(parents=True, exist_ok=True)
        target = requests / (request_id + ".json")
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(request))
        os.replace(temporary, target)
        deadline = time.monotonic() + self.timeout
        response = responses / target.name
        while time.monotonic() < deadline:
            if response.exists():
                result = json.loads(response.read_text())
                if result["id"] != request_id:
                    raise RuntimeError("Response id mismatch.")
                return result
            time.sleep(0.025)
        raise TimeoutError(f"No response to {operation}; execution outcome unknown, do not retry automatically.")


def main():
    parser = argparse.ArgumentParser(description="调用最小验证原型的文件工具接口。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("operation", choices=tuple(name for name in NATIVE_TOOLS if name != 'capture_screenshot') + ('close_deck', 'start_test_combat'))
    parser.add_argument("--pile", choices=("draw", "discard", "exhaust"))
    parser.add_argument("--preset", choices=("default", "full", "summary"), help="牌组／牌堆默认 default；战斗对象／药水默认 full")
    parser.add_argument("--slot-indices", nargs="*", type=int, help="药水的原始槽位；省略取全部，空列表不取槽位")
    parser.add_argument('--card-ids', nargs='*', help='牌组 deck:N 或战斗牌堆 pile:N 实例 ID；省略取全部，空列表不取卡牌')
    parser.add_argument("--sources", nargs="*", help="战斗对象来源路径；省略取全部，空列表不取对象")
    parser.add_argument("--view-upgrades", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--sort-by", choices=("obtained", "type", "cost", "name"))
    direction = parser.add_mutually_exclusive_group()
    direction.add_argument("--descending", dest="descending", action="store_const", const=True, default=None)
    direction.add_argument("--ascending", dest="descending", action="store_const", const=False)
    parser.add_argument("--expected-state")
    parser.add_argument("--card-id", type=int)
    parser.add_argument("--potion-slot", type=int)
    parser.add_argument("--target-id", help="战斗生物整数 ID，或药水特殊目标 merchant")
    parser.add_argument("--reward-id", type=int)
    parser.add_argument("--node-id")
    parser.add_argument("--item-id", type=int)
    parser.add_argument("--open-only", action="store_true", default=None)
    parser.add_argument("--option-id")
    parser.add_argument("--view", choices=("battlefield", "selection"))
    parser.add_argument("--option", choices=("confirm", "cancel"))
    parser.add_argument("--tool", choices=("big", "small"))
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--raw", action="store_true", help="输出保留状态令牌等控制信息的原始响应")
    args = parser.parse_args()
    request_sent = False
    try:
        arguments = {key: getattr(args, key) for key in ("pile", "view_upgrades", "sort_by", "descending", "card_id", "potion_slot", "target_id", "option_id", "view", "reward_id", "open_only", "item_id", "tool", "x", "y", "option", "node_id")
                     if getattr(args, key) is not None}
        if args.operation in {'choose_ancient_option', 'choose_event_option'} and args.option_id is not None:
            arguments['option_id'] = int(args.option_id)
        if args.target_id is not None and args.target_id.isascii() and args.target_id.isdecimal():
            arguments["target_id"] = int(args.target_id)
        browsing = args.operation in {'inspect_deck', 'inspect_pile'}
        closing = args.operation == 'close_card_view'
        combatants = args.operation == 'inspect_combatants'
        potions = args.operation == 'inspect_potions'
        if args.preset is not None and not (browsing or closing or combatants or potions):
            raise ValueError('--preset is supported for inspect_deck, inspect_pile, close_card_view, inspect_combatants and inspect_potions.')
        if args.card_ids is not None:
            if not browsing:
                raise ValueError('--card-ids is supported for inspect_deck and inspect_pile.')
            arguments['card_ids'] = args.card_ids
        if args.sources is not None and not combatants:
            raise ValueError('--sources is supported for inspect_combatants.')
        if args.slot_indices is not None and not potions:
            raise ValueError('--slot-indices is supported for inspect_potions.')
        if potions:
            if arguments:
                raise ValueError('inspect_potions accepts only --preset and --slot-indices.')
            normalized = normalize_request(NATIVE_TOOLS[args.operation], {
                'preset': args.preset or 'full', **({'slot_indices': args.slot_indices} if args.slot_indices is not None else {})})
            arguments = normalized.native_arguments
        if combatants:
            if arguments:
                raise ValueError('inspect_combatants accepts only --preset and --sources.')
            normalized = normalize_request(NATIVE_TOOLS[args.operation], {
                'preset': args.preset or 'full', **({'sources': args.sources} if args.sources is not None else {})})
            settings = normalized.output_arguments
            arguments = normalized.native_arguments
        if browsing or closing:
            normalized = normalize_request(NATIVE_TOOLS[args.operation], {**arguments, 'preset': args.preset or 'default'})
            arguments = normalized.native_arguments
        request_sent = True
        request_options = {'response_options': {'include_divination_image': False}} if closing and not args.raw else {}
        result = Client(args.ipc_dir).call(args.operation, args.expected_state, arguments=arguments or None, **request_options)
        if not isinstance(result, dict) or type(result.get("ok")) is not bool:
            raise ValueError("Invalid game response.")
        if potions and result['ok'] and not args.raw:
            payload = normalized.project(decode_success(args.operation, result['state'], arguments, include_observation=True))
        elif combatants and result['ok'] and not args.raw:
            from sts2_mcp.output.combatant_presets import combatant_preset
            from sts2_mcp.output.presets import apply_preset
            payload = decode_success(args.operation, result['state'], arguments, include_observation=True)
            payload = combatant_preset(payload, **settings)
            payload = apply_preset(payload, 'default' if args.preset == 'default' or settings['preset'] == 'summary' else 'full')
        elif (browsing or closing) and result['ok'] and not args.raw:
            payload = normalized.project(decode_success(args.operation, result['state'], arguments, include_observation=True))
        else:
            payload = result if args.raw else (
                decode_success(args.operation, result['state'], arguments, include_observation=True)
                if result['ok'] else player_result(result, operation=args.operation, arguments=arguments))
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        local_argument_error = args.operation in {'inspect_deck', 'inspect_pile', 'close_card_view', 'inspect_combatants', 'inspect_potions'} and not request_sent and isinstance(error, ValueError)
        code = 'invalid_request' if local_argument_error else 'timeout' if isinstance(error, TimeoutError) else 'transport_error'
        result = {"ok": False, "error": {"code": code, "message": str(error)}}
        if local_argument_error: result['error']['public_message'] = str(error)
        payload = result if args.raw else player_result(result)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
