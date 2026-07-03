import os
import subprocess
import winreg


def _script_path(name):
    d = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(d, "scripts", name)


def install():
    script = _script_path("install_context_menu.ps1")
    if not os.path.isfile(script):
        return False, f"Script not found: {script}"
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
        capture_output=True, timeout=30,
    )
    if r.returncode == 0:
        return True, "右键菜单已安装"
    err = r.stderr.decode("utf-8", errors="replace") if r.stderr else "安装失败"
    return False, err.strip()


def uninstall():
    script = _script_path("uninstall_context_menu.ps1")
    if not os.path.isfile(script):
        return False, f"Script not found: {script}"
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
        capture_output=True, timeout=30,
    )
    if r.returncode == 0:
        return True, "右键菜单已卸载"
    err = r.stderr.decode("utf-8", errors="replace") if r.stderr else "卸载失败"
    return False, err.strip()


def is_installed():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\SystemFileAssociations\.md\shell\UploadToThrecial\command",
            0, winreg.KEY_READ,
        )
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
