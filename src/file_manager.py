import os
import shutil

RAW_DIR = os.path.join("articles", "raw")
PUBLISHED_DIR = os.path.join("articles", "published")


def ensure_article_dirs():
    for d in (RAW_DIR, PUBLISHED_DIR, "assets", "logs"):
        os.makedirs(d, exist_ok=True)


def is_raw_article(filepath):
    norm = os.path.normpath(os.path.dirname(os.path.abspath(filepath)))
    return norm == os.path.normpath(os.path.abspath(RAW_DIR))


def is_published_article(filepath):
    norm = os.path.normpath(os.path.dirname(os.path.abspath(filepath)))
    return norm == os.path.normpath(os.path.abspath(PUBLISHED_DIR))


def determine_publish_action(filepath):
    if is_raw_article(filepath):
        return "create"
    if is_published_article(filepath):
        return "update"
    return "unknown"


def _resolve_name_conflict(target_dir, filename):
    name, ext = os.path.splitext(filename)
    candidate = os.path.join(target_dir, filename)
    if not os.path.exists(candidate):
        return candidate
    counter = 2
    while True:
        candidate = os.path.join(target_dir, f"{name}-{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def move_to_published(source_path):
    if not os.path.isfile(source_path):
        return None
    target = _resolve_name_conflict(PUBLISHED_DIR, os.path.basename(source_path))
    tmp = source_path + ".movetmp"
    try:
        shutil.copy2(source_path, tmp)
        os.replace(tmp, target)
        os.remove(source_path)
        return target
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        return None
