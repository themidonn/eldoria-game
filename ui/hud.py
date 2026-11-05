"""
ui/hud.py — HUD (Heads-Up Display).

Слева сверху — сердца (полные = текущий HP, тёмные = потерянные).
Справа сверху — иконка кристалла + счётчик «x N/3».

Текст счётчика перерендеривается только при изменении
количества кристаллов (в draw() в остальное время — blit готовой Surface).
"""

import pygame
from settings import *


class HUD:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self):
        self.font = pygame.font.SysFont('arial', 20, bold=True)

        # Кэш текста кристаллов (перерендер только при изменении)
        self._last_text = None
        self._text_surf = None

    # ============================================================
    #   ПРИВАТНЫЕ МЕТОДЫ
    # ============================================================
    def _heart(self, screen, x, y, color):
        """
        Рисует одно сердце с идеальным контуром.
        (x, y) — левый верхний угол иконки.
        Размер сердца: 28x26 px.
        """
        OUTLINE = (20, 20, 20)

        # --- Заливка: 2 круга + треугольник ---
        pygame.draw.circle(screen, color, (x + 8,  y + 8), 8)
        pygame.draw.circle(screen, color, (x + 20, y + 8), 8)
        pygame.draw.polygon(screen, color,
                            [(x, y + 10), (x + 28, y + 10), (x + 14, y + 26)])

        # --- Обводка: круги + боковые линии треугольника ---
        pygame.draw.circle(screen, OUTLINE, (x + 8,  y + 8), 8, 1)
        pygame.draw.circle(screen, OUTLINE, (x + 20, y + 8), 8, 1)
        pygame.draw.line(screen, OUTLINE, (x,      y + 10), (x + 14, y + 26), 1)
        pygame.draw.line(screen, OUTLINE, (x + 28, y + 10), (x + 14, y + 26), 1)

        # --- Замыкающие линии: стыки между кругами и треугольником ---
        pygame.draw.line(screen, OUTLINE, (x,      y + 8), (x,      y + 10), 1)
        pygame.draw.line(screen, OUTLINE, (x + 28, y + 8), (x + 28, y + 10), 1)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, player, total):
        # --- Палитра ---
        HEART_FULL  = (220, 60, 60)
        HEART_EMPTY = (80, 30, 30)
        TEXT_COLOR  = (240, 240, 240)

        # --- Сердца (слева, шаг 32 px) ---
        for i in range(player.max_hp):
            color = HEART_FULL if i < player.hp else HEART_EMPTY
            self._heart(screen, 20 + i * 32, 20, color)

        # --- Иконка кристалла (справа) ---
        pygame.draw.circle(screen, COLOR_CRYSTAL,     (WIDTH - 130, 30), 12)
        pygame.draw.circle(screen, (100, 180, 220),   (WIDTH - 130, 30), 12, 2)

        # --- Счётчик кристаллов (перерендер только при изменении) ---
        current_text = f"x {player.crystals}/{total}"
        if current_text != self._last_text:
            self._last_text = current_text
            self._text_surf = self.font.render(current_text, True, TEXT_COLOR)

        screen.blit(self._text_surf, (WIDTH - 110, 20))