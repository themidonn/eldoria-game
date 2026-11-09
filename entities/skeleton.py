"""
entities/skeleton.py — Скелет: медленный, но крепкий враг.

4 HP, не отбрасывается мечом (тяжёлый). Патрулирует вокруг своей
стартовой точки. При приближении игрока (< 220 px) — переключается
в преследование. Обитает в подземелье, охраняет Короля Скелетов.

Используется в game.py:
  - _ensure_dungeon() — создаёт 4 скелета вокруг арены с боссом
  - _update_level_2() — update + take_damage
  - _draw_level_2() — draw

Поведение:
  - Игрок далеко (> 220 px):
      * если скелет ушёл от home — возвращается (порог 8 px)
      * если дома — патрулирует влево-вправо (±20 px от home_x)
  - Игрок близко (< 220 px): преследует с полной скоростью
"""

import pygame


class Skeleton:

    # ============================================================
    #   ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    # ============================================================
    BONE   = (220, 220, 200)     # кости
    BONE_D = (140, 140, 120)     # тень костей
    DARK   = (30, 30, 40)        # глазницы

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, hp=4):
        # --- Позиция и размеры ---
        self.x = float(x)
        self.y = float(y)
        self.w = self.h = 28

        # --- Здоровье ---
        self.hp = self.max_hp = hp

        # --- Движение ---
        # 0.9 px/кадр — медленнее слизня (1.3) и мыши (1.8).
        # Скелет «тяжёлый»: его легко обойти, но больно бить (4 HP).
        self.speed = 0.9

        # --- Состояние ---
        self.hit_flash = 0           # мс — красная вспышка при ударе
        self.dead = False

        # --- Патруль ---
        # home_x/home_y — стартовая точка, к ней скелет возвращается,
        # когда игрок уходит далеко.
        self.home_x = float(x)
        self.home_y = float(y)
        self.patrol_dir = 1          # 1 — вправо, -1 — влево
        self.patrol_timer = 0.0      # сек — до следующего разворота

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, player, world, dt):
        if self.dead:
            return

        # --- Таймеры ---
        # max(0, ...) — защита от отрицательного hit_flash при большом dt
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)

        # --- Расстояние до игрока ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        # --- Скорость (frame-independent) ---
        s = self.speed * (dt / 16.67)

        # ========================================================
        #   ПРЕСЛЕДОВАНИЕ (< 220 px)
        # ========================================================
        if dist < 220:
            # dist > 1 — защита от деления на ноль, если игрок
            # и скелет оказались в одной точке. В этом случае
            # скелет просто стоит — это нормально.
            if dist > 1:
                dx, dy = dx / dist, dy / dist
                self._try_move(self.x + dx * s, self.y + dy * s, world)

        # ========================================================
        #   ИГРОК ДАЛЕКО: возврат домой или патруль
        # ========================================================
        else:
            hdx = self.home_x - self.x
            hdy = self.home_y - self.y
            dist_home = (hdx * hdx + hdy * hdy) ** 0.5

            # Порог 8 px — примерно четверть размера скелета.
            # Если меньше — считаем, что «дома», и патрулируем.
            # Больше — возвращаемся (иначе скелет «дёргался» бы
            # вокруг home на каждом кадре).
            if dist_home > 8:
                # Скелет ушёл от стартовой точки — возвращаемся
                hdx, hdy = hdx / dist_home, hdy / dist_home
                self._try_move(self.x + hdx * s, self.y + hdy * s, world)
            else:
                # Дома — патруль влево-вправо в радиусе ±20 px от home_x.
                # Разворот каждые 2.5 сек или при столкновении со стеной.
                self.patrol_timer += dt / 1000.0
                if self.patrol_timer > 2.5:
                    self.patrol_timer = 0.0
                    self.patrol_dir *= -1

                # Патруль медленнее преследования (×0.5) — чтобы
                # скелет не «бегал» на месте, а именно патрулировал.
                new_x = self.x + self.patrol_dir * s * 0.5
                blocked = not world.is_walkable_rect(new_x, self.y, self.w, self.h)
                too_far = abs(new_x - self.home_x) > 20

                if blocked or too_far:
                    self.patrol_dir *= -1
                else:
                    self.x = new_x

    def _try_move(self, nx, ny, world):
        """
        Пытается сдвинуть скелета в (nx, ny) с проверкой коллизий по осям.

        X и Y проверяются отдельно — иначе скелет застревает в углах
        стен и не может «скользить» вдоль препятствия.
        """
        if world.is_walkable_rect(nx, self.y, self.w, self.h):
            self.x = nx
        if world.is_walkable_rect(self.x, ny, self.w, self.h):
            self.y = ny

    def take_damage(self, dmg, fx, fy):
        """
        Наносит урон. Скелета нельзя отбросить — параметры fx, fy
        сохранены для совместимости с API Slime / Bat / Boss,
        но не используются.
        """
        # Защита: нулевой/отрицательный урон не должен лечить скелета,
        # и мёртвого скелета нельзя «добить» второй раз.
        if dmg <= 0 or self.dead:
            return

        self.hp -= dmg
        self.hit_flash = 200
        if self.hp <= 0:
            self.dead = True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.dead:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Цвета (вспышка при ударе) ---
        color_bone   = (255, 150, 150) if self.hit_flash > 0 else self.BONE
        color_bone_d = (200, 100, 100) if self.hit_flash > 0 else self.BONE_D

        # --- Тело (позвоночник) ---
        pygame.draw.line(screen, color_bone,
                         (sx + self.w // 2, sy + 8),
                         (sx + self.w // 2, sy + self.h - 4), 3)

        # --- Рёбра (3 поперечные полоски) ---
        for i in range(3):
            ry = sy + 12 + i * 5
            pygame.draw.line(screen, color_bone_d,
                             (sx + 6, ry), (sx + self.w - 6, ry), 2)

        # --- Череп (круг + обводка) ---
        pygame.draw.circle(screen, color_bone,
                           (sx + self.w // 2, sy + 6), 6)
        pygame.draw.circle(screen, color_bone_d,
                           (sx + self.w // 2, sy + 6), 6, 1)

        # --- Глазницы (две чёрные точки) ---
        pygame.draw.circle(screen, self.DARK,
                           (sx + self.w // 2 - 2, sy + 6), 1)
        pygame.draw.circle(screen, self.DARK,
                           (sx + self.w // 2 + 2, sy + 6), 1)