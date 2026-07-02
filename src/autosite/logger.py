import os
import json
from datetime import datetime

from .utils import atomic_write


class Logger:
    def __init__(self, history_file, latest_file):
        self.history_file = history_file
        self.latest_file = latest_file
        self._ensure_dir(history_file)
        self._ensure_dir(latest_file)

    def _ensure_dir(self, filepath):
        dirpath = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(dirpath, exist_ok=True)

    def log(self, entry):
        entry["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe = {}
        for k, v in entry.items():
            if k in ("application_password", "authorization", "Authorization"):
                continue
            safe[k] = v
        line = json.dumps(safe, ensure_ascii=False)
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        atomic_write(self.latest_file, json.dumps(safe, ensure_ascii=False, indent=2))

    def log_success(self, action, filepath, post_id, slug, link, status):
        self.log({
            "action": action,
            "success": True,
            "source": filepath,
            "post_id": post_id,
            "slug": slug,
            "link": link,
            "status": status,
        })

    def log_failure(self, action, filepath, error_code, error_message, http_status):
        self.log({
            "action": action,
            "success": False,
            "source": filepath,
            "error_code": error_code,
            "error_message": error_message,
            "http_status": http_status,
        })
