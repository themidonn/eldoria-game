"""
ui/minimap.py — Мини-карта в правом верхнем углу.

Показывает рельеф (трава/вода/дома/стены/пол замка) и точки:
- Жёлтая — NPC (Старейшина, Житель).
- Голубая — не подобранные кристаллы.
- Красная — босс (когда активирован).
- Белая — игрок.

Дополнительно: во время квеста «найти ключ» показывает
белую полупрозрачную зону, где спавнится ключ.

Фон и зона поиска кэшируются — в draw() только blit'ы и точки.
Мини-карта рисуется только для главного мира (не для подземелья).
"""

import pygame
from settings import *


class MiniMap:

    # ============================================================
    #   КОНСТАНТЫ
    # ============================================================
    # Масштаб: 1 тайл мира = SCALE × SCALE пикселей на карте
    SCALE = 2

    # Цвета тайлов (ключ = тип тайла, значение = цвет)
    _TILE_COLORS = {
        GRASS:      (60, 100, 60),     # трава
        DARK_FLOOR: (70, 40, 40),      # пол замка
        HOUSE:      (150, 80, 50),     # дома деревни
        WATER:      (40, 80, 140),     # вода
        STONE:      (100, 100, 110),   # стены/колонны
    }

    # Цвета точек на карте
    _DOT_NPC     = (255, 200, 100)
    _DOT_CRYSTAL = COLOR_CRYSTAL
    _DOT_BOSS    = (255, 50, 50)
    _DOT_PLAYER  = (255, 255, 255)

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, world):
        self.w = world.w * self.SCALE
        self.h = world.h * self.SCALE

        # Позиция в правом верхнем углу (под счётчиком кристаллов)
        self.x = WIDTH - self.w - 20
        self.y = 70

        # --- Фон (кэш: рисуем рельеф 1 раз) ---
        self.bg = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.bg.fill((20, 20, 30, 180))
        self._render_tiles(world)

        # --- Зона поиска ключа (кэш) ---
        self._build_key_zone()

    # ============================================================
    #   ВНУТРЕННИЕ МЕТОДЫ
    # ============================================================
    def _render_tiles(self, world):
        """Рисует рельеф карты в фоновую Surface (один раз при создании)."""
        for ty in range(world.h):
            for tx in range(world.w):
                color = self._TILE_COLORS.get(world.tiles[ty][tx])
                if color:
                    rect = (tx * self.SCALE, ty * self.SCALE,
                            self.SCALE, self.SCALE)
                    pygame.draw.rect(self.bg, color, rect)

        # Рамка вокруг всей карты
        pygame.draw.rect(self.bg, (200, 180, 120), (0, 0, self.w, self.h), 2)

    def _build_key_zone(self):
        """Создаёт закэшированную Surface и Rect для зоны поиска ключа."""
        zone_w = KEY_ZONE_X_MAX - KEY_ZONE_X_MIN + 1
        zone_h = KEY_ZONE_Y_MAX - KEY_ZONE_Y_MIN + 1

        mx = self.x + KEY_ZONE_X_MIN * self.SCALE
        my = self.y + KEY_ZONE_Y_MIN * self.SCALE
        mw = zone_w * self.SCALE
        mh = zone_h * self.SCALE

        self.zone_rect = pygame.Rect(mx, my, mw, mh)
        self.zone_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        self.zone_surf.fill((255, 255, 255, 50))

    def _to_mini(self, wx, wy, game):
        """Переводит координаты мира (px) в координаты мини-карты (px)."""
        mx = self.x + int((wx / (game.world.w * TILE)) * self.w)
        my = self.y + int((wy / (game.world.h * TILE)) * self.h)
        return mx, my

    def _is_key_quest_active(self, game):
        """Идёт ли сейчас квест «найти ключ» (зона должна быть видна)."""
        return (game.villager_met
                and not game.villager_refused
                and not game.has_key
                and not game.quest_completed)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, game):
        # --- Слой 1: фон (рельеф) ---
        screen.blit(self.bg, (self.x, self.y))

        # --- Слой 2: зона поиска ключа (если квест активен) ---
        if self._is_key_quest_active(game):
            screen.blit(self.zone_surf, self.zone_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 255), self.zone_rect, 1)

        # --- Слой 3: точки (снизу вверх по важности) ---
        self._draw_dots(screen, game)

    def _draw_dots(self, screen, game):
        """Рисует точки: NPC, кристаллы, босс, игрок."""
        # NPC
        for npc in game.npcs:
            nx, ny = self._to_mini(npc.x, npc.y, game)
            pygame.draw.circle(screen, self._DOT_NPC, (nx, ny), 2)

        # Кристаллы (только не подобранные)
        for c in game.crystals:
            if not c.collected:
                cx, cy = self._to_mini(c.x, c.y, game)
                pygame.draw.circle(screen, self._DOT_CRYSTAL, (cx, cy), 2)

        # Босс (только активированный)
        if game.boss_spawned and not game.boss.dead:
            bx, by = self._to_mini(game.boss.x, game.boss.y, game)
            pygame.draw.circle(screen, self._DOT_BOSS, (bx, by), 3)

        # Игрок (последним — поверх всех)
        px, py = self._to_mini(game.player.x, game.player.y, game)
        pygame.draw.circle(screen, self._DOT_PLAYER, (px, py), 3)