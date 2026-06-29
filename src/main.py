import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config
from src.wordpress_client import WordPressClient
from src.publisher import Publisher
from src.file_manager import ensure_article_dirs
from src.auto_submit import run_auto_submit
from src.file_lock import force_unlock


def cmd_init_dirs():
    ensure_article_dirs()
    print("[INFO] Created directories:")
    print("       articles/raw/")
    print("       articles/published/")
    print("       assets/")
    print("       logs/")
    return 0


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


def cmd_publish(config, filepath, dry_run, upsert, no_write_back, force_create):
    publisher = Publisher(config)
    result = publisher.publish(
        filepath,
        dry_run=dry_run,
        upsert=upsert,
        no_write_back=no_write_back,
        force_create=force_create,
    )

    if dry_run:
        return 0
    if result["success"]:
        print(f"\n[SUCCESS] 文章发布成功")
        print(f"  文章 ID：{result['post_id']}")
        print(f"  Slug：{result['slug']}")
        print(f"  状态：{result['status']}")
        print(f"  链接：{result['link']}")
        if result["write_back"]:
            print(f"  [INFO] 已写回本地 Markdown")
        else:
            print(f"  [INFO] 未写回本地 Markdown")
        if result.get("source_after"):
            print(f"  [INFO] 文件已移至：{result['source_after']}")
        return 0
    else:
        if result["error_code"] or result["http_status"]:
            print(f"\n[ERROR] 发布失败")
            if result["error_code"]:
                print(f"  错误代码：{result['error_code']}")
            if result["error_message"]:
                print(f"  错误信息：{result['error_message']}")
            if result["http_status"]:
                print(f"  HTTP 状态：{result['http_status']}")
        return 1


def cmd_auto_submit(config, dry_run, fail_fast):
    report = run_auto_submit(config, dry_run=dry_run, fail_fast=fail_fast)
    if report is None:
        return 1
    total_fail = report["summary"]["raw_failed"] + report["summary"]["published_failed"]
    return 1 if total_fail > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="AutoSite — WordPress publisher")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-dirs", help="Create required directories")
    sub.add_parser("check", help="Check WordPress API connectivity and authentication")

    publish_parser = sub.add_parser("publish", help="Publish a Markdown article")
    publish_parser.add_argument("file", help="Path to the Markdown article file")
    publish_parser.add_argument("--dry-run", action="store_true", help="Preview without publishing")
    publish_parser.add_argument("--upsert", action="store_true", help="(deprecated) Directory now determines create/update")
    publish_parser.add_argument("--no-write-back", action="store_true", help="Skip writing slug/post_id back to local Markdown")
    publish_parser.add_argument("--force-create", action="store_true", help="Force create even if wp_post_id exists (raw only)")

    auto_parser = sub.add_parser("auto-submit", help="Auto-submit all articles in raw/ and published/")
    auto_parser.add_argument("--dry-run", action="store_true", help="Preview without publishing")
    auto_parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    auto_parser.add_argument("--force-unlock", action="store_true", help="Clear lock file before starting")

    args = parser.parse_args()

    if args.command == "init-dirs":
        return cmd_init_dirs()

    config = Config()
    if not config.validate():
        return 1

    if args.command == "check":
        return cmd_check(config)
    elif args.command == "publish":
        return cmd_publish(
            config,
            args.file,
            dry_run=args.dry_run,
            upsert=args.upsert,
            no_write_back=args.no_write_back,
            force_create=args.force_create,
        )
    elif args.command == "auto-submit":
        if args.force_unlock:
            force_unlock()
            return 0
        return cmd_auto_submit(config, dry_run=args.dry_run, fail_fast=args.fail_fast)

    return 0


if __name__ == "__main__":
    sys.exit(main())
