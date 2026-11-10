"""
ui/hud.py — HUD (Heads-Up Display).

Слева сверху — сердца (полные = текущий HP, тёмные = потерянные).
Справа сверху — иконка кристалла + счётчик «x N/3».

Текст счётчика перерендеривается только при изменении
количества кристаллов (в draw() в остальное время — blit готовой Surface).

Используется в game.py:
  - _reset() — создаёт экземпляр
  - _draw_ui() — draw (вызывается только в state == 'playing')

ВАЖНО: конструктор вызывает pygame.font.Font() —
перед созданием HUD должен быть вызван pygame.font.init().
В main.py это гарантировано: init до импорта Game.

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class HUD:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    HEART_FULL    = (220, 60, 60)     # полное сердце
    HEART_EMPTY   = (80, 30, 30)      # потерянное сердце
    HEART_OUTLINE = (20, 20, 20)      # контур сердца
    TEXT_COLOR    = (240, 240, 240)   # текст счётчика
    CRYSTAL_FILL  = COLOR_CRYSTAL     # тело иконки кристалла
    CRYSTAL_EDGE  = (100, 180, 220)   # обводка иконки
    # endregion

    # region КОНСТРУКТОР
    def __init__(self):
        try:
            self.font = pygame.font.Font("assets/Tiny5-Bold.ttf", 24)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 24)

        # Кэш текста кристаллов (перерендер только при изменении).
        # _last_text = None гарантирует, что первый draw() вызовет render:
        # current_text = "x N/M" != None всегда.
        self._last_text = None
        self._text_surf = None
    # endregion

    # region ПРИВАТНЫЕ МЕТОДЫ

    # region _heart
    def _heart(self, screen, x, y, color):
        """
        Рисует одно сердце с идеальным контуром.
        (x, y) — левый верхний угол иконки.

        Размер сердца: 28×26 px. Все координаты ниже относительны (x, y)
        и завязаны на этот размер. Если измените размер — пересчитайте
        вручную (заливка и обводка должны совпадать пиксель-в-пиксель).
        """
        # --- Заливка: 2 круга + треугольник ---
        # Круги центры: (x+8, y+8) и (x+20, y+8), радиус 8.
        # Треугольник: вершины (x, y+10), (x+28, y+10), (x+14, y+26).
        pygame.draw.circle(screen, color, (x + 8,  y + 8), 8)
        pygame.draw.circle(screen, color, (x + 20, y + 8), 8)
        pygame.draw.polygon(screen, color,
                            [(x, y + 10), (x + 28, y + 10), (x + 14, y + 26)])

        # --- Обводка: круги + боковые линии треугольника ---
        pygame.draw.circle(screen, self.HEART_OUTLINE, (x + 8,  y + 8), 8, 1)
        pygame.draw.circle(screen, self.HEART_OUTLINE, (x + 20, y + 8), 8, 1)
        pygame.draw.line(screen, self.HEART_OUTLINE,
                         (x,      y + 10), (x + 14, y + 26), 1)
        pygame.draw.line(screen, self.HEART_OUTLINE,
                         (x + 28, y + 10), (x + 14, y + 26), 1)

        # --- Замыкающие линии: стыки между кругами и треугольником ---
        # Без них обводка выглядит разорванной в точках (x, y+8..10)
        # и (x+28, y+8..10), где круг переходит в сторону треугольника.
        pygame.draw.line(screen, self.HEART_OUTLINE,
                         (x,      y + 8), (x,      y + 10), 1)
        pygame.draw.line(screen, self.HEART_OUTLINE,
                         (x + 28, y + 8), (x + 28, y + 10), 1)
    # endregion

    # endregion (ПРИВАТНЫЕ МЕТОДЫ)

    # region ОТРИСОВКА
    def draw(self, screen, player, total):
        # --- Сердца (слева, шаг 32 px, отступ 20 px) ---
        # 32 px — ширина сердца (28) + зазор 4 px между иконками.
        # При max_hp = 15 ширина ряда ~480 px + 20 отступ = 500 px,
        # при WIDTH = 960 ещё влезает. Если max_hp вырастет сильно —
        # придётся уменьшать шаг или переносить сердца на второй ряд.
        for i in range(player.max_hp):
            color = self.HEART_FULL if i < player.hp else self.HEART_EMPTY
            self._heart(screen, 20 + i * 32, 20, color)

        # --- Иконка кристалла (справа) ---
        # Центр (WIDTH - 130, 30), радиус 12, обводка 2 px.
        pygame.draw.circle(screen, self.CRYSTAL_FILL, (WIDTH - 130, 30), 12)
        pygame.draw.circle(screen, self.CRYSTAL_EDGE, (WIDTH - 130, 30), 12, 2)

        # --- Счётчик кристаллов (перерендер только при изменении) ---
        # current_text != None всегда, _last_text = None изначально —
        # значит первый вызов гарантированно отрендерит Surface.
        current_text = f"x {player.crystals}/{total}"
        if current_text != self._last_text:
            self._last_text = current_text
            self._text_surf = self.font.render(current_text, True, self.TEXT_COLOR)

        # Текст сдвинут вправо от иконки: иконка кончается на WIDTH - 118,
        # текст начинается на WIDTH - 110 (зазор 8 px).
        screen.blit(self._text_surf, (WIDTH - 110, 20))
    # endregion