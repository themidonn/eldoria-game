"""
save.py — сохранение и загрузка прогресса.

Работает на десктопе (файл ~/.eldoria/save.json) и в браузере
через Pygbag (localStorage). Формат — JSON.
"""

import json
import os

_SAVE_KEY = "eldoria_save_v1"

# --- Определение окружения ---
# В Pygbag импортируется специальный platform с атрибутом window.
# На десктопе platform.window нет — hasattr вернёт False.
try:
    import platform as _platform
    _IS_WEB = hasattr(_platform, "window")
except ImportError:
    _IS_WEB = False


def _desktop_path():
    home = os.path.expanduser("~")
    folder = os.path.join(home, ".eldoria")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "save.json")


def exists():
    """Есть ли сохранение?"""
    try:
        if _IS_WEB:
            return _platform.window.localStorage.getItem(_SAVE_KEY) is not None
        return os.path.exists(_desktop_path())
    except Exception:
        return False


def write(data):
    """Записывает dict в сохранение. Возвращает True при успехе."""
    try:
        text = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        print(f"[save] serialize error: {e}")
        return False
    try:
        if _IS_WEB:
            _platform.window.localStorage.setItem(_SAVE_KEY, text)
        else:
            with open(_desktop_path(), "w", encoding="utf-8") as f:
                f.write(text)
        return True
    except Exception as e:
        print(f"[save] write error: {e}")
        return False


def read():
    """Читает сохранение. Возвращает dict или None."""
    try:
        if _IS_WEB:
            text = _platform.window.localStorage.getItem(_SAVE_KEY)
        else:
            path = _desktop_path()
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
    except Exception as e:
        print(f"[save] read error: {e}")
        return None
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[save] json error: {e}")
        return None


def delete():
    """Удаляет сохранение."""
    try:
        if _IS_WEB:
            _platform.window.localStorage.removeItem(_SAVE_KEY)
        else:
            path = _desktop_path()
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        print(f"[save] delete error: {e}")