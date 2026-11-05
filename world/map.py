"""
world/map.py — Главный мир (уровень 1).

Большая карта 100×75 тайлов: лес, озеро, замок на северо-западе,
деревня в центре, колодец-вход в подземелье.

Генерация детерминирована (random.Random(7)) — карта
всегда одинаковая, чтобы игрок мог ориентироваться.
"""

import random
import pygame
from settings import *


class World:

    # ============================================================
    #   КОНСТАНТЫ
    # ============================================================
    # Размер карты в тайлах
    WIDTH_TILES  = 100
    HEIGHT_TILES = 75

    # Количество деревьев (случайно раскиданы по траве)
    TREE_COUNT = 350
    RANDOM_SEED = 7               # фиксированный seed → одинаковая карта

    # --- Озеро (юго-восток) ---
    LAKE_CENTER_X = 72
    LAKE_CENTER_Y = 60
    LAKE_RADIUS   = 7

    # --- Замок (северо-запад) ---
    CASTLE_X_MIN, CASTLE_X_MAX = 2, 12
    CASTLE_Y_MIN, CASTLE_Y_MAX = 2, 9
    GATE_X, GATE_Y = 7, 9         # координаты ворот в стене

    # --- Деревня (центр) ---
    VILLAGE_CENTER_X, VILLAGE_CENTER_Y = 55, 48
    VILLAGE_CLEAR_RADIUS = 10     # радиус расчистки от деревьев

    # Дома: (tx_min, tx_max, ty_min, ty_max) — прямоугольники
    HOUSES = [
        (51, 53, 45, 47),   # дом 1 (слева)
        (57, 60, 44, 46),   # дом 2 (справа)
        (55, 57, 50, 53),   # дом 3 (снизу)
    ]
    WELL_X, WELL_Y = 60, 55       # колодец — вход в подземелье

    # Зоны, которые нужно расчистить под ключевые объекты
    CLEAR_ZONES = [
        (50, 65, 4),   # старт + Старейшина
        (48, 65, 2),   # Старейшина
        (85, 30, 2),   # кристалл леса
        (72, 50, 2),   # кристалл озера
        (15, 40, 2),   # кристалл руин
        (7, 12, 2),    # ворота замка
    ]

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self):
        self.w = self.WIDTH_TILES
        self.h = self.HEIGHT_TILES
        self.gate_open = False
        self.generate()

    # ============================================================
    #   ГЕНЕРАЦИЯ
    # ============================================================
    def generate(self):
        """Полная генерация карты: границы → деревья → озеро → замок → деревня → очистка."""
        self.tiles = [[GRASS for _ in range(self.w)] for _ in range(self.h)]
        self._generate_borders()
        self._generate_trees()
        self._generate_lake()
        self._generate_castle()
        self._generate_village()
        self._clear_key_zones()

    def _generate_borders(self):
        """Обводим карту деревьями по периметру (чтобы нельзя было выйти за край)."""
        for x in range(self.w):
            self.tiles[0][x] = TREE
            self.tiles[self.h - 1][x] = TREE
        for y in range(self.h):
            self.tiles[y][0] = TREE
            self.tiles[y][self.w - 1] = TREE

    def _generate_trees(self):
        """Раскидываем TREE_COUNT деревьев случайно по траве."""
        rng = random.Random(self.RANDOM_SEED)
        for _ in range(self.TREE_COUNT):
            tx = rng.randint(2, self.w - 3)
            ty = rng.randint(2, self.h - 3)
            if self.tiles[ty][tx] == GRASS:
                self.tiles[ty][tx] = TREE

    def _generate_lake(self):
        """Озеро круглой формы с центром в LAKE_CENTER_X/Y."""
        for ty in range(self.LAKE_CENTER_Y - self.LAKE_RADIUS - 2,
                        self.LAKE_CENTER_Y + self.LAKE_RADIUS + 2):
            for tx in range(self.LAKE_CENTER_X - self.LAKE_RADIUS - 2,
                            self.LAKE_CENTER_X + self.LAKE_RADIUS + 2):
                # Сравниваем квадраты расстояний — без корня (быстрее)
                dx = tx - self.LAKE_CENTER_X
                dy = ty - self.LAKE_CENTER_Y
                if dx * dx + dy * dy < self.LAKE_RADIUS * self.LAKE_RADIUS:
                    self.tiles[ty][tx] = WATER

    def _generate_castle(self):
        """Замок с ареной босса: стены по периметру, пол внутри, ворота в стене."""
        for ty in range(self.CASTLE_Y_MIN, self.CASTLE_Y_MAX + 1):
            for tx in range(self.CASTLE_X_MIN, self.CASTLE_X_MAX + 1):
                # Стены — верхняя/нижняя/левая/правая
                if ty in (self.CASTLE_Y_MIN, self.CASTLE_Y_MAX) or \
                   tx in (self.CASTLE_X_MIN, self.CASTLE_X_MAX):
                    self.tiles[ty][tx] = STONE
                else:
                    self.tiles[ty][tx] = DARK_FLOOR

        # Ворота в нижней стене
        self.tiles[self.GATE_Y][self.GATE_X] = GATE

    def _generate_village(self):
        """Деревня: расчистка площади, дома, колодец."""
        # Расчищаем площадь от деревьев
        self.clear_area(self.VILLAGE_CENTER_X, self.VILLAGE_CENTER_Y,
                        self.VILLAGE_CLEAR_RADIUS)

        # Дома
        for tx_min, tx_max, ty_min, ty_max in self.HOUSES:
            for ty in range(ty_min, ty_max + 1):
                for tx in range(tx_min, tx_max + 1):
                    self.tiles[ty][tx] = HOUSE

        # Колодец — вход в подземелье
        self.tiles[self.WELL_Y][self.WELL_X] = STAIRS_DOWN

    def _clear_key_zones(self):
        """Расчищает маленькие площадки под кристаллы, зелья, камни лора."""
        for cx, cy, r in self.CLEAR_ZONES:
            self.clear_area(cx, cy, r)

    def clear_area(self, cx, cy, r):
        """Заполняет прямоугольник (cx±r, cy±r) травой (без краёв карты)."""
        for ty in range(cy - r, cy + r + 1):
            for tx in range(cx - r, cx + r + 1):
                if 1 <= tx < self.w - 1 and 1 <= ty < self.h - 1:
                    self.tiles[ty][tx] = GRASS

    # ============================================================
    #   КОЛЛИЗИИ
    # ============================================================
    def is_walkable_px(self, px, py):
        """Проходим ли пиксель? Ворота зависят от gate_open."""
        tx, ty = int(px // TILE), int(py // TILE)
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False

        t = self.tiles[ty][tx]
        if t == GATE:
            return self.gate_open
        return t in (GRASS, FLOOR, DARK_FLOOR, STAIRS_DOWN, STAIRS_UP)

    def is_walkable_rect(self, x, y, w, h):
        """Проходим ли весь прямоугольник (проверяет все перекрытые тайлы)?"""
        tx0, ty0 = int(x // TILE), int(y // TILE)
        tx1, ty1 = int((x + w - 1) // TILE), int((y + h - 1) // TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if not self.is_walkable_px(tx * TILE + TILE // 2,
                                           ty * TILE + TILE // 2):
                    return False
        return True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        """Рисует видимые тайлы (только то, что в кадре)."""
        x0 = max(0, int(cam.x) // TILE)
        y0 = max(0, int(cam.y) // TILE)
        x1 = min(self.w, (int(cam.x) + WIDTH) // TILE + 2)
        y1 = min(self.h, (int(cam.y) + HEIGHT) // TILE + 2)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                self._draw_tile(screen, cam, tx, ty)

    def _draw_tile(self, screen, cam, tx, ty):
        """Рендерит один тайл по его типу."""
        t = self.tiles[ty][tx]
        sx = int(tx * TILE - cam.x)
        sy = int(ty * TILE - cam.y)
        r = (sx, sy, TILE, TILE)

        if t == GRASS:
            self._draw_grass(screen, sx, sy, r)
        elif t == TREE:
            self._draw_tree(screen, sx, sy, r)
        elif t == WATER:
            self._draw_water(screen, sx, sy, r)
        elif t == STONE:
            self._draw_stone(screen, r)
        elif t == DARK_FLOOR:
            pygame.draw.rect(screen, COLOR_DARK_FLOOR, r)
        elif t == HOUSE:
            self._draw_house(screen, sx, sy, r)
        elif t == GATE:
            self._draw_gate(screen, sx, sy, r)
        elif t == STAIRS_DOWN:
            self._draw_well(screen, sx, sy, r)
        elif t == STAIRS_UP:
            self._draw_stairs_up(screen, sx, sy, r)

    def _draw_grass(self, screen, sx, sy, r):
        pygame.draw.rect(screen, COLOR_GRASS, r)
        # Две «травинки» для текстуры
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 8, sy + 8, 4, 4))
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 22, sy + 18, 4, 4))

    def _draw_tree(self, screen, sx, sy, r):
        pygame.draw.rect(screen, COLOR_GRASS_DARK, r)
        pygame.draw.circle(screen, COLOR_TREE,
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2)
        pygame.draw.circle(screen, (20, 60, 25),
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2, 2)

    def _draw_water(self, screen, sx, sy, r):
        pygame.draw.rect(screen, COLOR_WATER, r)
        pygame.draw.line(screen, (120, 180, 240),
                         (sx + 8, sy + 16), (sx + 24, sy + 16), 2)

    def _draw_stone(self, screen, r):
        pygame.draw.rect(screen, COLOR_STONE, r)
        pygame.draw.rect(screen, (60, 60, 70), r, 2)

    def _draw_house(self, screen, sx, sy, r):
        # Стены
        pygame.draw.rect(screen, COLOR_HOUSE, r)
        # Крыша (верхняя половина)
        pygame.draw.rect(screen, COLOR_ROOF, (sx, sy, TILE, TILE // 2))
        # Обводка
        pygame.draw.rect(screen, (40, 20, 10), r, 1)

    def _draw_gate(self, screen, sx, sy, r):
        pygame.draw.rect(screen, COLOR_STONE, r)
        color = (90, 200, 100) if self.gate_open else COLOR_GATE
        pygame.draw.rect(screen, color,
                         (sx + 6, sy + 4, TILE - 12, TILE - 8), 3)

    def _draw_well(self, screen, sx, sy, r):
        """Колодец — вход в подземелье."""
        pygame.draw.rect(screen, COLOR_GRASS_DARK, r)
        pygame.draw.circle(screen, COLOR_STONE,
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2)
        pygame.draw.circle(screen, (20, 20, 30),
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 8)

    def _draw_stairs_up(self, screen, sx, sy, r):
        """Лестница вверх (не спавнится в главном мире, но подстрахована)."""
        pygame.draw.rect(screen, COLOR_STONE, r)
        for i in range(3):
            y = sy + 6 + i * 10
            pygame.draw.line(screen, (50, 50, 60),
                             (sx + 6, y), (sx + TILE - 6, y), 3)
        pygame.draw.polygon(screen, COLOR_STAIRS_UP, [
            (sx + TILE // 2,     sy + 8),
            (sx + TILE // 2 - 6, sy + 18),
            (sx + TILE // 2 + 6, sy + 18),
        ])