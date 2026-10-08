"""Windows shell integration: desktop/Start Menu shortcuts and start-with-Windows."""
import os
import subprocess
import sys
from pathlib import Path

from .paths import APP_NAME, ICON_ICO, ROOT

APP_ID = "Murmur.Dictation"
DESKTOP = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
START_MENU = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
STARTUP = START_MENU / "Startup"


def _pythonw() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def _desktop_dir() -> Path:
    # OneDrive often redirects the Desktop; ask the shell for the real one.
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout.strip()
        if out:
            return Path(out)
    except (OSError, subprocess.SubprocessError):
        pass
    return DESKTOP


def create_shortcut(link: Path, args: str = "-m murmur"):
    link.parent.mkdir(parents=True, exist_ok=True)

    def q(s) -> str:
        return str(s).replace("'", "''")

    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        "$s.TargetPath='{target}';$s.Arguments='{args}';$s.WorkingDirectory='{cwd}';"
        "$s.IconLocation='{icon}';$s.Description='Murmur: free offline voice dictation';$s.Save()"
    ).format(link=q(link), target=q(_pythonw()), args=q(args), cwd=q(ROOT), icon=q(ICON_ICO))
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, timeout=20,
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def desktop_shortcut_path() -> Path:
    return _desktop_dir() / f"{APP_NAME}.lnk"


def create_desktop_and_start_menu():
    create_shortcut(desktop_shortcut_path())
    create_shortcut(START_MENU / f"{APP_NAME}.lnk")


def set_start_with_windows(enabled: bool):
    link = STARTUP / f"{APP_NAME}.lnk"
    if enabled:
        create_shortcut(link, "-m murmur --minimized")
    else:
        link.unlink(missing_ok=True)


def set_app_id():
    """Group the taskbar button under Murmur's own icon instead of Python's."""
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
