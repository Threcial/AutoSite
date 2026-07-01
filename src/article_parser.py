import os
import re
import yaml
import markdown
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup


@dataclass
class Article:
    title: str
    content_html: str
    status: str = "draft"
    slug: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: Optional[int] = None
    excerpt: Optional[str] = None
    cover: Optional[str] = None


ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def markdown_to_html(md_text):
    extensions = [
        "extra",
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "sane_lists",
    ]
    html = markdown.markdown(md_text, extensions=extensions)
    return html.strip()


def extract_title_from_markdown(body_md, filename):
    m = re.search(r"^#\s+(.+)", body_md, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(filename))[0]


def extract_local_images(html, article_dir):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith(("http://", "https://", "//", "data:")):
            continue
        abs_path = os.path.normpath(os.path.join(article_dir, src))
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            print(f"[WARN] Unsupported image format, skipping: {src}")
            continue
        if not os.path.isfile(abs_path):
            print(f"[ERROR] Local image not found: {abs_path}")
            print("[HINT]  Check the path in your Markdown file")
            return None, None
        results.append((src, abs_path))
    return results, soup


def replace_image_srcs(soup, src_map):
    for img in soup.find_all("img"):
        old = img.get("src", "")
        if old in src_map:
            img["src"] = src_map[old]
    return str(soup)


def parse_article(filepath, config):
    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fm = {}
    body_md = content.strip()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
            except yaml.YAMLError:
                fm = {}
            if not isinstance(fm, dict):
                fm = {}
            body_md = parts[2].strip()

    if fm.get("title"):
        title = str(fm["title"]).strip()
    else:
        title = extract_title_from_markdown(body_md, filepath)
        print(f"[INFO] Auto-detected title: {title}")

    status = fm.get("status") or config.default_status
    author = fm.get("author") or config.default_author
    categories = fm.get("categories") or []
    tags = fm.get("tags") or []
    excerpt = fm.get("excerpt") or ""
    slug = fm.get("slug")
    cover = fm.get("cover")

    html = markdown_to_html(body_md)

    return Article(
        title=title,
        content_html=html,
        status=status,
        slug=slug,
        categories=categories,
        tags=tags,
        author=author,
        excerpt=excerpt,
        cover=cover,
    )
