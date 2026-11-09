"""
entities/skeleton_king.py — Король Скелетов: босс подземелья.

30 HP, медленный преследователь. При HP <= 50% — ускоряется
и стреляет копьями чаще.

Стреляет костяными копьями (BoneProjectile) в игрока каждые 2 сек,
при 50% HP — каждые 1.2 сек.
"""

import pygame
from settings import *


class SkeletonKing:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.w, self.h = 48, 56
        self.hp = self.max_hp = 30
        self.speed = 0.9
        self.hit_flash = 0
        self.dead = False

        # Таймер стрельбы
        self.shoot_timer = 2.0
        self.shoot_interval_normal = 2.0
        self.shoot_interval_enraged = 1.2

        # Флаг «второй фазы» (50% HP — ускорение)
        self.enraged = False

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, player, world, dt, projectiles):
        """
        projectiles — список, куда босс добавляет новые снаряды.
        """
        if self.dead:
            return

        if self.hit_flash > 0:
            self.hit_flash -= dt

        # --- Переход во вторую фазу ---
        if not self.enraged and self.hp <= self.max_hp // 2:
            self.enraged = True
            self.speed = 1.5

        # --- Таймер стрельбы ---
        self.shoot_timer -= dt / 1000.0
        if self.shoot_timer <= 0:
            self._shoot(player, projectiles)
            self.shoot_timer = (self.shoot_interval_enraged
                                if self.enraged else self.shoot_interval_normal)

        # --- Преследование игрока ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist > 40 and dist < 600:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx * s, self.y, self.w, self.h):
                self.x += dx * s
            if world.is_walkable_rect(self.x, self.y + dy * s, self.w, self.h):
                self.y += dy * s

    def _shoot(self, player, projectiles):
        """Стреляет 1 костяным копьём в сторону игрока."""
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 0.01:
            # Игрок ровно в точке босса — иначе dx/dist = 0 и снаряд
            # с vx = vy = 0 зависнет в воздухе. Стреляем вправо.
            dx, dy, dist = 1.0, 0.0, 1.0
        dx, dy = dx / dist, dy / dist

        # Снаряд летит от центра босса
        px = self.x + self.w / 2
        py = self.y + self.h / 2
        projectiles.append(BoneProjectile(px, py, dx, dy))

    def take_damage(self, dmg, fx, fy):
        """Босс не отбрасывается."""
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
        BONE    = (230, 230, 210)
        BONE_D  = (160, 160, 140)
        DARK    = (20, 20, 30)
        CROWN   = (240, 200, 80)
        EYE     = (255, 60, 60) if self.enraged else (150, 60, 60)

        color_bone   = (255, 150, 150) if self.hit_flash > 0 else BONE
        color_bone_d = (200, 100, 100) if self.hit_flash > 0 else BONE_D

        # --- Мантия/тело (широкий тёмный овал) ---
        pygame.draw.ellipse(screen, (40, 30, 50),
                            (sx, sy + 20, self.w, self.h - 20))
        pygame.draw.ellipse(screen, (20, 15, 25),
                            (sx, sy + 20, self.w, self.h - 20), 2)

        # --- Рёбра (видны спереди) ---
        for i in range(4):
            ry = sy + 28 + i * 5
            pygame.draw.line(screen, color_bone_d,
                             (sx + 12, ry), (sx + self.w - 12, ry), 2)

        # --- Череп ---
        pygame.draw.circle(screen, color_bone,
                           (sx + self.w // 2, sy + 18), 12)
        pygame.draw.circle(screen, color_bone_d,
                           (sx + self.w // 2, sy + 18), 12, 2)

        # --- Глазницы ---
        pygame.draw.circle(screen, EYE,
                           (sx + self.w // 2 - 5, sy + 16), 3)
        pygame.draw.circle(screen, EYE,
                           (sx + self.w // 2 + 5, sy + 16), 3)

        # --- Корона ---
        cx = sx + self.w // 2
        pygame.draw.polygon(screen, CROWN, [
            (cx - 14, sy + 8),
            (cx - 10, sy + 2),
            (cx - 5,  sy + 7),
            (cx,      sy),
            (cx + 5,  sy + 7),
            (cx + 10, sy + 2),
            (cx + 14, sy + 8),
        ])
        pygame.draw.polygon(screen, (160, 120, 30), [
            (cx - 14, sy + 8),
            (cx - 10, sy + 2),
            (cx - 5,  sy + 7),
            (cx,      sy),
            (cx + 5,  sy + 7),
            (cx + 10, sy + 2),
            (cx + 14, sy + 8),
        ], 1)

        # --- HP-бар сверху экрана (только если босс в кадре) ---
        if -self.w < sx < WIDTH and -self.h < sy < HEIGHT:
            bw, bh = 240, 18
            bx = WIDTH // 2 - bw // 2
            by = 20

            pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh),
                             border_radius=4)
            fill = int(bw * self.hp / self.max_hp)
            bar_color = (200, 40, 60) if self.enraged else (180, 160, 120)
            pygame.draw.rect(screen, bar_color, (bx, by, fill, bh),
                             border_radius=4)
            pygame.draw.rect(screen, (240, 200, 100), (bx, by, bw, bh), 2,
                             border_radius=4)


# ============================================================
#   СНАРЯД — КОСТЯНОЕ КОПЬЁ
# ============================================================
class BoneProjectile:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, dx, dy):
        self.x = float(x)
        self.y = float(y)
        self.w = self.h = 8
        self.vx = dx * 5.0
        self.vy = dy * 5.0
        self.life = 2000                # мс
        self.dead = False

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, world, dt):
        if self.dead:
            return

        k = dt / 16.67
        nx = self.x + self.vx * k
        ny = self.y + self.vy * k

        # Если врезались в стену — исчезаем
        if not world.is_walkable_rect(nx, ny, self.w, self.h):
            self.dead = True
            return

        self.x, self.y = nx, ny
        self.life -= dt
        if self.life <= 0:
            self.dead = True

    # ============================================================
    #   ОТРИСОВКА
    # ============================================================
    def draw(self, screen, cam):
        if self.dead:
            return

        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)
        pygame.draw.circle(screen, (240, 230, 200), (sx + 4, sy + 4), 4)
        pygame.draw.circle(screen, (160, 140, 110), (sx + 4, sy + 4), 4, 1)