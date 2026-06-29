import os
import json
import hashlib

SYNC_STATE_FILE = os.path.join("logs", "sync-state.json")


def _hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def load_sync_state():
    if not os.path.isfile(SYNC_STATE_FILE):
        return {}
    try:
        with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_sync_state(state):
    os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
    with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_file_hash(filepath):
    if not os.path.isfile(filepath):
        return None
    return _hash_file(filepath)


def is_file_changed(filepath, state_entry):
    current = get_file_hash(filepath)
    if current is None:
        return False
    stored = (state_entry or {}).get("last_success_hash")
    return current != stored


def update_file_state(filepath, result, sync_state):
    fp = os.path.normpath(filepath)
    entry = sync_state.get(fp, {})
    entry["post_id"] = result.get("post_id")
    entry["slug"] = result.get("slug")
    entry["link"] = result.get("link")
    entry["last_success_hash"] = get_file_hash(filepath)
    entry["last_synced_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sync_state[fp] = entry


def remove_file_state(filepath, sync_state):
    fp = os.path.normpath(filepath)
    sync_state.pop(fp, None)
