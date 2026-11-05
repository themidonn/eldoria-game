"""
world/dungeon.py — Подземелье (второй уровень).

Большая зала с колоннами 2×2 и факелами на стенах по периметру.
Вход/выход — лестница вверх в левом нижнем углу.

Структура как у World (w, h, tiles, is_walkable_*, draw) —
благодаря этому game.py может переключать карты прозрачно.
"""

import math
import pygame
from settings import *


class Dungeon:

    # ============================================================
    #   КОНСТАНТЫ
    # ============================================================
    # Размер зала в тайлах
    WIDTH_TILES  = 40
    HEIGHT_TILES = 25

    # Отступ стен от края (в тайлах) — всё, что ближе, это стена
    WALL_MARGIN = 2

    # Колонны: расставлены в узлах сетки с шагом
    PILLAR_STEP = 5
    PILLAR_SIZE = 2              # 2×2 тайла

    # Факелы на стенах: первый на расстоянии, шаг между ними
    TORCH_START = 5
    TORCH_STEP  = 6

    # Цвета огня (3 слоя)
    FIRE_OUTER = (255, 80, 20)   # красный
    FIRE_MID   = (255, 160, 40)  # оранжевый
    FIRE_INNER = (255, 240, 120) # жёлтый
    TORCH_STICK = (80, 50, 30)   # деревянная палочка

    # Свечение факела (готовый Surface 80×80)
    GLOW_SIZE   = 80
    GLOW_INNER  = (255, 200, 80, 60)   # центр
    GLOW_OUTER  = (255, 140, 50, 40)   # ореол

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self):
        self.w = self.WIDTH_TILES
        self.h = self.HEIGHT_TILES
        self.gate_open = False       # для совместимости с World
        self.time = 0                # для анимации мерцания
        self.torches = []            # позиции факелов: [(tx, ty), ...]

        # Свечение кэшируется один раз — потом только blit
        self._glow_surf = self._make_glow()

        self.generate()

    def _make_glow(self):
        """Создаёт готовую Surface свечения факела (один раз)."""
        surf = pygame.Surface((self.GLOW_SIZE, self.GLOW_SIZE), pygame.SRCALPHA)
        half = self.GLOW_SIZE // 2
        pygame.draw.circle(surf, self.GLOW_OUTER, (half, half), 35)
        pygame.draw.circle(surf, self.GLOW_INNER, (half, half), 20)
        return surf

    # ============================================================
    #   ГЕНЕРАЦИЯ
    # ============================================================
    def generate(self):
        self._generate_walls_and_floor()
        self._generate_pillars()
        self._generate_stairs()
        self._generate_torches()

    def _generate_walls_and_floor(self):
        """Сначала всё стены, потом выкапываем зал с отступом WALL_MARGIN."""
        self.tiles = [[STONE for _ in range(self.w)] for _ in range(self.h)]

        m = self.WALL_MARGIN
        for ty in range(m, self.h - m):
            for tx in range(m, self.w - m):
                self.tiles[ty][tx] = DARK_FLOOR

    def _generate_pillars(self):
        """Ставит колонны 2×2 в узлах сетки с шагом PILLAR_STEP."""
        step = self.PILLAR_STEP
        size = self.PILLAR_SIZE
        m = self.WALL_MARGIN

        for ty in range(step, self.h - step, step):
            for tx in range(step, self.w - step, step):
                for dy in range(size):
                    for dx in range(size):
                        py = ty + dy
                        px = tx + dx
                        # Не залезаем в стены
                        if m <= px < self.w - m and m <= py < self.h - m:
                            self.tiles[py][px] = STONE

    def _generate_stairs(self):
        """Лестница вверх (выход) — левый нижний угол зала."""
        self.tiles[self.h - 4][4] = STAIRS_UP

    def _generate_torches(self):
        """Факелы по периметру зала: сверху, снизу, слева, справа."""
        start = self.TORCH_START
        step  = self.TORCH_STEP

        # Верхняя стена (стена на y=1, пол с y=2)
        for tx in range(start, self.w - start, step):
            self.torches.append((tx, 1))

        # Нижняя стена (стена на y=h-2)
        for tx in range(start, self.w - start, step):
            self.torches.append((tx, self.h - 2))

        # Левая стена (x=1)
        for ty in range(start + 1, self.h - start - 1, step):
            self.torches.append((1, ty))

        # Правая стена (x=w-2)
        for ty in range(start + 1, self.h - start - 1, step):
            self.torches.append((self.w - 2, ty))

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, dt):
        """Обновляет фазу мерцания факелов."""
        self.time += dt * 0.005

    # ============================================================
    #   КОЛЛИЗИИ
    # ============================================================
    def is_walkable_px(self, px, py):
        """Проходим ли пиксель (px, py)? Пол и лестница — да, стены — нет."""
        tx, ty = int(px // TILE), int(py // TILE)
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False
        return self.tiles[ty][tx] in (DARK_FLOOR, FLOOR, GRASS, STAIRS_UP)

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
        self._draw_tiles(screen, cam)
        self._draw_torches(screen, cam)

    def _draw_tiles(self, screen, cam):
        """Рисует видимые тайлы: стены, пол, лестницу."""
        x0 = max(0, int(cam.x) // TILE)
        y0 = max(0, int(cam.y) // TILE)
        x1 = min(self.w, (int(cam.x) + WIDTH) // TILE + 2)
        y1 = min(self.h, (int(cam.y) + HEIGHT) // TILE + 2)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                t = self.tiles[ty][tx]
                sx = int(tx * TILE - cam.x)
                sy = int(ty * TILE - cam.y)
                r = (sx, sy, TILE, TILE)

                if t == STONE:
                    pygame.draw.rect(screen, COLOR_STONE, r)
                    pygame.draw.rect(screen, (60, 60, 70), r, 2)
                elif t == DARK_FLOOR:
                    pygame.draw.rect(screen, COLOR_DARK_FLOOR, r)
                    # Кирпичики на полу
                    pygame.draw.line(screen, (50, 35, 35),
                                     (sx, sy + TILE // 2),
                                     (sx + TILE, sy + TILE // 2), 1)
                    pygame.draw.line(screen, (50, 35, 35),
                                     (sx + TILE // 2, sy),
                                     (sx + TILE // 2, sy + TILE // 2), 1)
                elif t == STAIRS_UP:
                    self._draw_stairs(screen, sx, sy)

    def _draw_stairs(self, screen, sx, sy):
        """Отрисовка лестницы вверх (3 ступеньки + красная стрелка)."""
        r = (sx, sy, TILE, TILE)
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

    def _draw_torches(self, screen, cam):
        """Рисует все факелы: свечение, палочка, огонь (3 слоя)."""
        for torch_tx, torch_ty in self.torches:
            tx_screen = int(torch_tx * TILE - cam.x) + TILE // 2
            ty_screen = int(torch_ty * TILE - cam.y) + TILE // 2

            # Оптимизация: не рисуем, если далеко за экраном
            if not (-TILE * 2 < tx_screen < WIDTH + TILE * 2 and
                    -TILE * 2 < ty_screen < HEIGHT + TILE * 2):
                continue

            # Смещение огня — синус с разной фазой для каждого факела
            flicker_offset = math.sin(self.time + torch_tx * 0.7) * 2

            # --- Свечение (готовый Surface) ---
            screen.blit(self._glow_surf,
                        (tx_screen - self.GLOW_SIZE // 2,
                         ty_screen - self.GLOW_SIZE // 2))

            # --- Палочка ---
            pygame.draw.rect(screen, self.TORCH_STICK,
                             (tx_screen - 2, ty_screen + 2, 4, 12))

            # --- Огонь (3 слоя, смещён мерцанием) ---
            fire_x = tx_screen + int(flicker_offset)
            fire_y = ty_screen - 4 + int(flicker_offset / 2)
            pygame.draw.circle(screen, self.FIRE_OUTER, (fire_x, fire_y), 6)
            pygame.draw.circle(screen, self.FIRE_MID,   (fire_x, fire_y), 4)
            pygame.draw.circle(screen, self.FIRE_INNER, (fire_x, fire_y), 2)