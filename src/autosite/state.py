import os
import json
import shutil

from .utils import atomic_write


class State:
    def __init__(self, path):
        self.path = path
        self._data = self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            return {"files": {}, "media": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "files" in data and "media" in data:
                return data
            return {"files": {}, "media": {}}
        except (json.JSONDecodeError, ValueError):
            broken_path = self.path + ".broken"
            shutil.move(self.path, broken_path)
            print(f"[WARN] State file corrupted, backed up to {broken_path}")
            return {"files": {}, "media": {}}

    def save(self):
        dirpath = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(dirpath, exist_ok=True)
        atomic_write(self.path, json.dumps(self._data, ensure_ascii=False, indent=2))

    def get_post_id(self, filepath):
        norm = os.path.abspath(filepath).replace("\\", "/")
        entry = self._data["files"].get(norm)
        if entry:
            return entry.get("post_id")
        return None

    def set_post(self, filepath, post_id, slug, link):
        norm = os.path.abspath(filepath).replace("\\", "/")
        self._data["files"][norm] = {
            "post_id": post_id,
            "slug": slug,
            "link": link,
        }
        self.save()

    def get_media(self, filepath):
        norm = os.path.abspath(filepath).replace("\\", "/")
        return self._data["media"].get(norm)

    def set_media(self, filepath, media_id, url):
        norm = os.path.abspath(filepath).replace("\\", "/")
        self._data["media"][norm] = {
            "media_id": media_id,
            "url": url,
        }
        self.save()
