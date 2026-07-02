import os
import re
import yaml
from datetime import datetime

from .utils import atomic_write, backup_file

FM_DELIMITER = "---"
FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


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


def write_frontmatter(filepath, fm, body, backup=True):
    if backup:
        backup_file(filepath)
    new_content = build_frontmatter_yaml(fm) + "\n\n" + body.lstrip("\n")
    atomic_write(filepath, new_content)


def update_frontmatter_fields(filepath, fields, backup=True):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    fm, body = parse_frontmatter(content)
    for key, value in fields.items():
        if value is not None:
            fm[key] = value
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fm["last_uploaded_at"] = now
    write_frontmatter(filepath, fm, body, backup=backup)
