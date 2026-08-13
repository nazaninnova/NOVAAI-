"""
profile_manager.py
-------------------
مدیریت پروفایل‌های محلی (بدون سرور، بدون اینترنت). هر کاربر یک پوشه‌ی
جدا زیر ~/.nova_ai_offline/profiles/<username>/ دارد که شامل:
  - history.json   : تاریخچه‌ی کامل مکالمات (برای نمایش در چت بعد از باز کردن اپ)
  - memory.txt      : «حافظه‌ی بلندمدت» — خلاصه‌ای از نکات مهم درباره‌ی
                      کاربر که هوش مصنوعی هر بار در system prompt می‌بیند
"""

import os
import json
import re

def _get_base_dir():
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            return os.path.join(app.user_data_dir, "profiles")
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), ".nova_ai_offline", "profiles")



def _safe_name(name: str) -> str:
    """اسم پروفایل را به یک نام‌پوشه‌ی امن تبدیل می‌کند."""
    name = name.strip()
    name = re.sub(r"[^\w\u0600-\u06FF\- ]", "", name)
    return name or "user"


def list_profiles():
    base = _get_base_dir()
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))


def profile_dir(username: str) -> str:
    d = os.path.join(_get_base_dir(), _safe_name(username))
    os.makedirs(d, exist_ok=True)
    return d


def load_history(username: str):
    path = os.path.join(profile_dir(username), "history.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return []


def save_history(username: str, history: list):
    path = os.path.join(profile_dir(username), "history.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


def load_memory(username: str) -> str:
    path = os.path.join(profile_dir(username), "memory.txt")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:  # noqa: BLE001
        return ""


def append_memory(username: str, note: str):
    if not note.strip():
        return
    path = os.path.join(profile_dir(username), "memory.txt")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(note.strip() + "\n")
    except Exception:  # noqa: BLE001
        pass
