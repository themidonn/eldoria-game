"""
ui/minimap.py — Мини-карта в правом верхнем углу.

Показывает рельеф (трава/вода/дома/стены/пол замка/горы/болото)
и точки: NPC, кристаллы, босс, игрок.

Используется в game.py:
  - _reset() — создаёт экземпляр с main_world
  - _draw_ui() — draw (только при level == 1)

ВАЖНО: конструктор создаёт pygame.Surface —
перед созданием MiniMap должен быть вызван pygame.display.init().
В main.py это гарантировано: init до импорта Game.

ВАЖНО: MiniMap создаётся для КОНКРЕТНОЙ карты (main_world).
_to_mini использует self._world_w / self._world_h, сохранённые
в конструкторе, а не game.world. Это защищает от бага, если
мини-карту когда-нибудь нарисуют в подземелье (game.world будет
Dungeon, а карта — от main_world).

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class MiniMap:

    # region КОНСТАНТЫ
    # SCALE = 1.0 — карта 180×130 тайлов → 180×130 px.
    # 1 тайл = 1 пиксель. Дальше уменьшать нельзя — тайлы
    # станут меньше пикселя и карта превратится в кашу.
    # (Поэтому в _render_tiles и _build_key_zone стоят max(1, ...):
    # если когда-нибудь SCALE уменьшат, тайлы не исчезнут.)
    SCALE = 1.0

    # Цвета рельефа (ключ — константа тайла из settings.py)
    _TILE_COLORS = {
        GRASS:      (60, 100, 60),     # трава
        DARK_FLOOR: (70, 40, 40),      # пол замка
        HOUSE:      (150, 80, 50),     # дома деревни
        WATER:      (40, 80, 140),     # вода
        STONE:      (100, 100, 110),   # стены/колонны
        MOUNTAIN:   (80, 75, 70),      # горы
        SWAMP:      (40, 70, 40),      # болото
    }

    # Цвета точек (не совпадают с цветами entity — так точки
    # лучше видны на фоне травы и камня)
    _DOT_NPC     = (255, 200, 100)    # оранжевый
    _DOT_CRYSTAL = COLOR_CRYSTAL      # голубой
    _DOT_BOSS    = (255, 50, 50)      # ярко-красный
    _DOT_PLAYER  = (255, 255, 255)    # белый
    # endregion

    # region КОНСТРУКТОР
    def __init__(self, world):
        # --- Размеры мини-карты (от исходной карты) ---
        self.w = int(world.w * self.SCALE)
        self.h = int(world.h * self.SCALE)

        # Сохраняем размеры ИСХОДНОЙ карты — нужны в _to_mini,
        # чтобы не зависеть от game.world (см. docstring модуля).
        self._world_w = world.w
        self._world_h = world.h

        # --- Позиция на экране (правый верхний угол) ---
        # 20 px отступ справа, 70 px сверху (под HUD).
        self.x = WIDTH - self.w - 20
        self.y = 70

        # --- Фон + рельеф ---
        self.bg = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        # SRCALPHA + alpha через цвет — Pygbag-safe.
        self.bg.fill((20, 20, 30, 180))
        self._render_tiles(world)

        # --- Зона ключа (подсветка, пока квест активен) ---
        self._build_key_zone()
    # endregion

    # region ВНУТРЕННИЕ МЕТОДЫ

    # region _render_tiles
    def _render_tiles(self, world):
        """
        Рисует рельеф с округлением границ тайлов — без щелей и наложений.

        max(1, ...) — защита от нулевой ширины/высоты тайла,
        если когда-нибудь SCALE уменьшат (например, до 0.5).
        """
        for ty in range(world.h):
            for tx in range(world.w):
                color = self._TILE_COLORS.get(world.tiles[ty][tx])
                if not color:
                    continue

                # Границы текущего тайла на мини-карте
                x1 = int(tx * self.SCALE)
                y1 = int(ty * self.SCALE)
                x2 = int((tx + 1) * self.SCALE)
                y2 = int((ty + 1) * self.SCALE)

                # max(1, ...) — чтобы тайл не исчез при SCALE < 1
                pygame.draw.rect(
                    self.bg, color,
                    (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
                )

        # Рамка мини-карты
        pygame.draw.rect(self.bg, (200, 180, 120), (0, 0, self.w, self.h), 2)
    # endregion

    # region _build_key_zone
    def _build_key_zone(self):
        """
        Строит подсветку зоны спавна ключа (KEY_ZONE_* из settings).

        max(1, ...) гарантирует ненулевой размер Surface, даже если
        SCALE уменьшат и зона окажется меньше пикселя.
        Поэтому zone_rect и zone_surf создаются всегда,
        и в draw() не нужна проверка на None.
        """
        zone_w = KEY_ZONE_X_MAX - KEY_ZONE_X_MIN + 1
        zone_h = KEY_ZONE_Y_MAX - KEY_ZONE_Y_MIN + 1

        mx = self.x + int(KEY_ZONE_X_MIN * self.SCALE)
        my = self.y + int(KEY_ZONE_Y_MIN * self.SCALE)
        mw = max(1, int(zone_w * self.SCALE))
        mh = max(1, int(zone_h * self.SCALE))

        self.zone_rect = pygame.Rect(mx, my, mw, mh)
        # SRCALPHA + alpha через цвет — Pygbag-safe.
        self.zone_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        self.zone_surf.fill((255, 255, 255, 50))
    # endregion

    # region _to_mini
    def _to_mini(self, wx, wy, game):
        """
        Преобразует мировые координаты (пиксели) в координаты мини-карты.

        Использует self._world_w / self._world_h — размеры карты,
        для которой создан MiniMap. НЕ использует game.world:
        если когда-нибудь minimap нарисуют в подземелье, game.world
        будет Dungeon, и координаты уедут.

        Параметр game оставлен для совместимости с вызовами
        (в будущем может понадобиться, например, для game.level).
        """
        mx = self.x + int((wx / (self._world_w * TILE)) * self.w)
        my = self.y + int((wy / (self._world_h * TILE)) * self.h)
        return mx, my
    # endregion

    # region _is_key_quest_active
    def _is_key_quest_active(self, game):
        """
        Квест Жителя активен, если ВСЕ условия выполнены:
          - villager_met     — игрок поговорил с Жителем
          - not refused      — не отказал (иначе NPC больше не заговорит)
          - not has_key      — ключ ещё не найден
          - not quest_completed — квест ещё не сдан
        """
        return (game.villager_met
                and not game.villager_refused
                and not game.has_key
                and not game.quest_completed)
    # endregion

    # endregion (ВНУТРЕННИЕ МЕТОДЫ)

    # region ОТРИСОВКА

    # region draw
    def draw(self, screen, game):
        # --- Фон + рельеф ---
        screen.blit(self.bg, (self.x, self.y))

        # --- Подсветка зоны ключа (только пока квест активен) ---
        # zone_surf всегда существует (см. _build_key_zone),
        # поэтому blit безопасен без проверки на None.
        if self._is_key_quest_active(game):
            screen.blit(self.zone_surf, self.zone_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 255), self.zone_rect, 1)

        # --- Точки поверх фона ---
        self._draw_dots(screen, game)
    # endregion

    # region _draw_dots
    def _draw_dots(self, screen, game):
        # --- NPC (все, кто есть на карте) ---
        for npc in game.npcs:
            nx, ny = self._to_mini(npc.x, npc.y, game)
            pygame.draw.circle(screen, self._DOT_NPC, (nx, ny), 2)

        # --- Кристаллы (только несобранные) ---
        for c in game.crystals:
            if not c.collected:
                cx, cy = self._to_mini(c.x, c.y, game)
                pygame.draw.circle(screen, self._DOT_CRYSTAL, (cx, cy), 2)

        # --- Босс (только после активации и пока жив) ---
        # game.boss всегда существует (создаётся в _spawn), поэтому
        # проверка `game.boss is not None` не нужна.
        if game.boss_spawned and not game.boss.dead:
            bx, by = self._to_mini(game.boss.x, game.boss.y, game)
            pygame.draw.circle(screen, self._DOT_BOSS, (bx, by), 3)

        # --- Игрок (всегда) ---
        px, py = self._to_mini(game.player.x, game.player.y, game)
        pygame.draw.circle(screen, self._DOT_PLAYER, (px, py), 3)
    # endregion

    # endregion (ОТРИСОВКА)