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

Поиск по файлу: Ctrl+F "region"
"""

import json
import os
import sys


# region КОНСТАНТЫ
# Версионированный ключ: если формат сохранения изменится —
# поднять до _v2, старый _v1 останется нетронутым в localStorage.
_SAVE_KEY = "eldoria_save_v1"
# endregion


# region ОПРЕДЕЛЕНИЕ СРЕДЫ
# sys.platform == "emscripten" → True в браузере (Pygbag),
# False на десктопе. Это самый надёжный способ.
_IS_WEB = (sys.platform == "emscripten")

# Для браузера: пробуем достать platform.window (localStorage).
# Если не получилось — _HAS_STORAGE = False, все операции
# будут возвращать «нет сохранения».
_HAS_STORAGE = False
_platform = None

if _IS_WEB:
    try:
        import platform as _platform  # специальный модуль Pygbag
        # getattr(..., None) is not None — строже, чем hasattr:
        # если window существует, но равен None (битое состояние
        # Pygbag), hasattr вернул бы True, а мы — False.
        # Дополнительно проверяем localStorage: в редких сборках
        # window есть, а localStorage нет.
        _HAS_STORAGE = (
            getattr(_platform, "window", None) is not None
            and hasattr(_platform.window, "localStorage")
        )
    except ImportError as e:
        # На практике не срабатывает: platform — стандартный модуль.
        # Но Pygbag исторически нестабилен, оставляем защиту и
        # печатаем ошибку, чтобы отладка была возможной.
        print(f"[save] platform import error: {e}")
        _HAS_STORAGE = False
# endregion


# region ПУТЬ ДЛЯ ДЕСКТОПА
def _desktop_dir():
    """
    Возвращает путь к папке ~/.eldoria — БЕЗ создания.

    Создание папки — только в write(): exists()/read()/delete()
    не должны иметь побочных эффектов на файловую систему.
    """
    return os.path.join(os.path.expanduser("~"), ".eldoria")


def _desktop_path():
    """Возвращает путь к файлу сохранения — БЕЗ создания папки."""
    return os.path.join(_desktop_dir(), "save.json")
# endregion


# region ПУБЛИЧНЫЕ ФУНКЦИИ
def exists():
    """
    Есть ли сохранение? Возвращает bool.

    Без побочных эффектов: не создаёт ~/.eldoria/, если её нет.
    """
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
            # makedirs — только здесь: это единственное место,
            # где папка реально нужна. exist_ok=True — если папка
            # уже есть, ничего не делаем (частый случай).
            os.makedirs(_desktop_dir(), exist_ok=True)
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
# endregion