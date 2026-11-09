"""
entities/skeleton.py — Скелет: медленный, но крепкий враг.

4 HP, не отбрасывается мечом (тяжёлый). Патрулирует вокруг своей
стартовой точки. При приближении игрока (< 220 px) — переключается
в преследование. Обитает в подземелье, охраняет Короля Скелетов.
"""

import pygame


class Skeleton:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, hp=4):
        self.x = float(x)
        self.y = float(y)
        self.w = self.h = 28
        self.hp = self.max_hp = hp
        self.speed = 0.9
        self.hit_flash = 0
        self.dead = False

        # Стартовая позиция — скелет возвращается сюда, когда игрок далеко
        self.home_x = float(x)
        self.home_y = float(y)
        self.patrol_dir = 1              # 1 — вправо, -1 — влево
        self.patrol_timer = 0.0

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

        if self.hit_flash > 0:
            self.hit_flash -= dt

        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        s = self.speed * (dt / 16.67)

        # --- Преследование игрока (< 220 px) ---
        if dist < 220:
            if dist > 1:
                dx, dy = dx / dist, dy / dist
                if world.is_walkable_rect(self.x + dx * s, self.y, self.w, self.h):
                    self.x += dx * s
                if world.is_walkable_rect(self.x, self.y + dy * s, self.w, self.h):
                    self.y += dy * s
        else:
            # --- Игрок далеко: возврат домой или патруль вокруг дома ---
            hdx = self.home_x - self.x
            hdy = self.home_y - self.y
            dist_home = (hdx * hdx + hdy * hdy) ** 0.5

            if dist_home > 8:
                # Скелет ушёл от стартовой точки — возвращаемся
                hdx, hdy = hdx / dist_home, hdy / dist_home
                if world.is_walkable_rect(self.x + hdx * s, self.y, self.w, self.h):
                    self.x += hdx * s
                if world.is_walkable_rect(self.x, self.y + hdy * s, self.w, self.h):
                    self.y += hdy * s
            else:
                # Дома — патруль влево-вправо в радиусе ±20 px от home_x
                self.patrol_timer += dt / 1000.0
                if self.patrol_timer > 2.5:
                    self.patrol_timer = 0.0
                    self.patrol_dir *= -1

                new_x = self.x + self.patrol_dir * s * 0.5
                blocked = not world.is_walkable_rect(new_x, self.y, self.w, self.h)
                too_far = abs(new_x - self.home_x) > 20

                if blocked or too_far:
                    self.patrol_dir *= -1
                else:
                    self.x = new_x

    def take_damage(self, dmg, fx, fy):
        """fx, fy не используются: скелета не отбросить мечом."""
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

        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Палитра ---
        BONE   = (220, 220, 200)
        BONE_D = (140, 140, 120)
        DARK   = (30, 30, 40)

        color_bone   = (255, 150, 150) if self.hit_flash > 0 else BONE
        color_bone_d = (200, 100, 100) if self.hit_flash > 0 else BONE_D

        # --- Тело (позвоночник) ---
        pygame.draw.line(screen, color_bone,
                         (sx + self.w // 2, sy + 8),
                         (sx + self.w // 2, sy + self.h - 4), 3)

        # --- Рёбра ---
        for i in range(3):
            ry = sy + 12 + i * 5
            pygame.draw.line(screen, color_bone_d,
                             (sx + 6, ry), (sx + self.w - 6, ry), 2)

        # --- Череп ---
        pygame.draw.circle(screen, color_bone,
                           (sx + self.w // 2, sy + 6), 6)
        pygame.draw.circle(screen, color_bone_d,
                           (sx + self.w // 2, sy + 6), 6, 1)

        # --- Глазницы ---
        pygame.draw.circle(screen, DARK,
                           (sx + self.w // 2 - 2, sy + 6), 1)
        pygame.draw.circle(screen, DARK,
                           (sx + self.w // 2 + 2, sy + 6), 1)