"""
entities/key.py — Золотой ключ жителя.

Спавнится в случайном месте в лесу (зона задаётся в settings.py:
KEY_ZONE_X_MIN..MAX, KEY_ZONE_Y_MIN..MAX).
Покачивается вверх-вниз, светится золотым, исчезает после подбора.
"""

import math
import pygame


class Key:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w = self.h = 24
        self.collected = False
        self.bob = 0                          # фаза покачивания

        # Кэшируем свечение один раз (60x60 с альфа-каналом)
        self.glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 215, 0, 80), (30, 30), 30)

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

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y + math.sin(self.bob) * 4)

        GOLD = (255, 215, 0)

        # --- Свечение (готовый Surface) ---
        screen.blit(self.glow, (sx - 18, sy - 18))

        # --- Кольцо ключа ---
        pygame.draw.circle(screen, GOLD, (sx + 8, sy + 8), 5, 2)

        # --- Стержень ---
        pygame.draw.line(screen, GOLD, (sx + 11, sy + 11), (sx + 18, sy + 18), 3)

        # --- Зубчики (два маленьких отрезка) ---
        pygame.draw.line(screen, GOLD, (sx + 15, sy + 15), (sx + 18, sy + 12), 2)
        pygame.draw.line(screen, GOLD, (sx + 18, sy + 18), (sx + 20, sy + 16), 2)