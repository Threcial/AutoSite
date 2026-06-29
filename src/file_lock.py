import os
import json

LOCK_FILE = os.path.join("logs", "auto-submit.lock")


def acquire_lock():
    if os.path.isfile(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
        except Exception:
            data = ""
        pid = os.getpid()
        print(f"[ERROR] Lock file exists: {LOCK_FILE}")
        if data:
            print(f"[ERROR] Locked by PID {data}")
        print("[HINT]  If no other process is running, use --force-unlock to clear it")
        return False

    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except OSError as e:
        print(f"[ERROR] Cannot create lock file: {e}")
        return False


def release_lock():
    try:
        if os.path.isfile(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


def force_unlock():
    released = os.path.isfile(LOCK_FILE)
    try:
        if os.path.isfile(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass
    if released:
        print("[INFO] Lock file cleared")
    else:
        print("[INFO] No lock file to clear")
