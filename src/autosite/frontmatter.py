import os
import re
import yaml
from datetime import datetime

from .utils import atomic_write, backup_file

FM_DELIMITER = "---"
FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

def _format_scalar(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    s = str(value)
    if not s or s.strip() != s or any(c in s for c in ":,#{}[]&*?|-<>!=%@`"):
        return yaml.dump(s, allow_unicode=True, default_style='"').strip()
    return s


def _update_fm_text_inplace(fm_text, fields):
    for key, value in fields.items():
        if value is None:
            continue
        encoded = _format_scalar(value)
        pat = re.compile(r'^' + re.escape(key) + r'\s*:.*?$', re.MULTILINE)
        line = f"{key}: {encoded}"
        if pat.search(fm_text):
            fm_text = pat.sub(line, fm_text)
        else:
            fm_text += "\n" + line
    return fm_text


def parse_frontmatter(content):
    match = FM_PATTERN.match(content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, content
    if not isinstance(fm, dict):
        fm = {}
    body = content[match.end():]
    return fm, body


def build_frontmatter_yaml(fm):
    lines = ["---"]
    for key in ["title", "slug", "wp_post_id", "wp_link", "status",
                "categories", "tags", "author", "excerpt", "cover",
                "date", "last_published_at", "last_updated_at", "last_uploaded_at"]:
        if key in fm:
            lines.append(yaml.dump({key: fm[key]},
                                   default_flow_style=False,
                                   allow_unicode=True,
                                   sort_keys=False).strip())
    for key, value in fm.items():
        if key not in ["title", "slug", "wp_post_id", "wp_link", "status",
                       "categories", "tags", "author", "excerpt", "cover",
                       "date", "last_published_at", "last_updated_at", "last_uploaded_at"]:
            lines.append(yaml.dump({key: value},
                                   default_flow_style=False,
                                   allow_unicode=True,
                                   sort_keys=False).strip())
    lines.append("---")
    return "\n".join(lines)


def standardize_frontmatter(fm, config, title=None):
    defaults = {
        "status": config.default_status,
        "author": config.default_author,
        "categories": list(config.default_categories),
        "tags": list(config.default_tags),
        "excerpt": config.default_excerpt,
    }
    result = {}
    for key in ["title", "slug", "wp_post_id", "wp_link", "status",
                "categories", "tags", "author", "excerpt", "cover",
                "date", "last_published_at", "last_updated_at", "last_uploaded_at"]:
        if key in fm and fm[key] is not None:
            result[key] = fm[key]
    if title:
        result["title"] = title
    for key, val in defaults.items():
        if key not in result:
            result[key] = val
    for key, value in fm.items():
        if key not in ["title", "slug", "wp_post_id", "wp_link", "status",
                       "categories", "tags", "author", "excerpt", "cover",
                       "date", "last_published_at", "last_updated_at", "last_uploaded_at"]:
            if key not in result:
                result[key] = value
    return result


def update_frontmatter_fields(filepath, fields):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = FM_PATTERN.match(content)
    if not match:
        return

    fm_text = match.group(1)
    body = content[match.end():]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields["last_uploaded_at"] = now

    fm_text = _update_fm_text_inplace(fm_text, fields)
    new_content = "---\n" + fm_text + "\n---" + body
    atomic_write(filepath, new_content)
