import argparse
import json
import os
import time
import uuid
from pathlib import Path


ENEMY_ATTACK_INTENT_NOTE = "Enemy attack intents already include current preview modifiers, including effects on you. Do not apply those modifiers again; the number is not guaranteed HP loss."
CARD_VALUE_NOTE = "Card values are contextual previews. Target-specific modifiers may apply only when aiming. Do not apply included modifiers again."


def share_hand_tips(hand):
    cards = []
    shared = {}
    for card in hand:
        cards.append({key: value for key, value in card.items() if key != "hover_tips"})
        for tip in card.get("hover_tips") or []:
            key = (tip.get("title"), tip["description"])
            if key not in shared:
                shared[key] = {"title": key[0], "description": key[1], "card_ids": []}
            if card["id"] not in shared[key]["card_ids"]:
                shared[key]["card_ids"].append(card["id"])
    return cards, list(shared.values())


def player_result(response):
    if response["ok"]:
        gameplay_fields = {"scene", "screen", "turn", "player", "enemies", "top_bar", "buttons", "available_actions", "hand", "hover_tips"}
        result = {key: value for key, value in response["state"].items() if key in gameplay_fields}
        if "hand" in result and result["hand"] is not None:
            result["hand"], result["hover_tips"] = share_hand_tips(result["hand"])
        notes = {}
        if result.get("hand"):
            notes["card_values"] = CARD_VALUE_NOTE
        if result.get("scene") == "combat" and any(
            enemy.get("intents") for enemy in result.get("enemies") or []
        ):
            notes["enemy_attack_intents"] = ENEMY_ATTACK_INTENT_NOTE
        if notes:
            result["notes"] = notes
        return result
    code = response["error"]["code"]
    messages = {
        "stale_state": ("The observation is outdated. Read the current state before choosing an action.", "get_state"),
        "illegal_action": ("The requested action is unavailable. Read the current state and choose a legal action.", "get_state"),
        "invalid_request": ("The request arguments are invalid. Correct them before submitting again.", "correct_request"),
        "expired_request": ("The request expired before execution. Read the current state before choosing an action.", "get_state"),
        "timeout": ("The request timed out; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"),
        "game_error": ("The game could not complete the request; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"),
        "transport_error": ("The local game connection failed. Check the connection before reading the current state.", "check_connection"),
    }
    message, recovery = messages.get(code, (
        "The request failed; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"))
    error = {"code": code, "message": message, "recovery": recovery}
    if code not in {"stale_state", "illegal_action", "invalid_request", "expired_request"}:
        error["outcome"] = "unknown"
    return {"error": error}


class Client:
    def __init__(self, directory, timeout=40):
        self.directory = Path(directory)
        self.timeout = timeout

    def call(self, operation, expected_state=None, request_id=None):
        request_id = request_id or uuid.uuid4().hex
        if len(request_id) != 32 or uuid.UUID(hex=request_id).hex != request_id:
            raise ValueError("Request id must be a lowercase UUID hex string.")
        request = {"id": request_id, "operation": operation}
        if expected_state is not None:
            request["expected_state"] = expected_state
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
    parser.add_argument("operation", choices=("get_state", "inspect_hand", "inspect_ui", "start_test_combat", "end_turn"))
    parser.add_argument("--expected-state")
    parser.add_argument("--raw", action="store_true", help="输出保留状态令牌等控制信息的原始响应")
    args = parser.parse_args()
    try:
        result = Client(args.ipc_dir).call(args.operation, args.expected_state)
    except TimeoutError as error:
        result = {"ok": False, "error": {"code": "timeout", "message": str(error)}}
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        result = {"ok": False, "error": {"code": "transport_error", "message": str(error)}}
    print(json.dumps(result if args.raw else player_result(result), indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
