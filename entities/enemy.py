"""
entities/enemy.py — Враги: слизни (обычные и элитные).

Обычный слизень: 2 HP, светло-зелёный.
Элитный слизень: 3+ HP, тёмно-зелёный.
"""

import pygame
from settings import *


class Slime:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, hp=2):
        self.x, self.y = float(x), float(y)
        self.w = self.h = 28
        self.hp = self.max_hp = hp
        self.speed = 1.3
        self.hit_flash = 0                # мс — красная вспышка при ударе
        self.knockback = [0.0, 0.0]       # [vx, vy] — текущая скорость отбрасывания
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
    def update(self, player, world, dt):
        if self.dead:
            return

        # --- Таймеры ---
        if self.hit_flash > 0:
            self.hit_flash -= dt

        # --- Отбрасывание после удара ---
        if self.knockback[0] or self.knockback[1]:
            k = dt / 16.67
            nx = self.x + self.knockback[0] * k
            ny = self.y + self.knockback[1] * k
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny

            # Плавное затухание (0.85 за обновление)
            self.knockback[0] *= 0.85
            self.knockback[1] *= 0.85
            if abs(self.knockback[0]) < 0.1:
                self.knockback[0] = 0
            if abs(self.knockback[1]) < 0.1:
                self.knockback[1] = 0

        # --- Преследование игрока (только в радиусе 20..250 px) ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if 20 < dist < 250:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx * s, self.y, self.w, self.h):
                self.x += dx * s
            if world.is_walkable_rect(self.x, self.y + dy * s, self.w, self.h):
                self.y += dy * s

    def take_damage(self, dmg, fx, fy):
        """fx, fy — координаты атакующего (игрока), от них считается направление knockback."""
        self.hp -= dmg
        self.hit_flash = 200

        # Вектор от атакующего к слизню, нормализованный и умноженный на 8
        dx = self.x - fx
        dy = self.y - fy
        d = (dx * dx + dy * dy) ** 0.5
        if d < 0.01:
            # Игрок и слизень в одной точке — отбрасываем вправо,
            # иначе knockback = [0, 0] и слизень остался бы на месте.
            dx, dy, d = 1.0, 0.0, 1.0
        self.knockback = [dx / d * 8, dy / d * 8]

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

        # --- Выбор цвета по силе слизня ---
        if self.max_hp >= 3:
            # Элитный: тёмно-зелёный
            base_color = (60, 130, 60)
            outline_color = (30, 70, 30)
        else:
            # Обычный: светло-зелёный
            base_color = COLOR_SLIME
            outline_color = COLOR_SLIME_D

        # Красная вспышка при получении урона
        color = (255, 100, 100) if self.hit_flash > 0 else base_color

        # --- Тело (овал + обводка) ---
        pygame.draw.ellipse(screen, color, (sx, sy + 4, self.w, self.h - 4))
        pygame.draw.ellipse(screen, outline_color,
                            (sx, sy + 4, self.w, self.h - 4), 2)

        # --- Глаза (белки + зрачки) ---
        pygame.draw.circle(screen, (255, 255, 255), (sx + 8, sy + 12), 3)
        pygame.draw.circle(screen, (255, 255, 255), (sx + self.w - 8, sy + 12), 3)
        pygame.draw.circle(screen, (0, 0, 0),      (sx + 8, sy + 12), 1)
        pygame.draw.circle(screen, (0, 0, 0),      (sx + self.w - 8, sy + 12), 1)