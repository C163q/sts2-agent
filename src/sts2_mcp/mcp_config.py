import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "mcp-config.json"


@dataclass(frozen=True)
class Settings:
    screenshot_directory: Path | None = None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = value
    return result


def load_config(path=None, *, default_path=DEFAULT_CONFIG):
    selected = Path(path if path is not None else default_path).expanduser().resolve()
    try:
        text = selected.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        if path is None:
            return Settings()
        raise ValueError(f"Configuration file does not exist: {selected}") from error
    except OSError as error:
        raise ValueError(f"Cannot read configuration: {selected}") from error
    try:
        config = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(config, dict) or config.keys() - {"screenshots"}:
            raise ValueError("Expected only the screenshots configuration section.")
        screenshots = config.get("screenshots", {})
        if not isinstance(screenshots, dict) or screenshots.keys() - {"enabled", "directory"}:
            raise ValueError("Expected screenshots.enabled and screenshots.directory.")
        enabled = screenshots.get("enabled", False)
        if type(enabled) is not bool:
            raise ValueError("screenshots.enabled must be a boolean.")
        directory = screenshots.get("directory")
        if "directory" in screenshots and (not isinstance(directory, str) or not directory.strip() or "\0" in directory):
            raise ValueError("screenshots.directory must be a nonempty path.")
        if not enabled:
            return Settings()
        if directory is None:
            raise ValueError("screenshots.directory is required when screenshots are enabled.")
        destination = Path(directory).expanduser()
        if not destination.is_absolute():
            destination = selected.parent / destination
        return Settings(destination.resolve())
    except (ValueError, RuntimeError) as error:
        raise ValueError(f"Invalid configuration {selected}: {error}") from error
