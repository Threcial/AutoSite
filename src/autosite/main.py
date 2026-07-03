import sys
import subprocess
import os

from .config import Config
from .wordpress_client import WordPressClient
from .uploader import Uploader


def cmd_gui():
    from .gui import main as gui_main
    gui_main()


def cmd_check(config):
    print(f"[INFO] WordPress: {config.base_url}")
    print(f"[INFO] Checking connection and authentication...")

    client = WordPressClient(
        base_url=config.base_url,
        api_base=config.api_base,
        username=config.username,
        app_password=config.application_password,
        verify_ssl=config.verify_ssl,
        timeout=config.timeout,
    )

    result = client.check_auth()
    if result is None:
        print(f"[ERROR] Authentication failed (no response)")
        print(f"[HINT]  Check network and config.yaml: base_url")
        return 1

    if "error_code" in result:
        print(f"[ERROR] Authentication failed: {result.get('http_status')} {result.get('error_code')}")
        print(f"       {result.get('error_message')}")
        print(f"[HINT]  Check config.yaml: username / application_password")
        return 1

    print(f"[INFO] Authentication successful")
    print(f"[INFO] User ID:   {result.get('id')}")
    print(f"[INFO] Username:  {result.get('slug', result.get('name'))}")
    print(f"[INFO] Display:   {result.get('name')}")
    print(f"[INFO] Site URL:  {config.base_url}")
    return 0


def cmd_upload(config, filepath, dry_run):
    uploader = Uploader(config)
    return uploader.upload(filepath, dry_run=dry_run)


def cmd_install_context_menu():
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "install_context_menu.ps1")
    if not os.path.isfile(script):
        print(f"[ERROR] Script not found: {script}")
        return 1
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
                            capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode


def cmd_uninstall_context_menu():
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "uninstall_context_menu.ps1")
    if not os.path.isfile(script):
        print(f"[ERROR] Script not found: {script}")
        return 1
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
                            capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m autosite check")
        print("  python -m autosite upload <filepath> [--dry-run]")
        print("  python -m autosite install-context-menu")
        print("  python -m autosite uninstall-context-menu")
        return 1

    command = sys.argv[1]

    if command == "gui":
        return cmd_gui()

    if command in ("install-context-menu",):
        return cmd_install_context_menu()

    if command in ("uninstall-context-menu",):
        return cmd_uninstall_context_menu()

    config = Config()

    if command == "check":
        return cmd_check(config)

    if command == "upload":
        if len(sys.argv) < 3:
            print("[ERROR] Missing file path argument")
            print("Usage: python -m autosite upload <filepath> [--dry-run]")
            return 1
        filepath = sys.argv[2]
        dry_run = "--dry-run" in sys.argv
        return cmd_upload(config, filepath, dry_run)

    print(f"[ERROR] Unknown command: {command}")
    print("Available commands: check, upload, install-context-menu, uninstall-context-menu, gui")
    return 1


if __name__ == "__main__":
    sys.exit(main())
