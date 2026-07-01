import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config
from src.wordpress_client import WordPressClient
from src.publisher import Publisher


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


def cmd_publish(config, filepath, dry_run):
    publisher = Publisher(config)
    result = publisher.publish(filepath, dry_run=dry_run)

    if dry_run:
        return 0

    if result["success"]:
        print(f"\n[SUCCESS] 文章发布成功")
        print(f"  文章 ID：{result['post_id']}")
        print(f"  Slug：{result['slug']}")
        print(f"  状态：{result['status']}")
        if result["link"]:
            print(f"  链接：{result['link']}")
        return 0

    if result["error_code"] or result["http_status"]:
        print(f"\n[ERROR] 发布失败")
        if result["error_code"]:
            print(f"  错误代码：{result['error_code']}")
        if result["error_message"]:
            print(f"  错误信息：{result['error_message']}")
        if result["http_status"]:
            print(f"  HTTP 状态：{result['http_status']}")
    return 1


def main():
    parser = argparse.ArgumentParser(description="AutoSite — WordPress publisher")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Check WordPress API connectivity and authentication")

    publish_parser = sub.add_parser("publish", help="Publish a Markdown article")
    publish_parser.add_argument("file", help="Path to the Markdown article file")
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
