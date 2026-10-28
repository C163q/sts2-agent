import argparse
import json
import os
import time
import uuid
from pathlib import Path


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
    parser.add_argument("operation", choices=("get_state", "start_test_combat", "end_turn"))
    parser.add_argument("--expected-state")
    args = parser.parse_args()
    result = Client(args.ipc_dir).call(args.operation, args.expected_state)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
