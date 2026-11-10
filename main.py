"""
main.py — точка входа в игру.

ВАЖНО: порядок действий нарушать нельзя.
1. pygame.display.init() + pygame.font.init() — инициализация Pygame.
   (pygame.init() НЕ используем: в Pygbag он падает на mixer.init()
   с ошибкой SDL_OpenAudioDevice / Mix_OpenAudioDevice. Звук в игре
   пока не используется, поэтому микшер не инициализируем.)
2. Создаём окно через display.set_mode() ДО импорта Game.
   Game.__init__ вызывает pygame.display.get_surface() — без
   предварительного set_mode он вернёт None.
3. Только ПОСЛЕ этого можно импортировать Game.

Поиск по файлу: Ctrl+F "region"
"""

# region АУДИО-ДРАЙВЕР (только для Pygbag)
# SDL_AUDIODRIVER=dummy нужен ТОЛЬКО в Pygbag/WASM, где реальный
# аудиодрайвер недоступен. На десктопе dummy ставить нельзя —
# иначе pygame.mixer (если добавишь звук) будет молчать.
# sys.platform == "emscripten" — стандартный детект Pygbag.
import os
import sys

if sys.platform == "emscripten":
    os.environ["SDL_AUDIODRIVER"] = "dummy"
# endregion

# region ИМПОРТЫ
import asyncio
import pygame

from settings import WIDTH, HEIGHT
# endregion

# region ИНИЦИАЛИЗАЦИЯ PYGAME (до импорта Game!)
pygame.display.init()
pygame.font.init()
pygame.display.set_mode((WIDTH, HEIGHT))
# endregion

# region ИМПОРТ ИГРЫ (только после init)
# Импорт Game ТРЕБУЕТ, чтобы display.set_mode уже был вызван —
# Game.__init__ читает pygame.display.get_surface().
from game import Game
# endregion

# region ЗАПУСК
async def main():
    """
    Асинхронная точка входа. Pygbag требует async для работы в браузере.

    asyncio.sleep(0) в конце — попадает сюда только если game.run()
    вернулся (self.running = False). Даёт Pygbag «подышать» при выходе.
    """
    game = Game()
    await game.run()
    await asyncio.sleep(0)


# ВАЖНО: без `if __name__ == "__main__":` — Pygbag запускает main.py
# не как обычный скрипт, и __name__ может быть не "__main__".
# Стандартный паттерн Pygbag — asyncio.run(main()) на верхнем уровне.
asyncio.run(main())
# endregion