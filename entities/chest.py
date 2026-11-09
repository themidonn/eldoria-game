"""
entities/chest.py — Сундук с сокровищем.

Закрыт, пока жив Король Скелетов. Когда босс подземелья мёртв —
сундук можно открыть по нажатию E и получить награду.

Награда: полное восстановление HP игрока.
"""

import pygame
from settings import *


class Chest:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 32, 28
        self.opened = False

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Палитра ---
        BODY_COLOR = (130, 80, 40)      # дерево
        BORDER    = (60, 30, 10)         # тёмный контур
        GOLD      = (220, 180, 80)       # металлические полосы/замок
        GOLD_DARK = (150, 110, 40)

        # --- Тело сундука ---
        body_rect = (sx, sy + 10, self.w, self.h - 10)
        pygame.draw.rect(screen, BODY_COLOR, body_rect, border_radius=3)
        pygame.draw.rect(screen, BORDER, body_rect, 2, border_radius=3)

        # --- Крышка (закрытая / открытая) ---
        if self.opened:
            # Открыта — рисуем как прямоугольник вверх и вправо (типа откинута)
            lid_rect = (sx, sy - 8, self.w, 14)
            pygame.draw.rect(screen, BODY_COLOR, lid_rect, border_radius=3)
            pygame.draw.rect(screen, BORDER, lid_rect, 2, border_radius=3)
            # Внутри — жёлтое свечение (сокровище)
            pygame.draw.rect(screen, GOLD,
                             (sx + 4, sy + 12, self.w - 8, self.h - 16))
        else:
            # Закрыта — крышка сверху
            lid_rect = (sx - 2, sy, self.w + 4, 14)
            pygame.draw.rect(screen, BODY_COLOR, lid_rect, border_radius=4)
            pygame.draw.rect(screen, BORDER, lid_rect, 2, border_radius=4)
            # Замок
            pygame.draw.rect(screen, GOLD,
                             (sx + self.w // 2 - 4, sy + 8, 8, 10), border_radius=2)
            pygame.draw.circle(screen, GOLD_DARK,
                               (sx + self.w // 2, sy + 12), 2)

        # --- Металлические полосы по бокам ---
        pygame.draw.line(screen, GOLD, (sx + 6, sy + 14), (sx + 6, sy + self.h),
                         2)
        pygame.draw.line(screen, GOLD,
                         (sx + self.w - 6, sy + 14),
                         (sx + self.w - 6, sy + self.h), 2)