import os
import json
from datetime import datetime

from src.config import Config
from src.wordpress_client import WordPressClient
from src.article_parser import (
    parse_markdown_file,
    parse_article_lenient,
    extract_local_images,
    replace_image_srcs,
    update_front_matter,
)
from src.file_manager import determine_publish_action, move_to_published
from src.logger import append_publish_log


class Publisher:
    def __init__(self, config: Config):
        self.config = config
        self.client = WordPressClient(
            base_url=config.base_url,
            username=config.username,
            app_password=config.app_password,
            verify_ssl=config.verify_ssl,
        )

    def publish(self, filepath, dry_run=False, upsert=False, overrides=None, no_write_back=False, force_create=False):
        result = {
            "success": False,
            "post_id": None,
            "slug": None,
            "link": None,
            "status": None,
            "action": None,
            "error_code": None,
            "error_message": None,
            "http_status": None,
            "write_back": False,
            "source_before": filepath,
            "source_after": None,
            "defaults_applied": {},
        }

        print(f"[INFO] Loading article: {filepath}")
        print(f"[INFO] WordPress: {self.config.base_url}")
        print(f"[INFO] Dry run: {'true' if dry_run else 'false'}")

        action = determine_publish_action(filepath)
        if action == "unknown":
            action = "create" if not upsert else "update"
            print(f"[WARN] File not in articles/raw/ or articles/published/ — defaulting to {action}")

        result["action"] = action

        # --- parse article ---
        if action == "create":
            article, defaults = parse_article_lenient(filepath, self.config)
            if article is None:
                return result
            result["defaults_applied"] = defaults
            if defaults:
                for k, v in defaults.items():
                    print(f"[INFO] Auto-default {k}: {v}")
        else:
            article = parse_markdown_file(filepath)
            if article is None:
                return result

        if overrides:
            for key, value in overrides.items():
                if value is not None and hasattr(article, key):
                    setattr(article, key, value)
                    if key in ("categories", "tags"):
                        print(f"[INFO] Override {key}: {value}")

        print(f"[INFO] Title: {article.title}")
        print(f"[INFO] Action: {action}")
        print(f"[INFO] HTML length: {len(article.content_html)} chars")

        # --- raw article validation ---
        existing_post_id = None
        if action == "create":
            wp_pid = article.raw_front_matter.get("wp_post_id")
            if wp_pid is not None and not force_create:
                print(f"[ERROR] File has wp_post_id={wp_pid} — appears to be a published article")
                print("[HINT]  Move it to articles/published/ and run publish again")
                print("[HINT]  Or use --force-create to create as new article anyway")
                return result
        else:
            # published: find existing post_id
            wp_pid = article.raw_front_matter.get("wp_post_id")
            if wp_pid is not None:
                existing_post_id = int(wp_pid)
                print(f"[INFO] Using wp_post_id {existing_post_id} from Front Matter")
            elif article.slug:
                existing = self.client.get_post_by_slug(article.slug)
                if existing:
                    existing_post_id = existing["id"]
                    print(f"[INFO] Found post by slug '{article.slug}' — ID {existing_post_id}")
                else:
                    print(f"[ERROR] No WordPress post found for slug '{article.slug}'")
                    return result
            else:
                print("[ERROR] Published article has no wp_post_id or slug")
                print("[HINT]  Add wp_post_id or slug to Front Matter")
                print("[HINT]  Or move the file to articles/raw/ to create as new article")
                result["error_code"] = "missing_post_identity"
                result["error_message"] = "published article requires wp_post_id or slug"
                return result

        article_dir = os.path.dirname(os.path.abspath(filepath))

        # --- handle cover image ---
        featured_media_id = None
        cover_uploads = []
        if article.cover:
            cover_path = os.path.normpath(os.path.join(article_dir, article.cover))
            if os.path.isfile(cover_path):
                cover_uploads.append(("cover", article.cover, cover_path))
            elif article.cover.startswith(("http://", "https://", "//")):
                pass
            else:
                print(f"[ERROR] Cover image not found: {cover_path}")
                return result

        # --- handle body images ---
        body_images, soup = extract_local_images(article.content_html, article_dir)
        if body_images is None:
            return result

        # --- dry-run ---
        if dry_run:
            result["success"] = True
            print(f"[INFO] Will {action} post (dry-run)")

            if defaults:
                print(f"[INFO] Front Matter defaults to be applied on publish:")
                for k, v in defaults.items():
                    print(f"[INFO]   {k}: {v}")

            if article.cover:
                print(f"[INFO] Cover image: {article.cover}")
                if cover_uploads:
                    print(f"[INFO]   -> will be uploaded as featured_media")
            if body_images:
                print(f"[INFO] Local images found in body: {len(body_images)}")
                for orig_src, abs_path in body_images:
                    print(f"[INFO]   {orig_src} -> {abs_path}")
            if not cover_uploads and not body_images:
                print(f"[INFO] No local images to upload.")

            category_ids, tag_ids = self._resolve_taxonomies(article)
            if category_ids is None or tag_ids is None:
                return result

            post_data = self._build_post_data(article, category_ids, tag_ids, featured_media_id)
            print("[INFO] Dry run — final request JSON:")
            print(json.dumps(post_data, ensure_ascii=False, indent=2))
            print(f"[INFO] Dry run complete. No post {action}d.")

            append_publish_log({
                "source": filepath,
                "action": action,
                "success": True,
                "dry_run": True,
            })
            return result

        # --- real run: upload images ---
        if cover_uploads:
            for label, orig, abs_path in cover_uploads:
                upload_result = self.client.upload_media(abs_path)
                if upload_result is None:
                    return result
                featured_media_id = upload_result["id"]
                print(f"[INFO] Cover uploaded: {orig} -> media ID {featured_media_id}")

        src_map = {}
        if body_images:
            print(f"[INFO] Local images found: {len(body_images)}")
            uploaded_count = 0
            for orig_src, abs_path in body_images:
                upload_result = self.client.upload_media(abs_path)
                if upload_result is None:
                    return result
                src_map[orig_src] = upload_result["source_url"]
                uploaded_count += 1
                print(f"[INFO] Image uploaded: {orig_src} -> media ID {upload_result['id']}")
            article.content_html = replace_image_srcs(soup, src_map)
            print(f"[INFO] Images uploaded: {uploaded_count}")
            print(f"[INFO] HTML updated with remote image URLs")

        category_ids, tag_ids = self._resolve_taxonomies(article)
        if category_ids is None or tag_ids is None:
            return result

        post_data = self._build_post_data(article, category_ids, tag_ids, featured_media_id)

        # --- API call ---
        if existing_post_id:
            api_result = self.client.update_post(existing_post_id, post_data)
            if api_result is None:
                return result
            result["success"] = True
            result["post_id"] = api_result.get("id")
            result["slug"] = api_result.get("slug")
            result["link"] = api_result.get("link")
            result["status"] = api_result.get("status")
            print(f"[INFO] Post updated: ID {result['post_id']}")
        else:
            api_result = self.client.create_post(post_data)
            if api_result is None:
                return result
            result["success"] = True
            result["post_id"] = api_result.get("id")
            result["slug"] = api_result.get("slug")
            result["link"] = api_result.get("link")
            result["status"] = api_result.get("status")
            print(f"[INFO] Post created: ID {result['post_id']}")

        if result["link"]:
            print(f"[INFO] URL: {result['link']}")

        # --- write back Front Matter ---
        if not no_write_back:
            write_ok = self._write_back_markdown(filepath, result, action)
            result["write_back"] = write_ok
            if write_ok:
                print("[INFO] Local Markdown updated")
            else:
                print("[WARN] Post published, but failed to update local Markdown")
        else:
            print("[INFO] --no-write-back, local Markdown not modified")

        # --- move to published if create ---
        if result["success"] and action == "create":
            new_path = move_to_published(filepath)
            if new_path:
                result["source_after"] = new_path
                print(f"[INFO] File moved to: {new_path}")
            else:
                print("[WARN] Post created, but failed to move file to articles/published/")

        # --- log ---
        self._log_result(filepath, result, action, dry_run)
        return result

    def _write_back_markdown(self, filepath, result, action):
        fields = {
            "slug": result["slug"],
            "wp_post_id": result["post_id"],
            "wp_link": result["link"],
        }
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if action == "create":
            fields["last_published_at"] = now
        else:
            fields["last_updated_at"] = now
        if result["status"]:
            fields["status"] = result["status"]
        return update_front_matter(filepath, fields)

    def _log_result(self, filepath, result, action, dry_run):
        entry = {
            "action": action,
            "success": result["success"],
            "dry_run": dry_run,
        }
        if action == "create":
            entry["source_before"] = filepath
            if result.get("source_after"):
                entry["source_after"] = result["source_after"]
        else:
            entry["source"] = filepath

        if result["success"]:
            entry["post_id"] = result["post_id"]
            entry["slug"] = result["slug"]
            entry["link"] = result["link"]
            entry["status"] = result["status"]
            entry["write_back"] = result["write_back"]
        else:
            entry["error_code"] = result["error_code"]
            entry["error_message"] = result["error_message"]
            entry["http_status"] = result["http_status"]
        append_publish_log(entry)

    def _resolve_taxonomies(self, article):
        category_ids = []
        for cat_name in article.categories:
            cat_id = self.client.get_or_create_category(cat_name)
            if cat_id is None:
                return None, None
            print(f"[INFO] Category: {cat_name} -> ID {cat_id}")
            category_ids.append(cat_id)

        tag_ids = []
        for tag_name in article.tags:
            tag_id = self.client.get_or_create_tag(tag_name)
            if tag_id is None:
                return None, None
            print(f"[INFO] Tag: {tag_name} -> ID {tag_id}")
            tag_ids.append(tag_id)

        return category_ids, tag_ids

    def _build_post_data(self, article, category_ids, tag_ids, featured_media_id):
        post_data = {
            "title": article.title,
            "content": article.content_html,
            "status": article.status or self.config.default_status,
        }
        if category_ids:
            post_data["categories"] = category_ids
        if tag_ids:
            post_data["tags"] = tag_ids
        if article.author:
            post_data["author"] = article.author
        elif self.config.default_author:
            post_data["author"] = self.config.default_author
        if article.excerpt:
            post_data["excerpt"] = article.excerpt
        if article.slug:
            post_data["slug"] = article.slug
        if featured_media_id:
            post_data["featured_media"] = featured_media_id
        return post_data
