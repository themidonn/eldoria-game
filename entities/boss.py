"""
entities/boss.py — Босс Морвейн: преследование игрока, рывки, HP-бар.
"""

import pygame
from settings import *


class Boss:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = 60, 70
        self.hp = self.max_hp = 20
        self.speed = 1.0
        self.hit_flash = 0                    # мс — красная вспышка при ударе
        self.phase = 'idle'                   # 'idle' или 'charge'
        self.charge_timer = 3.0               # сек — перезарядка перед рывком
        self.charge_dir = (0, 0)              # нормализованное направление рывка
        self.dead = True                      # активируется после диалога со Старейшиной

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
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.charge_timer > 0:
            # dt в миллисекундах, charge_timer в секундах — переводим
            self.charge_timer -= dt / 1000.0

        # --- Расстояние до игрока ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5 or 1

        # --- Фаза: Рывок ---
        if self.phase == 'charge':
            # Клэмп dt не даёт боссу телепортироваться при лагах
            step = 8 * min(dt / 16.67, 3.0)
            nx = self.x + self.charge_dir[0] * step
            ny = self.y + self.charge_dir[1] * step
            moved = False
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx
                moved = True
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny
                moved = True
            if not moved:
                # Упёрлись в стену — завершаем рывок
                self.phase = 'idle'

        # --- Фаза: Преследование ---
        elif dist < 400:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx * s, self.y, self.w, self.h):
                self.x += dx * s
            if world.is_walkable_rect(self.x, self.y + dy * s, self.w, self.h):
                self.y += dy * s

            if self.charge_timer <= 0:
                # Fallback на случай, если игрок оказался ровно в точке босса:
                # без него charge_dir стал бы (0, 0), и босс завис бы в вечном charge.
                cx, cy = dx, dy
                if cx == 0 and cy == 0:
                    cx, cy = 1.0, 0.0
                self.phase = 'charge'
                self.charge_dir = (cx, cy)
                self.charge_timer = 3.0

        else:
            # Игрок ушёл далеко — не даём заряду «накопиться впрок».
            # При возврате в зону будет минимум 1 секунда на реакцию.
            if self.charge_timer < 1.0:
                self.charge_timer = 1.0

    def take_damage(self, dmg, fx, fy):
        # fx, fy не используются: босса нельзя отбросить ударом меча.
        # Параметры сохранены для совместимости с API Slime.take_damage().
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

        # --- Тело (овал + обводка) ---
        color = (255, 100, 100) if self.hit_flash > 0 else COLOR_BOSS
        pygame.draw.ellipse(screen, color, (sx, sy + 10, self.w, self.h - 10))
        pygame.draw.ellipse(screen, (50, 10, 20),
                            (sx, sy + 10, self.w, self.h - 10), 3)

        # --- Глаза (жёлтые белки + чёрные зрачки) ---
        pygame.draw.circle(screen, (255, 240, 100), (sx + 18, sy + 30), 5)
        pygame.draw.circle(screen, (255, 240, 100), (sx + self.w - 18, sy + 30), 5)
        pygame.draw.circle(screen, (0, 0, 0),      (sx + 18, sy + 30), 2)
        pygame.draw.circle(screen, (0, 0, 0),      (sx + self.w - 18, sy + 30), 2)

        # --- HP-бар сверху экрана (только если босс в кадре) ---
        if -self.w < sx < WIDTH and -self.h < sy < HEIGHT:
            bw, bh = 200, 18
            bx = WIDTH // 2 - bw // 2
            by = 20

            pygame.draw.rect(screen, (50, 20, 30),  (bx, by, bw, bh), border_radius=4)
            fill = int(bw * self.hp / self.max_hp)
            pygame.draw.rect(screen, (200, 40, 60), (bx, by, fill, bh), border_radius=4)
            pygame.draw.rect(screen, (240, 200, 100), (bx, by, bw, bh), 2, border_radius=4)