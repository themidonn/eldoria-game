"""
entities/potion.py — Зелье лечения.

Подбирается игроком (если HP не полное). Восстанавливает 1 HP.
Покачивается вверх-вниз, светится красным. Флакон = 5 частей:
горлышко, пробка, тело, обводка тела, блик.
"""

import math
import pygame
from settings import *


class Potion:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w = self.h = 24
        self.collected = False
        self.bob = 0                          # фаза покачивания

        # Кэшируем красное свечение (60x60 с альфа-каналом)
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 150, 150, 70), (30, 30), 30)

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

        # --- Палитра флакона (5 частей) ---
        NECK_COLOR    = (80, 60, 40)          # горлышко
        CORK_COLOR    = (150, 100, 50)        # пробка
        BODY_COLOR    = (200, 40, 40)         # красная жидкость
        BODY_OUTLINE  = (60, 10, 10)          # обводка тела
        HIGHLIGHT     = (255, 200, 200)       # блик

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 3)

        # --- Свечение (готовый Surface) ---
        screen.blit(self.glow, (sx - 18, sy - 18))

        # --- Горлышко (узкая вертикальная полоска) ---
        pygame.draw.rect(screen, NECK_COLOR, (sx + 9, sy + 2, 6, 8))

        # --- Пробка (поперечная полоска сверху) ---
        pygame.draw.rect(screen, CORK_COLOR, (sx + 8, sy, 8, 4), border_radius=2)

        # --- Тело флакона (красный прямоугольник со скруглением) ---
        body_rect = (sx + 4, sy + 8, 16, 14)
        pygame.draw.rect(screen, BODY_COLOR, body_rect, border_radius=4)
        pygame.draw.rect(screen, BODY_OUTLINE, body_rect, 1, border_radius=4)

        # --- Блик (белая точка на жидкости) ---
        pygame.draw.circle(screen, HIGHLIGHT, (sx + 8, sy + 12), 2)