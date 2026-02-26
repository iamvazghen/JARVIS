import subprocess
import os
import re

def launch_app(path_of_app):
    try:
        subprocess.call([path_of_app])
        return True
    except Exception as e:
        print(e)
        return False


def _start_menu_shortcuts():
    dirs = []
    program_data = os.getenv("ProgramData")
    app_data = os.getenv("APPDATA")

    if program_data:
        dirs.append(os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs"))
    if app_data:
        dirs.append(os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs"))

    return [d for d in dirs if os.path.isdir(d)]


def _find_shortcut(app_name, max_results=10):
    app_name = (app_name or "").strip().lower()
    if not app_name:
        return []

    results = []
    for root in _start_menu_shortcuts():
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.lower().endswith(".lnk"):
                    continue
                stem = filename[:-4].lower()
                if app_name in stem:
                    results.append(os.path.join(dirpath, filename))
                    if len(results) >= max_results:
                        return results
    return results


def launch_app_by_name(app_name, new_window=False):
    """
    Launch an installed application by its common name. Best-effort:
    - Uses a small curated mapping for known apps (supports "new window" args)
    - Falls back to Start Menu .lnk shortcuts
    - Falls back to shell execution (start)
    """
    name = (app_name or "").strip()
    if not name:
        return False

    key = re.sub(r"\s+", " ", name).strip().lower()

    known = {
        "chrome": ("C:/Program Files/Google/Chrome/Application/chrome.exe", ["--new-window"] if new_window else []),
        "google chrome": ("C:/Program Files/Google/Chrome/Application/chrome.exe", ["--new-window"] if new_window else []),
        "edge": ("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", ["--new-window"] if new_window else []),
        "microsoft edge": ("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", ["--new-window"] if new_window else []),
        "notepad": ("notepad.exe", []),
        "calculator": ("calc.exe", []),
        "explorer": ("explorer.exe", []),
    }

    if key in known:
        exe, args = known[key]
        try:
            subprocess.Popen([exe] + list(args))
            return True
        except Exception as e:
            print(e)
            # fall through to other strategies

    # Start Menu shortcut fallback
    shortcuts = _find_shortcut(key)
    if shortcuts:
        try:
            os.startfile(shortcuts[0])
            return True
        except Exception as e:
            print(e)

    # Shell execution fallback (may work for registered app names)
    try:
        subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        return True
    except Exception as e:
        print(e)
        return False
