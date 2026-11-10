"""
entities/npc.py — Неигровые персонажи (Старейшина, Житель).

Статичные объекты: рисуются как прямоугольник с глазами,
над головой — имя. Имя рендерится один раз при создании
(в draw() только blit готовой поверхности).

Используется в game.py:
  - _spawn() — создаёт Старейшину (48, 65) и Жителя (55, 48)
  - _try_talk_to_npc() — проверяет близость и запускает диалог
  - _draw_level_1() — отрисовка

ВАЖНО: конструктор вызывает pygame.font.render() —
перед созданием NPC должен быть вызван pygame.font.init().
В main.py это гарантировано: init до импорта Game.

Шрифт грузится для каждого NPC отдельно. Для 2 NPC это
не проблема, но если когда-нибудь понадобится 50+ NPC —
стоит вынести кэш шрифта на уровень класса.

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class NPC:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    OUTLINE_COLOR = (30, 30, 30)      # обводка тела
    EYE_COLOR     = (0, 0, 0)         # глаза
    NAME_COLOR    = (255, 255, 255)   # текст имени
    # endregion

    # region КОНСТРУКТОР
    def __init__(self, x, y, name, color=COLOR_ELDER):
        # float() — для консистентности с bat.py / boss.py / enemy.py / key.py.
        self.x = float(x)
        self.y = float(y)

        self.w, self.h = 30, 34
        self.name = name
        self.color = color

        # Шрифт 16 px — компромисс между читаемостью и размером
        # над головой NPC. При отсутствии файла — дефолтный шрифт pygame.
        try:
            self.font = pygame.font.Font("assets/Tiny5-Bold.ttf", 16)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 16)

        # Имя рендерится один раз — в draw() только blit готовой Surface.
        # Это важно для производительности: render() дороже, чем blit().
        self.name_surface = self.font.render(self.name, True, self.NAME_COLOR)
    # endregion

    # region СВОЙСТВА
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Тело (прямоугольник со скруглением + обводка) ---
        body_rect = (sx, sy, self.w, self.h)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=6)
        pygame.draw.rect(screen, self.OUTLINE_COLOR, body_rect, 2, border_radius=6)

        # --- Глаза (две чёрные точки) ---
        # Смещение 9 px от края — примерно четверть ширины (30 / 4 ≈ 7.5),
        # 12 px от верха — примерно треть высоты (34 / 3 ≈ 11.3).
        # Подобрано визуально, чтобы глаза были «на лице», а не на макушке.
        pygame.draw.circle(screen, self.EYE_COLOR, (sx + 9, sy + 12), 2)
        pygame.draw.circle(screen, self.EYE_COLOR,
                           (sx + self.w - 9, sy + 12), 2)

        # --- Имя над головой (центрированное, готовая Surface) ---
        # sy - 16 — над верхним краем тела с отступом 16 px.
        # Центрирование по горизонтали: w/2 - ширина_текста/2.
        name_x = sx + self.w // 2 - self.name_surface.get_width() // 2
        screen.blit(self.name_surface, (name_x, sy - 16))
    # endregion