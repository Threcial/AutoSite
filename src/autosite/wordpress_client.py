import os
import requests
from requests.auth import HTTPBasicAuth


class WordPressClient:
    def __init__(self, base_url, api_base, username, app_password, verify_ssl=True, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.api_base = api_base.rstrip("/")
        self.auth = HTTPBasicAuth(username, app_password)
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = verify_ssl

    def _url(self, path):
        return f"{self.api_base}/{path.lstrip('/')}"

    def _get(self, path, params=None):
        return self.session.get(self._url(path), params=params, timeout=self.timeout)

    def _post(self, path, json=None):
        return self.session.post(self._url(path), json=json, timeout=self.timeout)

    def check_auth(self):
        resp = self._get("users/me")
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_post_by_slug(self, slug):
        resp = self._get("posts", params={"slug": slug, "_fields": "id,slug,link,title,status"})
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
        return None

    def search_posts_by_title(self, title):
        resp = self._get("posts", params={"search": title, "_fields": "id,slug,link,title,status"})
        if resp.status_code == 200:
            return resp.json()
        return None

    def create_post(self, data):
        resp = self._post("posts", json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        return None

    def update_post(self, post_id, data):
        resp = self._post(f"posts/{post_id}", json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        return None

    def get_category_by_name(self, name):
        resp = self._get("categories", params={"search": name, "_fields": "id,name"})
        if resp.status_code == 200:
            data = resp.json()
            for cat in data:
                if cat.get("name") == name:
                    return cat
        return None

    def create_category(self, name):
        resp = self._post("categories", json={"name": name})
        if resp.status_code in (200, 201):
            return resp.json()
        return None

    def get_or_create_category(self, name, auto_create=False):
        existing = self.get_category_by_name(name)
        if existing:
            return existing["id"]
        if not auto_create:
            print(f"[ERROR] Category '{name}' not found and auto_create_categories is disabled")
            return None
        created = self.create_category(name)
        if created:
            print(f"[INFO] Created category: {name} (ID {created['id']})")
            return created["id"]
        return None

    def get_tag_by_name(self, name):
        resp = self._get("tags", params={"search": name, "_fields": "id,name"})
        if resp.status_code == 200:
            data = resp.json()
            for tag in data:
                if tag.get("name") == name:
                    return tag
        return None

    def create_tag(self, name):
        resp = self._post("tags", json={"name": name})
        if resp.status_code in (200, 201):
            return resp.json()
        return None

    def get_or_create_tag(self, name, auto_create=False):
        existing = self.get_tag_by_name(name)
        if existing:
            return existing["id"]
        if not auto_create:
            print(f"[ERROR] Tag '{name}' not found and auto_create_tags is disabled")
            return None
        created = self.create_tag(name)
        if created:
            print(f"[INFO] Created tag: {name} (ID {created['id']})")
            return created["id"]
        return None

    def upload_media(self, filepath):
        if not os.path.isfile(filepath):
            print(f"[ERROR] Media file not found: {filepath}")
            return None
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, self._guess_mime(filepath))}
            resp = self.session.post(
                self._url("media"),
                files=files,
                timeout=self.timeout,
            )
        if resp.status_code in (200, 201):
            return resp.json()
        return None

    @staticmethod
    def _guess_mime(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "application/octet-stream")
