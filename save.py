"""
save.py — сохранение и загрузка прогресса.

Две среды выполнения:
  • Десктоп (Windows / Linux / macOS) — файл в ~/.eldoria/save.json
  • Браузер (Pygbag/WASM) — localStorage

Определение среды через sys.platform == "emscripten" — это
официальный способ Pygbag отличить WASM от нативного Python.
Использовать hasattr(platform, "window") НЕЛЬЗЯ: в некоторых
сборках Pygbag этот атрибут либо отсутствует, либо ведёт себя
нестабильно — что вызывало ошибку BrowserFS not found.

Все операции обёрнуты в try/except, чтобы недоступность
localStorage (приватный режим, старый браузер, квота) не
роняла игру: просто не будет сохранений, но игра работает.

Используется в game.py:
  - exists()  — на старте, для титульника (Enter / N)
  - read()    — при загрузке сейва
  - write()   — при автосохранении и по F5
  - delete()  — при R (win/lose) и N (новая игра)
"""

import json
import os
import sys

_SAVE_KEY = "eldoria_save_v1"


# ============================================================
#   ОПРЕДЕЛЕНИЕ СРЕДЫ
#   sys.platform == "emscripten" → True в браузере (Pygbag),
#   False на десктопе. Это самый надёжный способ.
# ============================================================
_IS_WEB = (sys.platform == "emscripten")

# Для браузера: пробуем достать platform.window (localStorage).
# Если не получилось — _HAS_STORAGE = False, все операции
# будут возвращать «нет сохранения».
_HAS_STORAGE = False
_platform = None

if _IS_WEB:
    try:
        import platform as _platform  # специальный модуль Pygbag
        _HAS_STORAGE = hasattr(_platform, "window")
    except ImportError:
        _HAS_STORAGE = False


# ============================================================
#   ПУТЬ ДЛЯ ДЕСКТОПА
# ============================================================
def _desktop_path():
    """Возвращает путь к файлу сохранения на десктопе.

    Создаёт папку ~/.eldoria, если её нет. Используется только
    на десктопе: в браузере os.makedirs упал бы с BrowserFS not found.
    """
    home = os.path.expanduser("~")
    folder = os.path.join(home, ".eldoria")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "save.json")


# ============================================================
#   ПУБЛИЧНЫЕ ФУНКЦИИ
# ============================================================
def exists():
    """Есть ли сохранение? Возвращает bool."""
    try:
        if _IS_WEB:
            if not _HAS_STORAGE:
                return False
            return _platform.window.localStorage.getItem(_SAVE_KEY) is not None
        return os.path.exists(_desktop_path())
    except Exception:
        # Любая ошибка (браузер не даёт доступ, файл повреждён) —
        # считаем, что сохранения нет. Игра начнётся как новая.
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
            if not _HAS_STORAGE:
                return False
            _platform.window.localStorage.setItem(_SAVE_KEY, text)
        else:
            with open(_desktop_path(), "w", encoding="utf-8") as f:
                f.write(text)
        return True
    except Exception as e:
        # Квота localStorage переполнена / файл недоступен для записи /
        # любой другой сбой I/O — не роняем игру.
        print(f"[save] write error: {e}")
        return False


def read():
    """Читает сохранение. Возвращает dict или None."""
    try:
        if _IS_WEB:
            if not _HAS_STORAGE:
                return None
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
    """Удаляет сохранение. Молча игнорирует ошибки."""
    try:
        if _IS_WEB:
            if not _HAS_STORAGE:
                return
            _platform.window.localStorage.removeItem(_SAVE_KEY)
        else:
            path = _desktop_path()
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        print(f"[save] delete error: {e}")