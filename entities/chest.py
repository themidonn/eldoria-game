"""
entities/chest.py — Сундук с сокровищем.

Закрыт, пока жив Король Скелетов (босс подземелья). Когда босс
мёртв — сундук можно открыть по нажатию E и получить награду.

Награда: полное восстановление HP игрока.

Используется в game.py:
  - _ensure_dungeon() — создаёт экземпляр (один на подземелье)
  - _try_open_chest() — проверяет близость, ставит opened = True
  - _draw_level_2() / _draw_hints() — отрисовка и подсказка
  - save_progress() / load_progress() — сохраняет opened

Поиск по файлу: Ctrl+F "region"
"""

import pygame


class Chest:

    # region КОНСТРУКТОР
    def __init__(self, x, y):
        # float() — для консистентности с bat.py / boss.py / skeleton.py.
        # Сундук не двигается, но float-арифметика в rect и draw
        # ведёт себя предсказуемее, чем смесь int и float.
        self.x = float(x)
        self.y = float(y)

        # Размер тела: 32×28 — компактнее тайла (TILE = 40).
        # Тело занимает нижние 18 px (self.h - 10), крышка — верхние 10.
        self.w, self.h = 32, 28

        # Открыт ли сундук (сохраняется в save_progress)
        self.opened = False
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

        # --- Палитра ---
        BODY_COLOR = (130, 80, 40)      # дерево
        BORDER     = (60, 30, 10)       # тёмный контур
        GOLD       = (220, 180, 80)     # металлические полосы/замок
        GOLD_DARK  = (150, 110, 40)     # тень замка

        # --- Тело сундука (нижние 18 px) ---
        # Верхние 10 px (sy..sy+10) — зона крышки.
        body_rect = (sx, sy + 10, self.w, self.h - 10)
        pygame.draw.rect(screen, BODY_COLOR, body_rect, border_radius=3)
        pygame.draw.rect(screen, BORDER, body_rect, 2, border_radius=3)

        # --- Крышка: открытая или закрытая ---
        if self.opened:
            # Открыта — крышка откинута вверх, стыкуется с телом.
            # Диапазон: sy-4 .. sy+10 (тело начинается с sy+10).
            lid_rect = (sx, sy - 4, self.w, 14)
            pygame.draw.rect(screen, BODY_COLOR, lid_rect, border_radius=4)
            pygame.draw.rect(screen, BORDER, lid_rect, 2, border_radius=4)

            # Внутри — жёлтое свечение (сокровище).
            # Высота self.h - 14 = 14, отступ 2 px от низа тела.
            pygame.draw.rect(
                screen, GOLD,
                (sx + 4, sy + 12, self.w - 8, self.h - 14)
            )
        else:
            # Закрыта — крышка сверху, чуть шире тела (sx-2 .. sx+w+2).
            lid_rect = (sx - 2, sy, self.w + 4, 14)
            pygame.draw.rect(screen, BODY_COLOR, lid_rect, border_radius=4)
            pygame.draw.rect(screen, BORDER, lid_rect, 2, border_radius=4)

            # Замок по центру крышки: 8×10 + круглая замочная скважина.
            pygame.draw.rect(
                screen, GOLD,
                (sx + self.w // 2 - 4, sy + 8, 8, 10),
                border_radius=2
            )
            pygame.draw.circle(
                screen, GOLD_DARK,
                (sx + self.w // 2, sy + 12), 2
            )

        # --- Металлические полосы по бокам (рисуются поверх всего) ---
        # Идут от верха тела (sy + 14) до низа (sy + self.h).
        pygame.draw.line(screen, GOLD,
                         (sx + 6, sy + 14), (sx + 6, sy + self.h), 2)
        pygame.draw.line(screen, GOLD,
                         (sx + self.w - 6, sy + 14),
                         (sx + self.w - 6, sy + self.h), 2)
    # endregion