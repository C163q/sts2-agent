import argparse
import json
import os
import time
import uuid
from pathlib import Path


from player_output import (
    CARD_VALUE_NOTE, ENEMY_ATTACK_INTENT_NOTE, player_result, share_hand_tips,
    share_indexed_tips, share_potion_tips,
)


class Client:
    def __init__(self, directory, timeout=40):
        self.directory = Path(directory)
        self.timeout = timeout

    def call(self, operation, expected_state=None, request_id=None, arguments=None):
        request_id = request_id or uuid.uuid4().hex
        if len(request_id) != 32 or uuid.UUID(hex=request_id).hex != request_id:
            raise ValueError("Request id must be a lowercase UUID hex string.")
        request = {"id": request_id, "operation": operation}
        if expected_state is not None:
            request["expected_state"] = expected_state
        if arguments is not None:
            request["arguments"] = arguments
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
    parser.add_argument("operation", choices=("travel_to_node", "get_state", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "inspect_map", "close_map", "close_card_view", "close_deck", "inspect_selection", "select_card", "selection_option", "set_selection_view", "start_test_combat", "end_turn", "inspect_targets", "play_card", "use_potion", "discard_potion", "inspect_rewards", "claim_reward", "proceed", "inspect_rest_site", "choose_rest_option", "loot_treasure", "inspect_treasure", "open_shop", "close_shop", "inspect_shop", "buy_item", "inspect_ancient", "choose_ancient_option", "advance_dialogue", "inspect_event", "choose_event_option", "set_divination_tool", "divine", "respond_to_confirmation"))
    parser.add_argument("--pile", choices=("draw", "discard", "exhaust"))
    parser.add_argument("--detail-level", choices=("summary", "full"))
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
    try:
        arguments = {key: getattr(args, key) for key in ("pile", "detail_level", "view_upgrades", "sort_by", "descending", "card_id", "potion_slot", "target_id", "option_id", "view", "reward_id", "open_only", "item_id", "tool", "x", "y", "option", "node_id")
                     if getattr(args, key) is not None}
        if args.operation in {'choose_ancient_option', 'choose_event_option'} and args.option_id is not None:
            arguments['option_id'] = int(args.option_id)
        if args.target_id is not None and args.target_id.isascii() and args.target_id.isdecimal():
            arguments["target_id"] = int(args.target_id)
        result = Client(args.ipc_dir).call(args.operation, args.expected_state, arguments=arguments or None)
        if not isinstance(result, dict) or type(result.get("ok")) is not bool:
            raise ValueError("Invalid game response.")
        payload = result if args.raw else player_result(result)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        code = "timeout" if isinstance(error, TimeoutError) else "transport_error"
        result = {"ok": False, "error": {"code": code, "message": str(error)}}
        payload = result if args.raw else player_result(result)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
