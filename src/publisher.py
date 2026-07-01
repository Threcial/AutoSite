import os
import json
from datetime import datetime

from src.config import Config
from src.wordpress_client import WordPressClient
from src.article_parser import parse_article, extract_local_images, replace_image_srcs, update_front_matter


class Publisher:
    def __init__(self, config: Config):
        self.config = config
        self.client = WordPressClient(
            base_url=config.base_url,
            username=config.username,
            app_password=config.app_password,
            verify_ssl=config.verify_ssl,
        )

    def publish(self, filepath, dry_run=False):
        result = {
            "success": False,
            "post_id": None,
            "slug": None,
            "link": None,
            "status": None,
            "error_code": None,
            "error_message": None,
            "http_status": None,
        }

        print(f"[INFO] Loading article: {filepath}")
        print(f"[INFO] WordPress: {self.config.base_url}")
        print(f"[INFO] Dry run: {'true' if dry_run else 'false'}")

        article = parse_article(filepath, self.config)
        if article is None:
            return result

        print(f"[INFO] Title: {article.title}")
        print(f"[INFO] HTML length: {len(article.content_html)} chars")

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

        # --- resolve taxonomies ---
        category_ids = []
        for cat_name in article.categories:
            cat_id = self.client.get_or_create_category(cat_name)
            if cat_id is None:
                return result
            print(f"[INFO] Category: {cat_name} -> ID {cat_id}")
            category_ids.append(cat_id)

        tag_ids = []
        for tag_name in article.tags:
            tag_id = self.client.get_or_create_tag(tag_name)
            if tag_id is None:
                return result
            print(f"[INFO] Tag: {tag_name} -> ID {tag_id}")
            tag_ids.append(tag_id)

        # --- dry-run ---
        if dry_run:
            result["success"] = True
            print(f"[INFO] Will create post (dry-run)")

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

            post_data = self._build_post_data(article, category_ids, tag_ids, featured_media_id)
            print("[INFO] Dry run — final request JSON:")
            print(json.dumps(post_data, ensure_ascii=False, indent=2))
            print("[INFO] Dry run complete. No post created.")
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

        post_data = self._build_post_data(article, category_ids, tag_ids, featured_media_id)
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

        # --- write slug + post info back to original file ---
        write_ok = self._write_back(filepath, result)
        result["write_back"] = write_ok
        if write_ok:
            print(f"[INFO] Slug/wp_post_id written back to: {filepath}")
        else:
            print(f"[WARN] Post created, but failed to write slug back to local file")
        return result

    def _write_back(self, filepath, result):
        fields = {
            "slug": result.get("slug"),
            "wp_post_id": result.get("post_id"),
            "wp_link": result.get("link"),
            "status": result.get("status"),
            "last_published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return update_front_matter(filepath, fields)

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
