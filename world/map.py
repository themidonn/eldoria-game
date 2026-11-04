import random, pygame
from settings import *


class World:
    def __init__(self):
        self.w, self.h = 100, 75  # <-- УВЕЛИЧИЛИ РАЗМЕР КАРТЫ
        self.gate_open = False
        self.generate()

    # ---------- генерация ----------
    def generate(self):
        self.tiles = [[GRASS for _ in range(self.w)] for _ in range(self.h)]

        # граница
        for x in range(self.w):
            self.tiles[0][x] = TREE
            self.tiles[self.h - 1][x] = TREE
        for y in range(self.h):
            self.tiles[y][0] = TREE
            self.tiles[y][self.w - 1] = TREE

        rng = random.Random(7)
        # Увеличили количество деревьев с 110 до 350, чтобы лес был густым
        for _ in range(350):
            tx, ty = rng.randint(2, self.w - 3), rng.randint(2, self.h - 3)
            if self.tiles[ty][tx] == GRASS:
                self.tiles[ty][tx] = TREE

        # озеро (сдвинуто на юго-восток)
        for ty in range(50, 70):
            for tx in range(60, 85):
                if (tx - 72) ** 2 + (ty - 60) ** 2 < 49:  # Радиус 7
                    self.tiles[ty][tx] = WATER

        # замок-арена (остается на северо-западе)
        for ty in range(2, 10):
            for tx in range(2, 13):
                if ty in (2, 9) or tx in (2, 12):
                    self.tiles[ty][tx] = STONE
                else:
                    self.tiles[ty][tx] = DARK_FLOOR
        self.tiles[9][7] = GATE  # ворота

        # --- ДЕРЕВНЯ (центр карты) ---
        # Расчищаем большую площадь от деревьев под деревню
        self.clear_area(55, 48, 10)

        # Дом 1 (слева)
        for ty in range(45, 48):
            for tx in range(51, 54):
                self.tiles[ty][tx] = HOUSE

        # Дом 2 (справа)
        for ty in range(44, 47):
            for tx in range(57, 61):
                self.tiles[ty][tx] = HOUSE

        # Дом 3 (снизу)
        for ty in range(50, 54):
            for tx in range(55, 58):
                self.tiles[ty][tx] = HOUSE
        # -----------------------------

        # чистим площадки под ключевые объекты
        for cx, cy, r in [(50, 65, 4), (48, 65, 2), (85, 30, 2),
                          (72, 60, 2), (15, 40, 2), (7, 12, 2)]:
            self.clear_area(cx, cy, r)

    def clear_area(self, cx, cy, r):
        for ty in range(cy - r, cy + r + 1):
            for tx in range(cx - r, cx + r + 1):
                if 1 <= tx < self.w - 1 and 1 <= ty < self.h - 1:
                    self.tiles[ty][tx] = GRASS

    # ---------- коллизии ----------
    def is_walkable_px(self, px, py):
        tx, ty = int(px // TILE), int(py // TILE)
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False
        t = self.tiles[ty][tx]
        if t == GATE:
            return self.gate_open
        return t in (GRASS, FLOOR, DARK_FLOOR)

    def is_walkable_rect(self, x, y, w, h):
        tx0, ty0 = int(x // TILE), int(y // TILE)
        tx1, ty1 = int((x + w - 1) // TILE), int((y + h - 1) // TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if not self.is_walkable_px(tx * TILE + TILE // 2,
                                           ty * TILE + TILE // 2):
                    return False
        return True

    # ---------- отрисовка ----------
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
                if t == GRASS:
                    pygame.draw.rect(screen, COLOR_GRASS, r)
                    pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 8, sy + 8, 4, 4))
                    pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 22, sy + 18, 4, 4))
                elif t == TREE:
                    pygame.draw.rect(screen, COLOR_GRASS_DARK, r)
                    pygame.draw.circle(screen, COLOR_TREE,
                                       (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2)
                    pygame.draw.circle(screen, (20, 60, 25),
                                       (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2, 2)
                elif t == WATER:
                    pygame.draw.rect(screen, COLOR_WATER, r)
                    pygame.draw.line(screen, (120, 180, 240),
                                     (sx + 8, sy + 16), (sx + 24, sy + 16), 2)
                elif t == STONE:
                    pygame.draw.rect(screen, COLOR_STONE, r)
                    pygame.draw.rect(screen, (60, 60, 70), r, 2)
                elif t == DARK_FLOOR:
                    pygame.draw.rect(screen, COLOR_DARK_FLOOR, r)
                elif t == HOUSE:
                    # Стены
                    pygame.draw.rect(screen, COLOR_HOUSE, r)
                    # Крыша (верхняя половина тайла)
                    pygame.draw.rect(screen, COLOR_ROOF, (sx, sy, TILE, TILE // 2))
                    # Контур, чтобы дом выделялся
                    pygame.draw.rect(screen, (40, 20, 10), r, 1)
                elif t == GATE:
                    pygame.draw.rect(screen, COLOR_STONE, r)
                    color = (90, 200, 100) if self.gate_open else COLOR_GATE
                    pygame.draw.rect(screen, color, (sx + 6, sy + 4, TILE - 12, TILE - 8), 3)