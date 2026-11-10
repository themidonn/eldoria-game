"""
entities/lore_stone.py — Древний камень с руной.

Игрок читает камень по нажатию E (см. game.py, _try_read_lore_stone
и _try_read_dungeon_lore). Пока камень не прочитан — руна светится
голубым. После прочтения — гаснет (серая).

Используется в game.py:
  - _spawn() — 5 камней на наземном уровне
  - _ensure_dungeon() — 3 камня в подземелье
  - _try_read_lore_stone() / _try_read_dungeon_lore() — чтение
  - _draw_level_1() / _draw_level_2() — отрисовка
  - save_progress() / load_progress() — сохраняет is_read

После прочтения всех 5 наземных камней игрок получает +1 к макс. HP
(см. game.py, _try_read_lore_stone → lore_reward_given).

Поиск по файлу: Ctrl+F "region"
"""

import pygame


class LoreStone:

    # region ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    STONE_COLOR   = (100, 100, 110)     # тело камня
    STONE_OUTLINE = (60, 60, 70)        # контур
    SHADOW_COLOR  = (20, 40, 20)        # тень под камнем
    RUNE_ACTIVE   = (100, 200, 255)     # голубая светящаяся руна
    RUNE_GLOW     = (150, 220, 255)     # яркая точка в центре руны
    RUNE_INACTIVE = (40, 40, 50)        # потухшая руна (темнее контура)
    # endregion

    # region КОНСТРУКТОР
    def __init__(self, x, y, title, text):
        # float() — для консистентности с bat.py / boss.py / enemy.py / key.py.
        self.x = float(x)
        self.y = float(y)

        self.w = self.h = 36
        self.title = title                # заголовок диалога ("Древний камень")
        self.text = text                  # содержимое (лор)
        self.is_read = False              # прочитал ли игрок
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

        # --- Тень под камнем (вылезает за низ хитбокса — это нормально) ---
        pygame.draw.ellipse(
            screen, self.SHADOW_COLOR,
            (sx, sy + 26, self.w, 10)
        )

        # --- Камень (уже хитбокса на 4 px с каждой стороны) ---
        # Хитбокс 36×36, тело 28×36 — так игрок может «зайти» за край
        # камня на 4 px и всё равно прочитать его. Это сделано специально
        # (см. game.py, rect.inflate(40, 40) при проверке близости).
        stone_rect = (sx + 4, sy, self.w - 8, self.h)
        pygame.draw.rect(screen, self.STONE_COLOR, stone_rect, border_radius=4)
        pygame.draw.rect(screen, self.STONE_OUTLINE, stone_rect, 2, border_radius=4)

        # --- Центр руны (вычисляется от stone_rect, а не от sx) ---
        # Так руна останется по центру, даже если кто-то изменит w/h.
        rune_cx = sx + 4 + (self.w - 8) // 2
        rune_cy = sy + self.h // 2

        # --- Руна: вертикальная черта + горизонтальная перекладина ---
        if not self.is_read:
            # Активная: голубая, светится
            pygame.draw.line(
                screen, self.RUNE_ACTIVE,
                (rune_cx, sy + 8), (rune_cx, sy + 24), 2
            )
            pygame.draw.line(
                screen, self.RUNE_ACTIVE,
                (rune_cx - 6, rune_cy), (rune_cx + 6, rune_cy), 2
            )
            pygame.draw.circle(screen, self.RUNE_GLOW, (rune_cx, rune_cy), 3)
        else:
            # Потухшая: серая, едва заметна.
            # Точки в центре нет — это визуальный сигнал «руна мертва».
            pygame.draw.line(
                screen, self.RUNE_INACTIVE,
                (rune_cx, sy + 8), (rune_cx, sy + 24), 2
            )
            pygame.draw.line(
                screen, self.RUNE_INACTIVE,
                (rune_cx - 6, rune_cy), (rune_cx + 6, rune_cy), 2
            )
    # endregion