import pygame
from settings import *


class Dungeon:
    def __init__(self):
        self.w, self.h = 40, 25
        self.gate_open = False  # Для совместимости с World
        self.generate()

    def generate(self):
        # Всё стены
        self.tiles = [[STONE for _ in range(self.w)] for _ in range(self.h)]

        # Выкапываем залу
        for ty in range(2, self.h - 2):
            for tx in range(2, self.w - 2):
                self.tiles[ty][tx] = DARK_FLOOR

        # Колонны (2x2) для атмосферы
        for ty in range(5, self.h - 5, 5):
            for tx in range(5, self.w - 5, 5):
                self.tiles[ty][tx] = STONE
                if tx + 1 < self.w - 2:
                    self.tiles[ty][tx + 1] = STONE
                if ty + 1 < self.h - 2:
                    self.tiles[ty + 1][tx] = STONE
                    self.tiles[ty + 1][tx + 1] = STONE

        # Лестница вверх (выход) в левом нижнем углу
        self.tiles[self.h - 4][4] = STAIRS_UP

    def is_walkable_px(self, px, py):
        tx, ty = int(px // TILE), int(py // TILE)
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False
        t = self.tiles[ty][tx]
        return t in (DARK_FLOOR, FLOOR, GRASS, STAIRS_UP)

    def is_walkable_rect(self, x, y, w, h):
        tx0, ty0 = int(x // TILE), int(y // TILE)
        tx1, ty1 = int((x + w - 1) // TILE), int((y + h - 1) // TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if not self.is_walkable_px(tx * TILE + TILE // 2,
                                           ty * TILE + TILE // 2):
                    return False
        return True

    def draw(self, screen, cam):
        x0 = max(0, int(cam.x) // TILE)
        y0 = max(0, int(cam.y) // TILE)
        x1 = min(self.w, (int(cam.x) + WIDTH) // TILE + 2)
        y1 = min(self.h, (int(cam.y) + HEIGHT) // TILE + 2)
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                t = self.tiles[ty][tx]
                sx, sy = int(tx * TILE - cam.x), int(ty * TILE - cam.y)
                r = (sx, sy, TILE, TILE)
                if t == STONE:
                    pygame.draw.rect(screen, COLOR_STONE, r)
                    pygame.draw.rect(screen, (60, 60, 70), r, 2)
                elif t == DARK_FLOOR:
                    pygame.draw.rect(screen, COLOR_DARK_FLOOR, r)
                    # Кирпичики на полу для атмосферы
                    pygame.draw.line(screen, (50, 35, 35), (sx, sy + TILE // 2), (sx + TILE, sy + TILE // 2), 1)
                    pygame.draw.line(screen, (50, 35, 35), (sx + TILE // 2, sy), (sx + TILE // 2, sy + TILE // 2), 1)
                elif t == STAIRS_UP:
                    pygame.draw.rect(screen, COLOR_STONE, r)
                    for i in range(3):
                        y = sy + 6 + i * 10
                        pygame.draw.line(screen, (50, 50, 60), (sx + 6, y), (sx + TILE - 6, y), 3)
                    pygame.draw.polygon(screen, COLOR_STAIRS_UP, [
                        (sx + TILE // 2, sy + 8),
                        (sx + TILE // 2 - 6, sy + 18),
                        (sx + TILE // 2 + 6, sy + 18)
                    ])