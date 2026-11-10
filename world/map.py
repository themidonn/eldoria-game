"""
world/map.py — Главный мир (уровень 1).

Большая карта 180×130 тайлов: лес, озеро, замок на северо-западе,
деревня в центре, колодец-вход в подземелье, горная гряда на севере
(пики, перевалы, долины) и болото на юго-западе.

Генерация детерминирована (random.Random(7)) — карта
всегда одинаковая, чтобы игрок мог ориентироваться.

Используется в game.py:
  - _reset() — создаёт экземпляр (main_world)
  - _update_level_1() — is_walkable_rect
  - _draw_level_1() — draw
  - save_progress() / load_progress() — сохраняет только gate_open

Поиск по файлу: Ctrl+F "region"
"""

import random
import pygame
from settings import *


# region КЛАСС: World
class World:

    # region КОНСТАНТЫ
    # Размер карты в тайлах
    WIDTH_TILES  = 180
    HEIGHT_TILES = 130

    # Количество деревьев (случайно раскиданы по траве).
    # При 180×130 = 23400 тайлов и TREE_COUNT = 1100 деревьями
    # станет ~4.7% травы — карта не «забита», но и не пустая.
    TREE_COUNT = 1100

    # Фиксированные seed → одинаковая карта при каждом запуске.
    # Игрок может запомнить расположение и ориентироваться.
    RANDOM_SEED = 7
    MOUNTAIN_SEED = 8
    SWAMP_SEED = 9

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

    # --- Горы (север) ---
    # Естественная гряда: пики (стена), перевалы (проход снизу),
    # долины (широкий проход). Не более 3 горных блоков подряд —
    # гарантия, что стена не станет непроходимой.
    MOUNTAIN_X_MIN, MOUNTAIN_X_MAX = 20, 175
    MOUNTAIN_Y_MIN, MOUNTAIN_Y_MAX = 2, 15
    MOUNTAIN_MAX_BLOCKS_BEFORE_VALLEY = 3

    # --- Болото (юго-запад) ---
    SWAMP_X_MIN, SWAMP_X_MAX = 5, 50
    SWAMP_Y_MIN, SWAMP_Y_MAX = 85, 125

    # Зоны, которые нужно расчистить под ключевые объекты.
    # ВАЖНО: r=4 у Кристаллов Леса и Руин — под стражей на ±3 по X.
    # При r=2 стражи на крайних offset'ах (±3) оказывались за зоной
    # расчистки: если там оказывалось дерево — страж не спавнился
    # (см. game.py, _spawn_crystal_and_guards). Итог — «неполная охрана»
    # у двух кристаллов. r=4 гарантирует, что все offset'ы покрыты.
    # У Кристалла Воды стражи на ±2 — r=2 достаточно.
    CLEAR_ZONES = [
        (50, 65, 4),   # старт + Старейшина (x=46..54, y=61..69)
        (85, 30, 4),   # кристалл леса + стражи на (82,32)/(85,32)/(88,32)
        (72, 50, 2),   # кристалл озера (стражи ±2, r=2 покрывает)
        (15, 40, 4),   # кристалл руин + стражи на (12,42)/(15,42)/(18,42)
        (7, 12, 2),    # подход к воротам замка (y=10..14, ворота на y=9)
    ]
    # endregion

    # region КОНСТРУКТОР
    def __init__(self):
        self.w = self.WIDTH_TILES
        self.h = self.HEIGHT_TILES
        self.gate_open = False

        # Ленивый кэш трещин на горных тайлах: {(tx, ty): [(x1,y1,x2,y2), ...]}.
        # Заполняется в _draw_mountain при первом появлении тайла в кадре.
        # Без кэша random.Random(tx*1013 + ty*7919) создавался бы каждый кадр
        # на каждый видимый горный тайл (~200 объектов/кадр — заметно в WASM).
        self._mountain_cracks_cache = {}

        self.generate()
    # endregion

    # region ГЕНЕРАЦИЯ
    def generate(self):
        """
        Полная генерация в порядке наложения слоёв:
        границы → деревья → горы → болото → озеро → замок →
        деревня → очистка ключевых зон.

        Порядок важен: деревня и очистка идут последними, чтобы
        гарантированно расчистить площадки под объекты (иначе
        дерево могло бы «сесть» на точку спавна кристалла).
        """
        self.tiles = [[GRASS for _ in range(self.w)] for _ in range(self.h)]
        self._generate_borders()
        self._generate_trees()
        self._generate_mountains()
        self._generate_swamp()
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
        """
        Раскидываем TREE_COUNT деревьев случайно по траве.

        Границы 2..w-3 и 2..h-3 — «буферная зона» в 1 тайл от TREE-рамки:
        деревья никогда не встают вплотную к краю карты, оставляя
        визуально ровную кромку.
        """
        rng = random.Random(self.RANDOM_SEED)
        for _ in range(self.TREE_COUNT):
            tx = rng.randint(2, self.w - 3)
            ty = rng.randint(2, self.h - 3)
            if self.tiles[ty][tx] == GRASS:
                self.tiles[ty][tx] = TREE

    def _generate_mountains(self):
        """
        Естественная горная гряда с пиками, перевалами и долинами.

        Идём по X слева направо. Для каждого блока выбираем:
        - Пик (55%): полная стена y=2..15, ширина 2..4
        - Перевал (25%): гора сверху y=2..(2+4..8), снизу — проход,
          ширина 1..3
        - Долина (20%): полный проход y=2..15, ширина 3..6

        Гарантия проходимости: не более 3 горных блоков подряд
        (пик/перевал), затем принудительная долина.

        force_valley=True — всегда идёт в else (долина), потому что
        первые два условия содержат `not force_valley`.

        rng.random() вызывается на каждой итерации (даже при
        force_valley=True) — это сознательно: последовательность
        Random(MOUNTAIN_SEED) должна быть стабильной.
        """
        rng = random.Random(self.MOUNTAIN_SEED)

        x = self.MOUNTAIN_X_MIN
        blocks_since_valley = 0

        while x <= self.MOUNTAIN_X_MAX:
            force_valley = (blocks_since_valley
                            >= self.MOUNTAIN_MAX_BLOCKS_BEFORE_VALLEY)
            roll = rng.random()

            # --- Пик: полная стена ---
            if not force_valley and roll < 0.55:
                width = rng.randint(2, 4)
                for dx in range(width):
                    if x + dx > self.MOUNTAIN_X_MAX:
                        break
                    for ty in range(self.MOUNTAIN_Y_MIN,
                                    self.MOUNTAIN_Y_MAX + 1):
                        self.tiles[ty][x + dx] = MOUNTAIN
                x += width
                blocks_since_valley += 1

            # --- Перевал: гора сверху, проход снизу ---
            elif not force_valley and roll < 0.80:
                width = rng.randint(1, 3)
                peak_h = rng.randint(4, 8)
                for dx in range(width):
                    if x + dx > self.MOUNTAIN_X_MAX:
                        break
                    for ty in range(self.MOUNTAIN_Y_MIN,
                                    self.MOUNTAIN_Y_MIN + peak_h + 1):
                        if ty <= self.MOUNTAIN_Y_MAX:
                            self.tiles[ty][x + dx] = MOUNTAIN
                x += width
                blocks_since_valley += 1

            # --- Долина: широкий проход (сбрасывает счётчик) ---
            else:
                gap = rng.randint(3, 6)
                x += gap
                blocks_since_valley = 0

    def _generate_swamp(self):
        """
        Болото на юго-западе с рваными краями (неровный круг).

        Три зоны:
          dist < 0.6·max_r        → SWAMP (ядро, 100%)
          0.6·max_r .. 0.9·max_r  → SWAMP с вероятностью 70%
          0.9·max_r .. max_r      → SWAMP с вероятностью 30%
        Края получаются рваными за счёт вероятностного заполнения.
        """
        rng = random.Random(self.SWAMP_SEED)
        cx = (self.SWAMP_X_MIN + self.SWAMP_X_MAX) / 2
        cy = (self.SWAMP_Y_MIN + self.SWAMP_Y_MAX) / 2
        max_r = min(self.SWAMP_X_MAX - self.SWAMP_X_MIN,
                    self.SWAMP_Y_MAX - self.SWAMP_Y_MIN) / 2

        for ty in range(self.SWAMP_Y_MIN, self.SWAMP_Y_MAX + 1):
            for tx in range(self.SWAMP_X_MIN, self.SWAMP_X_MAX + 1):
                dx = tx - cx
                dy = ty - cy
                dist = (dx * dx + dy * dy) ** 0.5

                if dist < max_r * 0.6:
                    self.tiles[ty][tx] = SWAMP
                elif dist < max_r * 0.9 and rng.random() < 0.7:
                    self.tiles[ty][tx] = SWAMP
                elif dist < max_r and rng.random() < 0.3:
                    self.tiles[ty][tx] = SWAMP

    def _generate_lake(self):
        """
        Озеро круглой формы с центром в LAKE_CENTER_X/Y.

        Проверка границ 0 <= tx < self.w / 0 <= ty < self.h — защита
        от IndexError, если когда-нибудь LAKE_CENTER или LAKE_RADIUS
        изменят так, что круг выйдет за край карты.
        """
        for ty in range(self.LAKE_CENTER_Y - self.LAKE_RADIUS - 2,
                        self.LAKE_CENTER_Y + self.LAKE_RADIUS + 2):
            for tx in range(self.LAKE_CENTER_X - self.LAKE_RADIUS - 2,
                            self.LAKE_CENTER_X + self.LAKE_RADIUS + 2):
                # --- Защита от выхода за границы карты ---
                if not (0 <= tx < self.w and 0 <= ty < self.h):
                    continue

                dx = tx - self.LAKE_CENTER_X
                dy = ty - self.LAKE_CENTER_Y
                if dx * dx + dy * dy < self.LAKE_RADIUS * self.LAKE_RADIUS:
                    self.tiles[ty][tx] = WATER

    def _generate_castle(self):
        """
        Замок с ареной босса: стены по периметру, пол внутри,
        ворота в нижней стене (GATE_Y = CASTLE_Y_MAX).

        Ворота открываются после сбора 3 кристаллов (gate_open = True).
        """
        for ty in range(self.CASTLE_Y_MIN, self.CASTLE_Y_MAX + 1):
            for tx in range(self.CASTLE_X_MIN, self.CASTLE_X_MAX + 1):
                if ty in (self.CASTLE_Y_MIN, self.CASTLE_Y_MAX) or \
                   tx in (self.CASTLE_X_MIN, self.CASTLE_X_MAX):
                    self.tiles[ty][tx] = STONE
                else:
                    self.tiles[ty][tx] = DARK_FLOOR

        self.tiles[self.GATE_Y][self.GATE_X] = GATE

    def _generate_village(self):
        """
        Деревня: расчистка площади, дома, колодец (вход в подземелье).

        Порядок важен: clear_area → дома → колодец. Колодец не попадает
        ни в один дом (проверено по координатам: дома на y=44..53,
        колодец на y=55), поэтому ставится последним.
        """
        self.clear_area(self.VILLAGE_CENTER_X, self.VILLAGE_CENTER_Y,
                        self.VILLAGE_CLEAR_RADIUS)

        for tx_min, tx_max, ty_min, ty_max in self.HOUSES:
            for ty in range(ty_min, ty_max + 1):
                for tx in range(tx_min, tx_max + 1):
                    self.tiles[ty][tx] = HOUSE

        self.tiles[self.WELL_Y][self.WELL_X] = STAIRS_DOWN

    def _clear_key_zones(self):
        """Расчищает маленькие площадки под кристаллы, зелья, камни лора."""
        for cx, cy, r in self.CLEAR_ZONES:
            self.clear_area(cx, cy, r)

    def clear_area(self, cx, cy, r):
        """
        Заполняет прямоугольник (cx±r, cy±r) травой.

        Границы 1..w-2 и 1..h-2 — рамка карты (TREE по периметру)
        остаётся нетронутой.
        """
        for ty in range(cy - r, cy + r + 1):
            for tx in range(cx - r, cx + r + 1):
                if 1 <= tx < self.w - 1 and 1 <= ty < self.h - 1:
                    self.tiles[ty][tx] = GRASS
    # endregion

    # region КОЛЛИЗИИ
    def is_walkable_px(self, px, py):
        """
        Проходим ли пиксель?

        Горы, деревья, вода, дома, стены — нет.
        Болото — да (замедляет только визуально, но проходимо).
        Ворота — только если gate_open (открыты после 3 кристаллов).

        FLOOR и STAIRS_UP в кортеже — защитный код: generate() их
        никогда не создаёт, но если когда-нибудь появится генератор
        подземелья поверх наземной карты — они не будут блокировать.
        Сейчас это «мёртвые» значения (см. _draw_tile — FLOOR там
        нет ветки отрисовки, так что при появлении FLOOR он будет
        проходим, но невидим; добавьте ветку при необходимости).
        """
        tx, ty = int(px // TILE), int(py // TILE)
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False

        t = self.tiles[ty][tx]

        # --- Ворота: проходимы только когда открыты ---
        if t == GATE:
            return self.gate_open

        return t in (GRASS, FLOOR, DARK_FLOOR, STAIRS_DOWN, STAIRS_UP, SWAMP)

    def is_walkable_rect(self, x, y, w, h):
        """
        Проходим ли весь прямоугольник (проверяет все перекрытые тайлы)?

        Для каждого перекрытого тайла проверяется его ЦЕНТР. Если хотя бы
        один центр — не walkable, весь прямоугольник отбраковывается.
        """
        tx0, ty0 = int(x // TILE), int(y // TILE)
        tx1, ty1 = int((x + w - 1) // TILE), int((y + h - 1) // TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if not self.is_walkable_px(tx * TILE + TILE // 2,
                                           ty * TILE + TILE // 2):
                    return False
        return True
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        """
        Рисует видимые тайлы (только то, что в кадре).

        +2 тайла запаса по каждой оси — чтобы на краю экрана
        не появлялась полоса пустоты при движении камеры.
        """
        x0 = max(0, int(cam.x) // TILE)
        y0 = max(0, int(cam.y) // TILE)
        x1 = min(self.w, (int(cam.x) + WIDTH) // TILE + 2)
        y1 = min(self.h, (int(cam.y) + HEIGHT) // TILE + 2)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                self._draw_tile(screen, cam, tx, ty)

    def _draw_tile(self, screen, cam, tx, ty):
        """
        Рендерит один тайл по его типу (диспетчер).

        Если тип тайла не покрыт ни одной веткой — тайл не рисуется.
        Сейчас это безопасно: generate() создаёт только перечисленные
        типы. FLOOR (в is_walkable_px) в _draw_tile не покрыт —
        добавьте ветку, если начнёте его генерировать.
        """
        t = self.tiles[ty][tx]
        sx = int(tx * TILE - cam.x)
        sy = int(ty * TILE - cam.y)
        r = (sx, sy, TILE, TILE)

        # --- Диспетчеризация по типу тайла ---
        if t == GRASS:
            self._draw_grass(screen, sx, sy, r)
        elif t == TREE:
            self._draw_tree(screen, sx, sy, r)
        elif t == WATER:
            self._draw_water(screen, sx, sy, r)
        elif t == STONE:
            self._draw_stone(screen, sx, sy, r)
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
        elif t == MOUNTAIN:
            self._draw_mountain(screen, tx, ty, sx, sy, r)
        elif t == SWAMP:
            self._draw_swamp(screen, sx, sy, r)

    # region Тайлы (каждый метод принимает screen, sx, sy, r)
    def _draw_grass(self, screen, sx, sy, r):
        """Трава: зелёный фон + две тёмные точки (травинки)."""
        pygame.draw.rect(screen, COLOR_GRASS, r)
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 8, sy + 8, 4, 4))
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (sx + 22, sy + 18, 4, 4))

    def _draw_tree(self, screen, sx, sy, r):
        """Дерево: тёмная трава под кроной + круг кроны + обводка."""
        pygame.draw.rect(screen, COLOR_GRASS_DARK, r)
        pygame.draw.circle(screen, COLOR_TREE,
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2)
        pygame.draw.circle(screen, (20, 60, 25),
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2, 2)

    def _draw_water(self, screen, sx, sy, r):
        """Вода: синий фон + светлая волна по центру."""
        pygame.draw.rect(screen, COLOR_WATER, r)
        pygame.draw.line(screen, (120, 180, 240),
                         (sx + 8, sy + 16), (sx + 24, sy + 16), 2)

    def _draw_stone(self, screen, sx, sy, r):
        """Каменная стена: серый блок + тёмная обводка."""
        pygame.draw.rect(screen, COLOR_STONE, r)
        pygame.draw.rect(screen, (60, 60, 70), r, 2)

    def _draw_house(self, screen, sx, sy, r):
        """Дом: стена + крыша (верхняя половина) + обводка."""
        pygame.draw.rect(screen, COLOR_HOUSE, r)
        pygame.draw.rect(screen, COLOR_ROOF, (sx, sy, TILE, TILE // 2))
        pygame.draw.rect(screen, (40, 20, 10), r, 1)

    def _draw_gate(self, screen, sx, sy, r):
        """Ворота: камень + цветной прямоугольник (зелёный если открыты)."""
        pygame.draw.rect(screen, COLOR_STONE, r)
        color = (90, 200, 100) if self.gate_open else COLOR_GATE
        pygame.draw.rect(screen, color,
                         (sx + 6, sy + 4, TILE - 12, TILE - 8), 3)

    def _draw_well(self, screen, sx, sy, r):
        """Колодец — вход в подземелье: тёмный круг внутри каменного."""
        pygame.draw.rect(screen, COLOR_GRASS_DARK, r)
        pygame.draw.circle(screen, COLOR_STONE,
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 2)
        pygame.draw.circle(screen, (20, 20, 30),
                           (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 8)

    def _draw_stairs_up(self, screen, sx, sy, r):
        """
        Лестница вверх (не спавнится в главном мире, но подстрахована:
        generate() никогда не ставит STAIRS_UP, а is_walkable_px его
        пропускает — на случай будущих генераторов).
        """
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

    def _draw_mountain(self, screen, tx, ty, sx, sy, r):
        """
        Горный тайл: скала с тенью и бликом (без снега).

        Трещины — детерминированные по (tx, ty), кэшируются в
        _mountain_cracks_cache при первом появлении тайла в кадре.
        Раньше Random(tx*1013 + ty*7919) пересоздавался каждый кадр
        на каждый видимый тайл — это был главный перф-баг модуля.
        """
        # 1. База — камень
        pygame.draw.rect(screen, COLOR_MOUNTAIN, r)

        # 2. Тень справа — широкая (14 px) и тёмная
        pygame.draw.polygon(screen, COLOR_MOUNTAIN_SHADOW, [
            (sx + TILE - 14, sy),
            (sx + TILE, sy),
            (sx + TILE, sy + TILE),
            (sx + TILE - 14, sy + TILE),
        ])

        # 3. Блик слева — светлый, тёплый (5 px)
        pygame.draw.polygon(screen, COLOR_MOUNTAIN_LIGHT, [
            (sx, sy),
            (sx + 5, sy),
            (sx + 5, sy + TILE),
            (sx, sy + TILE),
        ])

        # 4. Трещины — из кэша (или вычисляются один раз)
        for x1, y1, x2, y2 in self._get_mountain_cracks(tx, ty):
            pygame.draw.line(screen, COLOR_MOUNTAIN_DARK,
                             (sx + x1, sy + y1),
                             (sx + x2, sy + y2), 2)

        # 5. Обводка
        pygame.draw.rect(screen, COLOR_MOUNTAIN_DARK, r, 2)

    def _get_mountain_cracks(self, tx, ty):
        """
        Возвращает список трещин [(x1_off, y1_off, x2_off, y2_off), ...]
        для тайла (tx, ty). Координаты — СМЕЩЕНИЯ внутри тайла (0..TILE).

        Ленивый кэш: для каждого (tx, ty) считается один раз за игру.
        Сид (tx*1013 + ty*7919) — детерминированный, привязан к мировым
        координатам тайла, поэтому трещины не «прыгают» при движении камеры.

        Замечание: randint(a, b) в Python = a + randbelow(b - a + 1),
        поэтому randint(sx+14, sx+TILE-16) даёт sx + 14 + offset —
        то есть абсолютная позиция едет с камерой, а смещение внутри
        тайла стабильно. Здесь мы храним именно смещение.
        """
        key = (tx, ty)
        cached = self._mountain_cracks_cache.get(key)
        if cached is not None:
            return cached

        rng = random.Random(tx * 1013 + ty * 7919)
        cracks = []
        for _ in range(2):
            x1 = rng.randint(14, TILE - 16)
            y1 = rng.randint(12, TILE - 20)
            x2 = x1 + rng.randint(-6, 6)
            y2 = y1 + rng.randint(6, 14)
            cracks.append((x1, y1, x2, y2))

        self._mountain_cracks_cache[key] = cracks
        return cracks

    def _draw_swamp(self, screen, sx, sy, r):
        """Болото: тёмно-зелёная вода с пузырями."""
        pygame.draw.rect(screen, COLOR_SWAMP, r)
        pygame.draw.circle(screen, COLOR_SWAMP_BUBBLE, (sx + 10, sy + 12), 3)
        pygame.draw.circle(screen, COLOR_SWAMP_BUBBLE, (sx + 26, sy + 24), 2)
        pygame.draw.circle(screen, COLOR_SWAMP_BUBBLE, (sx + 18, sy + 32), 2)
    # endregion

    # endregion (ОТРИСОВКА)
# endregion (World)