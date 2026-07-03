import os
import sys
from datetime import datetime

from .config import Config
from .frontmatter import parse_frontmatter, standardize_frontmatter, update_frontmatter_fields
from .markdown_parser import md_to_html, extract_title, remove_first_h1
from .wordpress_client import WordPressClient
from .state import State
from .logger import Logger
from .notifier import notify_success, notify_failure


class Uploader:
    def __init__(self, config):
        self.config = config
        self.client = WordPressClient(
            base_url=config.base_url,
            api_base=config.api_base,
            username=config.username,
            app_password=config.application_password,
            verify_ssl=config.verify_ssl,
            timeout=config.timeout,
        )
        self.state = State(config.state_file)
        self.logger = Logger(config.history_file, config.latest_file)

    def upload(self, filepath, dry_run=False):
        filepath = os.path.abspath(filepath)

        if not os.path.isfile(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return 1

        if not filepath.lower().endswith(".md"):
            print(f"[ERROR] Not a .md file: {filepath}")
            return 1

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        fm, body = parse_frontmatter(content)

        title = fm.get("title") or extract_title(content, self.config) or os.path.splitext(os.path.basename(filepath))[0]

        if self.config.standardize_frontmatter:
            fm = standardize_frontmatter(fm, self.config, title=title)

        markdown_body = body
        if self.config.remove_first_h1_from_content and title and "title" not in fm:
            markdown_body = remove_first_h1(markdown_body)

        html_content = md_to_html(markdown_body, self.config.markdown_extensions) if self.config.convert_to_html else markdown_body

        action = self._determine_action(filepath, fm)

        if action["type"] == "create":
            return self._do_create(filepath, fm, html_content, title, dry_run)
        else:
            return self._do_update(filepath, fm, html_content, title, action, dry_run)

    def _determine_action(self, filepath, fm):
        order = self.config.update_detection_order

        for method in order:
            if method == "wp_post_id":
                wp_id = fm.get("wp_post_id")
                if wp_id:
                    print(f"[INFO] Found wp_post_id={wp_id}, will update")
                    return {"type": "update", "post_id": wp_id, "method": "wp_post_id"}

            elif method == "slug":
                slug = fm.get("slug")
                if slug:
                    result = self.client.get_post_by_slug(slug)
                    if result is None:
                        print(f"[WARN] Slug '{slug}' not found on remote, will create")
                    elif "error_code" in result:
                        print(f"[ERROR] Slug lookup failed: {result.get('http_status')} {result.get('error_code')} - {result.get('error_message')}")
                        sys.exit(1)
                    else:
                        print(f"[INFO] Found slug='{slug}', post_id={result['id']}, will update")
                        return {"type": "update", "post_id": result["id"], "method": "slug"}

            elif method == "state":
                post_id = self.state.get_post_id(filepath)
                if post_id:
                    print(f"[INFO] Found state record, post_id={post_id}, will update")
                    return {"type": "update", "post_id": post_id, "method": "state"}

            elif method == "title_exact_match":
                if self.config.title_match_enabled:
                    title = fm.get("title", "")
                    if title:
                        results = self.client.search_posts_by_title(title)
                        if results is None:
                            pass
                        elif isinstance(results, dict) and "error_code" in results:
                            print(f"[ERROR] Title search failed: {results.get('http_status')} {results.get('error_code')} - {results.get('error_message')}")
                            sys.exit(1)
                        elif len(results) == 1:
                            post = results[0]
                            if not self.config.title_match_strict or post.get("title", {}).get("rendered") == title:
                                print(f"[INFO] Title matched, post_id={post['id']}, will update")
                                return {"type": "update", "post_id": post["id"], "method": "title_match"}
                        elif len(results) > 1:
                            print(f"[ERROR] Title '{title}' matched {len(results)} posts, cannot auto-select. Add wp_post_id or slug to Front Matter.")
                            sys.exit(1)

        return {"type": "create", "method": "none"}

    def _handle_api_error(self, result, context, filepath, action):
        if result is None:
            self.logger.log_failure(action, filepath, "no_response", "No response from server", None)
            if self.config.notification_enabled and self.config.error_popup:
                notify_failure(filepath, "No Response", "no_response", "No response from server")
            return True
        if "error_code" in result:
            code = result.get("error_code", "unknown")
            msg = result.get("error_message", "")
            http = result.get("http_status")
            print(f"[ERROR] {context}: {http} {code} - {msg}")
            self.logger.log_failure(action, filepath, code, msg, http)
            if self.config.notification_enabled and self.config.error_popup:
                notify_failure(filepath, http or "API Error", code, msg)
            return True
        return False

    def _resolve_categories(self, fm):
        ids = []
        raw = fm.get("categories", [])
        if not raw:
            return ids
        names = raw if isinstance(raw, list) else [raw]
        for name in names:
            cid = self.client.get_or_create_category(name, auto_create=self.config.auto_create_categories)
            if cid is None:
                return None
            ids.append(cid)
        return ids

    def _resolve_tags(self, fm):
        ids = []
        raw = fm.get("tags", [])
        if not raw:
            return ids
        names = raw if isinstance(raw, list) else [raw]
        for name in names:
            tid = self.client.get_or_create_tag(name, auto_create=self.config.auto_create_tags)
            if tid is None:
                return None
            ids.append(tid)
        return ids

    def _build_payload(self, fm, title, html_content, category_ids, tag_ids):
        status = fm.get("status", self.config.default_status)
        if not self.config.allow_publish_status and status == "publish":
            print("[WARN] publish status blocked by config, downgraded to draft")
            status = "draft"

        payload = {
            "title": title,
            "content": html_content,
            "status": status,
        }

        if fm.get("author"):
            payload["author"] = fm["author"]

        if fm.get("excerpt"):
            payload["excerpt"] = fm["excerpt"]

        if category_ids is not None and len(category_ids) > 0:
            payload["categories"] = category_ids
        elif fm.get("categories") == []:
            payload["categories"] = []

        if tag_ids is not None and len(tag_ids) > 0:
            payload["tags"] = tag_ids
        elif fm.get("tags") == []:
            payload["tags"] = []

        if fm.get("slug") and fm.get("slug_update"):
            payload["slug"] = fm["slug"]

        if fm.get("date"):
            payload["date"] = fm["date"]

        return payload, status

    def _upload_images(self, filepath, html_content, dry_run):
        import re
        from bs4 import BeautifulSoup

        article_dir = os.path.dirname(os.path.abspath(filepath))
        soup = BeautifulSoup(html_content, "html.parser")
        imgs = soup.find_all("img")
        src_map = {}
        for img in imgs:
            src = img.get("src")
            if not src:
                continue
            if src.startswith(("http://", "https://", "//", "data:")):
                continue
            abs_path = os.path.normpath(os.path.join(article_dir, src))
            if not os.path.isfile(abs_path):
                print(f"[ERROR] Image not found: {abs_path}")
                return None
            if dry_run:
                print(f"[INFO]   Will upload: {src} -> {abs_path}")
                continue
            existing = self.state.get_media(abs_path)
            if existing:
                src_map[src] = existing["url"]
                print(f"[INFO]   Image already uploaded: {src} -> {existing['url']}")
                continue
            result = self.client.upload_media(abs_path)
            if result is None:
                print(f"[ERROR] Image upload failed: {src}")
                return None
            if "error_code" in result:
                print(f"[ERROR] Image upload failed: {src} - {result.get('http_status')} {result.get('error_code')} {result.get('error_message')}")
                return None
            src_map[src] = result["source_url"]
            self.state.set_media(abs_path, result["id"], result["source_url"])
            print(f"[INFO]   Image uploaded: {src} -> {result['source_url']}")
        if src_map:
            for img in imgs:
                src = img.get("src")
                if src in src_map:
                    img["src"] = src_map[src]
            return str(soup)
        return html_content

    def _upload_cover(self, fm, filepath, dry_run):

        cover = fm.get("cover")
        if not cover:
            return None
        if cover.startswith(("http://", "https://", "//")):
            return None
        article_dir = os.path.dirname(os.path.abspath(filepath))
        cover_path = os.path.normpath(os.path.join(article_dir, cover))
        if not os.path.isfile(cover_path):
            print(f"[ERROR] Cover image not found: {cover_path}")
            sys.exit(1)
        if dry_run:
            print(f"[INFO]   Will upload cover: {cover}")
            return None
        existing = self.state.get_media(cover_path)
        if existing:
            print(f"[INFO]   Cover already uploaded: {existing['url']}")
            return existing["media_id"]
        result = self.client.upload_media(cover_path)
        if result is None:
            print(f"[ERROR] Cover image upload failed: {cover}")
            sys.exit(1)
        if "error_code" in result:
            print(f"[ERROR] Cover image upload failed: {cover} - {result.get('http_status')} {result.get('error_code')} {result.get('error_message')}")
            sys.exit(1)
        self.state.set_media(cover_path, result["id"], result["source_url"])
        print(f"[INFO]   Cover uploaded: {result['source_url']}")
        return result["id"]

    def _do_create(self, filepath, fm, html_content, title, dry_run):

        if dry_run:
            category_names = fm.get("categories", [])
            tag_names = fm.get("tags", [])
            payload, status = self._build_payload(fm, title, html_content, None, None)
            print(f"\n[DRY-RUN] Would CREATE post")
            print(f"  Title: {title}")
            print(f"  Status: {status}")
            if category_names:
                print(f"  Categories: {category_names}")
            if tag_names:
                print(f"  Tags: {tag_names}")
            print(f"  Payload: {payload}")
            return 0

        category_ids = self._resolve_categories(fm)
        if category_ids is None:
            return 1

        tag_ids = self._resolve_tags(fm)
        if tag_ids is None:
            return 1

        final_html = self._upload_images(filepath, html_content, dry_run)
        if final_html is None:
            return 1

        featured_media_id = self._upload_cover(fm, filepath, dry_run)

        payload, status = self._build_payload(fm, title, final_html, category_ids, tag_ids)
        if featured_media_id:
            payload["featured_media"] = featured_media_id

        result = self.client.create_post(payload)
        if self._handle_api_error(result, "Create post", filepath, "create"):
            return 1

        post_id = result["id"]
        slug = result.get("slug", "")
        link = result.get("link", "")
        api_status = result.get("status", status)

        print(f"[INFO] Post created: ID={post_id}, slug={slug}")

        self._write_back(filepath, fm, post_id, slug, link, api_status, created=True)

        self.state.set_post(filepath, post_id, slug, link)
        self.logger.log_success("create", filepath, post_id, slug, link, api_status)

        action_label = "创建新文章"
        if self.config.notification_enabled and self.config.success_popup:
            notify_success(action_label, title, post_id, slug, api_status, link)

        return 0

    def _do_update(self, filepath, fm, html_content, title, action, dry_run):

        post_id = action["post_id"]

        if dry_run:
            category_names = fm.get("categories", [])
            tag_names = fm.get("tags", [])
            payload, status = self._build_payload(fm, title, html_content, None, None)
            print(f"\n[DRY-RUN] Would UPDATE post (ID={post_id})")
            print(f"  Title: {title}")
            print(f"  Status: {status}")
            if category_names:
                print(f"  Categories: {category_names}")
            if tag_names:
                print(f"  Tags: {tag_names}")
            print(f"  Payload: {payload}")
            return 0

        category_ids = self._resolve_categories(fm)
        if category_ids is None:
            return 1

        tag_ids = self._resolve_tags(fm)
        if tag_ids is None:
            return 1

        final_html = self._upload_images(filepath, html_content, dry_run)
        if final_html is None:
            return 1

        featured_media_id = self._upload_cover(fm, filepath, dry_run)

        payload, status = self._build_payload(fm, title, final_html, category_ids, tag_ids)
        if featured_media_id:
            payload["featured_media"] = featured_media_id

        result = self.client.update_post(post_id, payload)
        if self._handle_api_error(result, "Update post", filepath, "update"):
            return 1

        new_post_id = result["id"]
        slug = result.get("slug", "")
        link = result.get("link", "")
        api_status = result.get("status", status)

        print(f"[INFO] Post updated: ID={new_post_id}, slug={slug}")

        self._write_back(filepath, fm, new_post_id, slug, link, api_status, created=False)

        self.state.set_post(filepath, new_post_id, slug, link)
        self.logger.log_success("update", filepath, new_post_id, slug, link, api_status)

        action_label = "更新文章"
        if self.config.notification_enabled and self.config.success_popup:
            notify_success(action_label, title, new_post_id, slug, api_status, link)

        return 0

    def _write_back(self, filepath, fm, post_id, slug, link, status, created):
        if not self.config.write_back:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = {
            "wp_post_id": post_id,
            "slug": slug,
            "wp_link": link,
            "status": status,
            "last_uploaded_at": now,
        }
        if created:
            fields["last_published_at"] = now
        else:
            fields["last_updated_at"] = now
        update_frontmatter_fields(filepath, fields)
        print(f"[INFO] Front Matter updated in: {filepath}")
