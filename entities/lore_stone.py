"""
entities/lore_stone.py — Древний камень с руной.

Игрок читает камень по нажатию E. Пока камень не прочитан —
руна светится голубым. После прочтения — гаснет (серая).
"""

import pygame
from settings import *


class LoreStone:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, title, text):
        self.x, self.y = x, y
        self.w = self.h = 36
        self.title = title                # заголовок диалога ("Древний камень")
        self.text = text                  # содержимое (лор)
        self.is_read = False              # прочитал ли игрок

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
        # --- Палитра (локальные константы) ---
        STONE_COLOR   = (100, 100, 110)
        STONE_OUTLINE = (60, 60, 70)
        SHADOW_COLOR  = (20, 40, 20)
        RUNE_ACTIVE   = (100, 200, 255)       # голубая светящаяся
        RUNE_GLOW     = (150, 220, 255)       # яркая точка в центре
        RUNE_INACTIVE = (40, 40, 50)          # тусклая (темнее обводки)

        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Тень под камнем ---
        pygame.draw.ellipse(screen, SHADOW_COLOR, (sx, sy + 26, self.w, 10))

        # --- Камень (уже хитбокса на 4 px с каждой стороны) ---
        stone_rect = (sx + 4, sy, self.w - 8, self.h)
        pygame.draw.rect(screen, STONE_COLOR, stone_rect, border_radius=4)
        pygame.draw.rect(screen, STONE_OUTLINE, stone_rect, 2, border_radius=4)

        # --- Руна ---
        if not self.is_read:
            # Активная: голубая, светится
            pygame.draw.line(screen, RUNE_ACTIVE, (sx + 18, sy + 8),  (sx + 18, sy + 24), 2)
            pygame.draw.line(screen, RUNE_ACTIVE, (sx + 12, sy + 14), (sx + 24, sy + 14), 2)
            pygame.draw.circle(screen, RUNE_GLOW, (sx + 18, sy + 16), 3)
        else:
            # Потухшая: серая, едва заметна
            pygame.draw.line(screen, RUNE_INACTIVE, (sx + 18, sy + 8),  (sx + 18, sy + 24), 2)
            pygame.draw.line(screen, RUNE_INACTIVE, (sx + 12, sy + 14), (sx + 24, sy + 14), 2)