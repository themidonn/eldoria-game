import pygame
from settings import *


class MiniMap:
    def __init__(self, world):
        self.scale = 2  # 1 тайл мира = 2x2 пикселя на карте
        self.w = world.w * self.scale
        self.h = world.h * self.scale

        # Позиция в правом верхнем углу (под счетчиком кристаллов)
        self.x = WIDTH - self.w - 20
        self.y = 70

        # Создаем фон (кэшируем, чтобы не рисовать 2700 квадратов каждый кадр)
        self.bg = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.bg.fill((20, 20, 30, 180))  # Полупрозрачный фон

        # Рисуем рельеф карты
        for ty in range(world.h):
            for tx in range(world.w):
                t = world.tiles[ty][tx]
                color = None
                if t == GRASS:
                    color = (60, 100, 60)
                elif t == DARK_FLOOR:
                    color = (70, 40, 40)
                elif t == HOUSE:
                    color = (150, 80, 50)
                elif t == WATER:
                    color = (40, 80, 140)
                elif t == STONE:
                    color = (100, 100, 110)

                if color:
                    pygame.draw.rect(self.bg, color, (tx * self.scale, ty * self.scale, self.scale, self.scale))

        # Рамка вокруг карты
        pygame.draw.rect(self.bg, (200, 180, 120), (0, 0, self.w, self.h), 2)

        # --- КЭШИРУЕМ ЗОНУ ПОИСКА КЛЮЧА ---
        # Размеры и позиция зоны не меняются, поэтому создаем их один раз
        zone_x = 75
        zone_y = 20
        zone_w = 95 - 75 + 1
        zone_h = 45 - 20 + 1

        mx = self.x + zone_x * self.scale
        my = self.y + zone_y * self.scale
        mw = zone_w * self.scale
        mh = zone_h * self.scale

        self.zone_rect = pygame.Rect(mx, my, mw, mh)
        self.zone_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        self.zone_surf.fill((255, 255, 255, 50))

    def draw(self, screen, game):
        # Рисуем закэшированный фон
        screen.blit(self.bg, (self.x, self.y))

        # Показываем зону, только если квест взят и ещё не выполнен
        if (game.villager_met and not game.villager_refused
                and not game.has_key and not game.quest_completed):
            screen.blit(self.zone_surf, self.zone_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 255), self.zone_rect, 1)

        # Вспомогательная функция: перевод координат мира в координаты мини-карты
        def to_mini(wx, wy):
            mx = self.x + int((wx / (game.world.w * TILE)) * self.w)
            my = self.y + int((wy / (game.world.h * TILE)) * self.h)
            return mx, my

        # 1. Рисуем Старейшину (желтая точка)
        for npc in game.npcs:
            nx, ny = to_mini(npc.x, npc.y)
            pygame.draw.circle(screen, (255, 200, 100), (nx, ny), 2)

        # 2. Рисуем Кристаллы (голубые точки, если еще не собраны)
        for c in game.crystals:
            if not c.collected:
                cx, cy = to_mini(c.x, c.y)
                pygame.draw.circle(screen, COLOR_CRYSTAL, (cx, cy), 2)

        # 3. Рисуем Босса (красная точка, если он активен)
        if game.boss_spawned and not game.boss.dead:
            bx, by = to_mini(game.boss.x, game.boss.y)
            pygame.draw.circle(screen, (255, 50, 50), (bx, by), 3)

        # 4. Рисуем Игрока (белая точка — рисуем последней, чтобы была поверх всех)
        px, py = to_mini(game.player.x, game.player.y)
        pygame.draw.circle(screen, (255, 255, 255), (px, py), 3)