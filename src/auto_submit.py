import os
import json
import glob
from datetime import datetime

from src.config import Config
from src.publisher import Publisher
from src.file_manager import ensure_article_dirs
from src.sync_state import load_sync_state, save_sync_state, get_file_hash, is_file_changed, update_file_state
from src.file_lock import acquire_lock, release_lock
from src.logger import append_publish_log


def _find_md_files(directory):
    files = glob.glob(os.path.join(directory, "**", "*.md"), recursive=True)
    files += glob.glob(os.path.join(directory, "*.md"), recursive=False)
    return sorted(set(files))


def _result_item(result):
    item = {
        "action": result.get("action", "unknown"),
        "success": result["success"],
    }
    if result.get("source_before"):
        item["source_before"] = result["source_before"]
    if result.get("source_after"):
        item["source_after"] = result["source_after"]
    if result.get("source"):
        item["source"] = result["source"]

    if result["success"]:
        item["post_id"] = result["post_id"]
        item["slug"] = result["slug"]
        item["link"] = result["link"]
    else:
        if result["error_code"]:
            item["error_code"] = result["error_code"]
        if result["error_message"]:
            item["error_message"] = result["error_message"]
        if result["http_status"]:
            item["http_status"] = result["http_status"]
    return item


def process_raw_articles(config, dry_run, fail_fast):
    publisher = Publisher(config)
    files = _find_md_files("articles/raw")
    results = []
    for fp in files:
        res = publisher.publish(fp, dry_run=dry_run, force_create=False)
        results.append((fp, res))
        if fail_fast and not res["success"]:
            break
    return results


def process_published_articles(config, dry_run, fail_fast, sync_state):
    publisher = Publisher(config)
    files = _find_md_files("articles/published")
    results = []
    for fp in files:
        se = sync_state.get(os.path.normpath(fp), {})
        changed = is_file_changed(fp, se)
        if not changed and se.get("last_success_hash"):
            results.append((fp, {"success": True, "action": "skip", "skip_reason": "unchanged"}))
            continue
        res = publisher.publish(fp, dry_run=dry_run, force_create=False)
        results.append((fp, res))
        if fail_fast and not res["success"]:
            break
    return results


def run_auto_submit(config, dry_run=False, fail_fast=False):
    ensure_article_dirs()

    if not dry_run:
        if not acquire_lock():
            return None

    sync_state = load_sync_state()

    raw_results = process_raw_articles(config, dry_run, fail_fast)
    pub_results = process_published_articles(config, dry_run, fail_fast, sync_state)

    # Build report
    raw_ok = sum(1 for _, r in raw_results if r["success"])
    raw_fail = sum(1 for _, r in raw_results if not r["success"])
    pub_ok = sum(1 for _, r in pub_results if r["success"] and r.get("action") == "update")
    pub_skip = sum(1 for _, r in pub_results if r.get("action") == "skip")
    pub_fail = sum(1 for _, r in pub_results if not r["success"] and r.get("action") != "skip")

    items = []
    for fp, res in raw_results:
        items.append(_result_item(res))
    for fp, res in pub_results:
        items.append(_result_item(res))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "time": now,
        "dry_run": dry_run,
        "summary": {
            "raw_total": len(raw_results),
            "raw_success": raw_ok,
            "raw_failed": raw_fail,
            "published_total": len(pub_results),
            "published_updated": pub_ok,
            "published_skipped": pub_skip,
            "published_failed": pub_fail,
        },
        "items": items,
    }

    # Print report
    print()
    print("=" * 60)
    print("Auto Submit Finished")
    print("=" * 60)
    print()
    print("Raw create:")
    print(f"  Success: {raw_ok}")
    print(f"  Failed : {raw_fail}")
    print()
    print("Published update:")
    print(f"  Updated: {pub_ok}")
    print(f"  Skipped: {pub_skip}")
    print(f"  Failed : {pub_fail}")
    print()
    print("Details:")
    for fp, res in raw_results:
        _print_item(fp, res)
    for fp, res in pub_results:
        _print_item(fp, res)
    print()

    # Save sync state
    if not dry_run:
        for fp, res in raw_results:
            if res["success"]:
                new_path = res.get("source_after")
                if new_path and os.path.isfile(new_path):
                    update_file_state(new_path, res, sync_state)
                elif os.path.isfile(fp):
                    update_file_state(fp, res, sync_state)
        for fp, res in pub_results:
            if res["success"] and res.get("action") == "update":
                update_file_state(fp, res, sync_state)
        save_sync_state(sync_state)

        # Save report file
        report_path = os.path.join("logs", "auto-submit-report.json")
        os.makedirs("logs", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Also append each item to publish-history.jsonl
        for item in items:
            entry = dict(item)
            entry["time"] = now
            append_publish_log(entry)

    if not dry_run:
        release_lock()

    return report


def _print_item(fp, res):
    if res.get("action") == "skip":
        print(f"  [SKIP] {fp} | {res.get('skip_reason', '')}")
    elif res["success"]:
        if res.get("action") == "create":
            after = res.get("source_after", "?")
            print(f"  [CREATE OK] {fp} -> {after} | ID {res.get('post_id')} | slug {res.get('slug')}")
        else:
            print(f"  [UPDATE OK] {fp} | ID {res.get('post_id')} | slug {res.get('slug')}")
    else:
        err = res.get("error_code", res.get("http_status", "unknown"))
        print(f"  [FAIL] {fp} | {err}")
