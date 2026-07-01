import sys
import os
import glob
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config
from src.wordpress_client import WordPressClient
from src.publisher import Publisher


def find_md_files(path):
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "**", "*.md"), recursive=True)
        files += glob.glob(os.path.join(path, "*.md"))
        return sorted(set(files))
    matched = glob.glob(path, recursive=True)
    return sorted(matched) if matched else []


def cmd_check(config):
    print(f"[INFO] WordPress: {config.base_url}")
    print(f"[INFO] Checking authentication...")

    client = WordPressClient(
        base_url=config.base_url,
        username=config.username,
        app_password=config.app_password,
        verify_ssl=config.verify_ssl,
    )

    user = client.check_auth()
    if user is None:
        return 1

    print(f"[INFO] Authentication successful")
    print(f"[INFO] User ID:   {user.get('id')}")
    print(f"[INFO] Username:  {user.get('slug', user.get('name'))}")
    print(f"[INFO] Display:   {user.get('name')}")
    roles = ", ".join(user.get("roles", []))
    print(f"[INFO] Roles:     {roles}")
    return 0


def publish_one(publisher, filepath, dry_run):
    result = publisher.publish(filepath, dry_run=dry_run)

    name = os.path.basename(filepath)
    if dry_run:
        if result["success"]:
            print(f"  [DRY-RUN] {name} — OK")
        else:
            print(f"  [DRY-RUN] {name} — FAIL")
        return 0 if result["success"] else 1

    if result["success"]:
        wb = "✓" if result.get("write_back") else "✗"
        print(f"  [CREATE OK] {name} | ID {result['post_id']} | slug {result['slug']} | write-back {wb}")
        return 0
    else:
        err = result.get("error_code") or result.get("http_status") or "unknown"
        print(f"  [FAIL] {name} | {err}")
        return 1


def cmd_publish(config, path, dry_run):
    files = find_md_files(path)
    if not files:
        print(f"[ERROR] No markdown files found: {path}")
        return 1

    print(f"[INFO] Found {len(files)} file(s)")
    print()

    publisher = Publisher(config)
    success_count = 0
    fail_count = 0

    for fp in files:
        rc = publish_one(publisher, fp, dry_run)
        if rc == 0:
            success_count += 1
        else:
            fail_count += 1

    print()
    if dry_run:
        print(f"[INFO] Dry-run complete: {success_count} OK, {fail_count} FAIL")
        return 0

    print(f"[INFO] Done: {success_count} success, {fail_count} failed")
    return 1 if fail_count > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="AutoSite — WordPress publisher")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Check WordPress API connectivity and authentication")

    publish_parser = sub.add_parser("publish", help="Publish Markdown articles")
    publish_parser.add_argument("file", help="File path, directory, or glob pattern")
    publish_parser.add_argument("--dry-run", action="store_true", help="Preview without publishing")

    args = parser.parse_args()

    if args.command == "check":
        config = Config()
        if not config.validate():
            return 1
        return cmd_check(config)

    if args.command == "publish":
        config = Config()
        if not config.validate():
            return 1
        return cmd_publish(config, args.file, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
