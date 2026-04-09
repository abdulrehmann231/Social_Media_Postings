import json
import os

DEFAULT_LOG_PATH = "logs/captions.jsonl"


def append_caption_log(entry: dict, log_path: str = DEFAULT_LOG_PATH):
    """Append a caption entry as a JSON line to the log file."""
    os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else ".", exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_caption_log(log_path: str = DEFAULT_LOG_PATH) -> list[dict]:
    """Read all caption log entries."""
    if not os.path.exists(log_path):
        return []
    with open(log_path) as f:
        return [json.loads(line) for line in f if line.strip()]
