"""
ui/minimap.py — Мини-карта в правом верхнем углу.

Показывает рельеф (трава/вода/дома/стены/пол замка/горы/болото)
и точки: NPC, кристаллы, босс, игрок.
"""

import pygame
from settings import *


class MiniMap:

    # ============================================================
    #   КОНСТАНТЫ
    # ============================================================
    # SCALE = 1.0 — карта 180×130 тайлов → 180×130 px.
    # 1 тайл = 1 пиксель. Дальше уменьшать нельзя — тайлы
    # станут меньше пикселя и карта превратится в кашу.
    SCALE = 1.0

    _TILE_COLORS = {
        GRASS:      (60, 100, 60),     # трава
        DARK_FLOOR: (70, 40, 40),      # пол замка
        HOUSE:      (150, 80, 50),     # дома деревни
        WATER:      (40, 80, 140),     # вода
        STONE:      (100, 100, 110),   # стены/колонны
        MOUNTAIN:   (80, 75, 70),      # горы
        SWAMP:      (40, 70, 40),      # болото
    }

    _DOT_NPC     = (255, 200, 100)
    _DOT_CRYSTAL = COLOR_CRYSTAL
    _DOT_BOSS    = (255, 50, 50)
    _DOT_PLAYER  = (255, 255, 255)

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, world):
        self.w = int(world.w * self.SCALE)
        self.h = int(world.h * self.SCALE)

        self.x = WIDTH - self.w - 20
        self.y = 70

        self.bg = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.bg.fill((20, 20, 30, 180))
        self._render_tiles(world)

        self._build_key_zone()

    # ============================================================
    #   ВНУТРЕННИЕ МЕТОДЫ
    # ============================================================
    def _render_tiles(self, world):
        """Рисует рельеф с округлением границ тайлов — без щелей и наложений."""
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

                pygame.draw.rect(self.bg, color, (x1, y1, x2 - x1, y2 - y1))

        pygame.draw.rect(self.bg, (200, 180, 120), (0, 0, self.w, self.h), 2)

    def _build_key_zone(self):
        zone_w = KEY_ZONE_X_MAX - KEY_ZONE_X_MIN + 1
        zone_h = KEY_ZONE_Y_MAX - KEY_ZONE_Y_MIN + 1

        mx = self.x + int(KEY_ZONE_X_MIN * self.SCALE)
        my = self.y + int(KEY_ZONE_Y_MIN * self.SCALE)
        mw = int(zone_w * self.SCALE)
        mh = int(zone_h * self.SCALE)

        self.zone_rect = pygame.Rect(mx, my, mw, mh)
        self.zone_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        self.zone_surf.fill((255, 255, 255, 50))

    def _to_mini(self, wx, wy, game):
        mx = self.x + int((wx / (game.world.w * TILE)) * self.w)
        my = self.y + int((wy / (game.world.h * TILE)) * self.h)
        return mx, my

    def _is_key_quest_active(self, game):
        return (game.villager_met
                and not game.villager_refused
                and not game.has_key
                and not game.quest_completed)

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, game):
        screen.blit(self.bg, (self.x, self.y))

        if self._is_key_quest_active(game):
            screen.blit(self.zone_surf, self.zone_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 255), self.zone_rect, 1)

        self._draw_dots(screen, game)

    def _draw_dots(self, screen, game):
        for npc in game.npcs:
            nx, ny = self._to_mini(npc.x, npc.y, game)
            pygame.draw.circle(screen, self._DOT_NPC, (nx, ny), 2)

        for c in game.crystals:
            if not c.collected:
                cx, cy = self._to_mini(c.x, c.y, game)
                pygame.draw.circle(screen, self._DOT_CRYSTAL, (cx, cy), 2)

        if game.boss_spawned and not game.boss.dead:
            bx, by = self._to_mini(game.boss.x, game.boss.y, game)
            pygame.draw.circle(screen, self._DOT_BOSS, (bx, by), 3)

        px, py = self._to_mini(game.player.x, game.player.y, game)
        pygame.draw.circle(screen, self._DOT_PLAYER, (px, py), 3)