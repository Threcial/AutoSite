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
    raw_front_matter: dict = field(default_factory=dict)


def parse_markdown_file(filepath):
    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        print(f"[ERROR] No Front Matter found in {filepath}")
        print("[HINT]  File must start with '---' followed by YAML front matter")
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"[ERROR] Invalid Front Matter in {filepath}")
        print("[HINT]  Format: ---\\nyour: fields\\n---\\n\\nBody text")
        return None

    yaml_block = parts[1]
    body_md = parts[2].strip()

    try:
        fm = yaml.safe_load(yaml_block)
    except yaml.YAMLError as e:
        print(f"[ERROR] Failed to parse YAML Front Matter: {e}")
        return None

    if not isinstance(fm, dict):
        print(f"[ERROR] Front Matter must be a YAML dictionary")
        return None

    title = fm.get("title", "").strip()
    if not title:
        print(f"[ERROR] 'title' is required in Front Matter")
        return None

    html = markdown_to_html(body_md)

    article = Article(
        title=title,
        content_html=html,
        status=fm.get("status", "draft"),
        slug=fm.get("slug"),
        categories=fm.get("categories", []),
        tags=fm.get("tags", []),
        author=fm.get("author"),
        excerpt=fm.get("excerpt"),
        cover=fm.get("cover"),
        raw_front_matter=fm,
    )

    return article


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


def extract_title_from_markdown(body_md, filename):
    m = re.search(r"^#\s+(.+)", body_md, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(filename))[0]


def parse_article_lenient(filepath, config):
    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return None, {}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    defaults_needed = {}
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

    if not fm.get("title"):
        title = extract_title_from_markdown(body_md, filepath)
        defaults_needed["title"] = title
    else:
        title = str(fm["title"]).strip()

    status = fm.get("status") or config.default_status
    author = fm.get("author") or config.default_author
    categories = fm.get("categories") or []
    tags = fm.get("tags") or []
    excerpt = fm.get("excerpt") or ""
    slug = fm.get("slug")
    cover = fm.get("cover")

    html = markdown_to_html(body_md)

    article = Article(
        title=title,
        content_html=html,
        status=status,
        slug=slug,
        categories=categories,
        tags=tags,
        author=author,
        excerpt=excerpt,
        cover=cover,
        raw_front_matter=fm,
    )

    return article, defaults_needed


def update_front_matter(filepath, fields):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return False

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False

    body = parts[2]

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return False

    if not isinstance(fm, dict):
        return False

    for k, v in fields.items():
        if v is not None:
            fm[k] = v

    new_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
    new_content = f"---\n{new_yaml}\n---{body}"

    tmp = filepath + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp, filepath)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False
