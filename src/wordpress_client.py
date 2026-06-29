import os
import requests
from requests.auth import HTTPBasicAuth


class WordPressClient:
    def __init__(self, base_url, username, app_password, verify_ssl=True):
        self.api_base = f"{base_url}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(username, app_password)
        self.verify_ssl = verify_ssl
        self.timeout = 30

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.api_base}/{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify_ssl)
        kwargs.setdefault("auth", self.auth)
        return requests.request(method, url, **kwargs)

    def check_auth(self):
        resp = self._request("GET", "users/me")
        if resp.status_code == 200:
            data = resp.json()
            return data
        elif resp.status_code == 401:
            detail = resp.json().get("message", "No details provided.")
            print(f"[ERROR] WordPress API returned 401 Unauthorized")
            print(f"[ERROR] {detail}")
            print("[HINT]  Check WP_USERNAME and WP_APP_PASSWORD in .env")
            print("[HINT]  Ensure Nginx is forwarding the Authorization header")
            print("[HINT]  Some security plugins block REST API access")
            return None
        elif resp.status_code == 403:
            detail = resp.json().get("message", "No details provided.")
            print(f"[ERROR] WordPress API returned 403 Forbidden")
            print(f"[ERROR] {detail}")
            print("[HINT]  Current user does not have sufficient permissions")
            print("[HINT]  Use an Author, Editor, or Administrator account")
            return None
        else:
            print(f"[ERROR] WordPress API returned {resp.status_code}")
            print(f"[ERROR] {resp.text[:500]}")
            return None

    def get_post_by_slug(self, slug):
        resp = self._request("GET", f"posts?slug={slug}")
        if resp.status_code == 200:
            items = resp.json()
            if items:
                return items[0]
        return None

    def create_post(self, data):
        resp = self._request("POST", "posts", json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        self._handle_post_error(resp)
        return None

    def update_post(self, post_id, data):
        resp = self._request("POST", f"posts/{post_id}", json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        self._handle_post_error(resp)
        return None

    def _handle_post_error(self, resp):
        status = resp.status_code
        print(f"[ERROR] WordPress API returned {status}")
        try:
            wp_error = resp.json()
            code = wp_error.get("code", "")
            message = wp_error.get("message", "")
            if message:
                print(f"[ERROR] {message}")
            if code == "rest_cannot_create":
                print("[HINT]  Current user cannot create posts")
            elif code == "rest_cannot_publish":
                print("[HINT]  Current user can create drafts but cannot publish directly")
                print("[HINT]  Set status to 'draft' or use an Editor/Administrator account")
            elif status == 413:
                print("[HINT]  Post content or images too large")
                print("[HINT]  Check Nginx client_max_body_size")
            elif "memory" in message.lower():
                print("[HINT]  WordPress PHP memory exhausted")
                print("[HINT]  Check server PHP memory_limit, plugins, and themes")
            else:
                print(f"[HINT]  HTTP {status} — review WordPress error above")
        except ValueError:
            print(f"[ERROR] {resp.text[:500]}")

    def _search_taxonomy(self, taxonomy, name):
        resp = self._request("GET", f"{taxonomy}?search={name}")
        if resp.status_code != 200:
            return None
        items = resp.json()
        for item in items:
            if item["name"] == name:
                return item["id"]
        return None

    def _create_taxonomy(self, taxonomy, name):
        import json
        resp = self._request("POST", taxonomy, json={"name": name})
        if resp.status_code in (200, 201):
            return resp.json()["id"]
        print(f"[ERROR] Failed to create {taxonomy.rstrip('s')} '{name}': {resp.status_code}")
        print(f"[ERROR] {resp.text[:300]}")
        return None

    def get_or_create_category(self, name):
        cat_id = self._search_taxonomy("categories", name)
        if cat_id:
            return cat_id
        return self._create_taxonomy("categories", name)

    def get_or_create_tag(self, name):
        tag_id = self._search_taxonomy("tags", name)
        if tag_id:
            return tag_id
        return self._create_taxonomy("tags", name)

    def list_categories(self):
        resp = self._request("GET", "categories?per_page=100&orderby=name&order=asc")
        if resp.status_code == 200:
            return [(c["name"], c["id"]) for c in resp.json()]
        return []

    def list_tags(self):
        resp = self._request("GET", "tags?per_page=100&orderby=name&order=asc")
        if resp.status_code == 200:
            return [(t["name"], t["id"]) for t in resp.json()]
        return []

    def list_users(self):
        resp = self._request("GET", "users?per_page=100&orderby=name&order=asc")
        if resp.status_code == 200:
            return [(u["name"], u["id"]) for u in resp.json()]
        return []

    @staticmethod
    def _get_mime_type(filename):
        ext = filename.lower().split(".")[-1]
        mapping = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }
        return mapping.get(ext, "application/octet-stream")

    def upload_media(self, filepath):
        filename = os.path.basename(filepath)
        mime = self._get_mime_type(filename)
        try:
            with open(filepath, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            print(f"[ERROR] Image file not found: {filepath}")
            return None
        except IOError as e:
            print(f"[ERROR] Cannot read image file {filepath}: {e}")
            return None

        headers = {
            "Content-Disposition": f'attachment; filename={filename}',
            "Content-Type": mime,
        }
        resp = self._request("POST", "media", data=data, headers=headers)

        if resp.status_code in (200, 201):
            result = resp.json()
            return {
                "id": result["id"],
                "source_url": result.get("source_url", ""),
                "filename": filename,
            }

        print(f"[ERROR] Failed to upload image '{filename}': HTTP {resp.status_code}")
        try:
            msg = resp.json().get("message", "")
            if msg:
                print(f"[ERROR] {msg}")
        except ValueError:
            print(f"[ERROR] {resp.text[:300]}")
        if resp.status_code == 413:
            print("[HINT]  Image too large — check Nginx client_max_body_size")
        return None
