"""
entities/pickup.py — Кристалл Света.

Подбирается игроком (3 штуки на карте). Светится голубым,
покачивается вверх-вниз. После подбора исчезает.
"""

import math
import pygame
from settings import *


class Crystal:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, name="Кристалл Света"):
        self.x, self.y = x, y
        self.w = self.h = 24
        self.name = name
        self.collected = False
        self.bob = 0                          # фаза покачивания

        # Кэшируем голубое свечение (60x60 с альфа-каналом)
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (180, 240, 255, 80), (30, 30), 30)

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, dt):
        self.bob += dt * 0.005

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.collected:
            return

        # --- Палитра ---
        BODY_COLOR    = COLOR_CRYSTAL
        OUTLINE_COLOR = (100, 180, 220)
        HIGHLIGHT     = (255, 255, 255)

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 4)

        # --- Свечение (готовый Surface) ---
        screen.blit(self.glow, (sx - 18, sy - 18))

        # --- Тело: пятиугольник-кристалл (5 вершин) ---
        pts = [
            (sx + 12, sy),        # верх
            (sx + 24, sy + 10),   # правый верх
            (sx + 20, sy + 24),   # правый низ
            (sx + 4,  sy + 24),   # левый низ
            (sx,      sy + 10),   # левый верх
        ]
        pygame.draw.polygon(screen, BODY_COLOR, pts)
        pygame.draw.polygon(screen, OUTLINE_COLOR, pts, 2)

        # --- Блик внутри (белая черта сверху-слева) ---
        pygame.draw.line(screen, HIGHLIGHT, (sx + 12, sy + 4), (sx + 8, sy + 16), 2)