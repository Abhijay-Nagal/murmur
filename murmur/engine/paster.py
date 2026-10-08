"""Types text into whatever window has focus, by pasting through the clipboard."""
import ctypes
import threading
import time
from ctypes import wintypes
from pathlib import Path

import keyboard
import pyperclip

_FRIENDLY = {
    "chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox", "brave": "Brave", "opera": "Opera",
    "code": "VS Code", "cursor": "Cursor", "notepad": "Notepad", "winword": "Word", "excel": "Excel",
    "powerpnt": "PowerPoint", "outlook": "Outlook", "olk": "Outlook", "whatsapp": "WhatsApp",
    "whatsapp.root": "WhatsApp", "telegram": "Telegram", "discord": "Discord", "slack": "Slack",
    "ms-teams": "Teams", "teams": "Teams", "notion": "Notion", "obsidian": "Obsidian",
    "windowsterminal": "Terminal", "explorer": "Explorer", "claude": "Claude", "pythonw": "Murmur",
}


def foreground_app() -> str:
    """Friendly name of the app that has keyboard focus, e.g. 'Chrome'."""
    try:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(len(buf))
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return ""
        finally:
            kernel32.CloseHandle(handle)
        stem = Path(buf.value).stem
        return _FRIENDLY.get(stem.lower(), stem[:1].upper() + stem[1:])
    except OSError:
        return ""


def _wait_for_modifiers_release(timeout: float = 2.0):
    # A still-held Alt would turn our Ctrl+V into Ctrl+Alt+V.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(
        keyboard.is_pressed(k) for k in ("ctrl", "alt", "shift", "left windows", "right windows")
    ):
        time.sleep(0.02)


def paste(text: str, restore_clipboard: bool = True):
    _wait_for_modifiers_release()
    previous = ""
    if restore_clipboard:
        try:
            previous = pyperclip.paste()
        except pyperclip.PyperclipException:
            pass
    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    # Restore only text we could read; some apps read the clipboard lazily, so wait a bit.
    if previous:
        threading.Timer(0.5, pyperclip.copy, args=(previous,)).start()
