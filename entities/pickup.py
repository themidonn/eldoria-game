"""
entities/pickup.py — Кристалл Света.

Подбирается игроком (3 штуки на карте). Светится голубым,
покачивается вверх-вниз. После подбора исчезает.

Используется в game.py:
  - _spawn() / _spawn_crystal_and_guards() — создаёт 3 кристалла
  - _update_level_1() — update + проверка коллизии с игроком
  - _draw_level_1() — draw (только если не собран)
  - save_progress() / load_progress() — сохраняет collected по индексу

Поле `name` используется для отладки и логирования (например,
"Кристалл Леса", "Кристалл Воды", "Кристалл Руин"). В save-файл
не попадает: там кристаллы сохраняются по индексу в списке.

ВАЖНО: конструктор создаёт pygame.Surface для свечения —
перед созданием Crystal должен быть вызван pygame.display.init().
В main.py это гарантировано: init до импорта Game.

Поиск по файлу: Ctrl+F "region"
"""

import math
import pygame
from settings import *


class Crystal:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    BODY_COLOR    = COLOR_CRYSTAL       # тело кристалла
    OUTLINE_COLOR = (100, 180, 220)     # контур
    HIGHLIGHT     = (255, 255, 255)     # блик
    GLOW_COLOR    = (180, 240, 255, 80) # свечение (alpha в цвете)
    # endregion

    # region КОНСТРУКТОР
    def __init__(self, x, y, name="Кристалл Света"):
        # float() — для консистентности с bat.py / boss.py / enemy.py / key.py.
        self.x = float(x)
        self.y = float(y)

        self.w = self.h = 24
        self.name = name
        self.collected = False
        self.bob = 0                          # фаза покачивания

        # Кэшируем свечение один раз (60×60 с альфа-каналом).
        # SRCALPHA + цвет (180, 240, 255, 80) — Pygbag-safe:
        # альфа задаётся через цвет, а не через Surface.set_alpha().
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, self.GLOW_COLOR, (30, 30), 30)
    # endregion

    # region СВОЙСТВА
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    # endregion

    # region ЛОГИКА
    def update(self, dt):
        # Собранный кристалл не анимируется — экономим вычисления.
        if self.collected:
            return

        # bob крутится в цикле, чтобы float не терял точность
        # при очень долгой игре (как в bat.py / key.py).
        self.bob = (self.bob + dt * 0.005) % (2 * math.pi * 1000)
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        if self.collected:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 4)

        # --- Свечение (готовый Surface) ---
        # glow 60×60, центр в (30, 30). Смещение (-18, -18) даёт
        # центр свечения на (sx + 12, sy + 12) — центр кристалла.
        screen.blit(self.glow, (sx - 18, sy - 18))

        # --- Тело: пятиугольник-кристалл (5 вершин) ---
        # Координаты завязаны на w = h = 24. Если измените размер —
        # пересчитайте вручную: форма не симметрична по высоте
        # (верхняя вершина на 10 px выше боковых).
        pts = [
            (sx + 12, sy),        # верх
            (sx + 24, sy + 10),   # правый верх
            (sx + 20, sy + 24),   # правый низ
            (sx + 4,  sy + 24),   # левый низ
            (sx,      sy + 10),   # левый верх
        ]
        pygame.draw.polygon(screen, self.BODY_COLOR, pts)
        pygame.draw.polygon(screen, self.OUTLINE_COLOR, pts, 2)

        # --- Блик внутри (белая черта сверху-слева) ---
        pygame.draw.line(screen, self.HIGHLIGHT,
                         (sx + 12, sy + 4), (sx + 8, sy + 16), 2)
    # endregion