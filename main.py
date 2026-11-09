"""
main.py — точка входа в игру.

ВАЖНО: порядок действий нарушать нельзя.
1. pygame.display.init() + pygame.font.init() — инициализация Pygame.
   (pygame.init() НЕ используем: в Pygbag он падает на mixer.init()
   с ошибкой SDL_OpenAudioDevice / Mix_OpenAudioDevice. Звук в игре
   пока не используется, поэтому микшер не инициализируем.)
2. Создаём окно через display.set_mode() ДО импорта Game.
   Pygbag требует, чтобы canvas был создан до загрузки модулей.
3. Только ПОСЛЕ этого можно импортировать Game.
"""

import os
os.environ["SDL_AUDIODRIVER"] = "dummy"

import asyncio
import pygame

from settings import WIDTH, HEIGHT


# ============================================================
#   ИНИЦИАЛИЗАЦИЯ PYGAME (до импорта Game!)
# ============================================================
pygame.display.init()
pygame.font.init()
pygame.display.set_mode((WIDTH, HEIGHT))  # ← ДОБАВЛЕНО: Pygbag требует создания окна здесь


# ============================================================
#   ИМПОРТ ИГРЫ (только после init)
# ============================================================
from game import Game


# ============================================================
#   ЗАПУСК
# ============================================================
async def main():
    """Асинхронная точка входа. Pygbag требует async для работы в браузере."""
    game = Game()
    await game.run()
    await asyncio.sleep(0)  # ← ДОБАВЛЕНО: защита от зависания браузера при выходе


if __name__ == "__main__":
    asyncio.run(main())