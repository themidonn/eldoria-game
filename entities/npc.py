"""
entities/npc.py — Неигровые персонажи (Старейшина, Житель).

Статичные объекты: рисуются как прямоугольник с глазами,
над головой — имя. Имя рендерится один раз при создании
(в draw() только blit готовой поверхности).
"""

import pygame
from settings import *


class NPC:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, name, color=COLOR_ELDER):
        self.x, self.y = x, y
        self.w, self.h = 30, 34
        self.name = name
        self.color = color

        try:
            self.font = pygame.font.Font("assets/Tiny5-Bold.ttf", 16)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 16)

        self.name_surface = self.font.render(self.name, True, (255, 255, 255))

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
        # --- Палитра ---
        OUTLINE_COLOR = (30, 30, 30)
        EYE_COLOR     = (0, 0, 0)

        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Тело (прямоугольник со скруглением + обводка) ---
        body_rect = (sx, sy, self.w, self.h)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=6)
        pygame.draw.rect(screen, OUTLINE_COLOR, body_rect, 2, border_radius=6)

        # --- Глаза (две чёрные точки) ---
        pygame.draw.circle(screen, EYE_COLOR, (sx + 9, sy + 12), 2)
        pygame.draw.circle(screen, EYE_COLOR, (sx + self.w - 9, sy + 12), 2)

        # --- Имя над головой (центрированное, готовая Surface) ---
        name_x = sx + self.w // 2 - self.name_surface.get_width() // 2
        screen.blit(self.name_surface, (name_x, sy - 16))