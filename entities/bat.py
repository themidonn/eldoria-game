"""
entities/bat.py — Летучая мышь: преследует игрока с коллизиями.

Слабая (1 HP), но её сложно поймать: двигается по синусоиде,
не даёт спокойно стоять на месте. Учитывает стены и колонны —
если игрок спрячется за колонной, мышь упрётся в неё.
"""

import math
import pygame
from settings import *


class Bat:

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.w = self.h = 22
        self.hp = self.max_hp = 1
        self.speed = 1.8
        self.hit_flash = 0                # мс — красная вспышка при ударе
        self.knockback = [0.0, 0.0]       # отбрасывание при ударе
        self.bob_time = 0.0               # фаза покачивания крыльев и полёта
        self.dead = False

    # ============================================================
    #   СВОЙСТВА
    # ============================================================
    @property
    def rect(self):
        # Хитбокс включает крылья: они расширяют тело на ±4 px по X.
        # Без этого урон не срабатывает, когда мышь касается игрока боком.
        return pygame.Rect(int(self.x) - 4, int(self.y), self.w + 8, self.h)

    # ============================================================
    #   ЛОГИКА
    # ============================================================
    def update(self, player, world, dt):
        if self.dead:
            return

        # --- Таймеры ---
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.bob_time += dt * 0.008

        # --- Отбрасывание (с коллизиями — мышь не провалится в стену) ---
        if self.knockback[0] or self.knockback[1]:
            k = dt / 16.67
            nx = self.x + self.knockback[0] * k
            ny = self.y + self.knockback[1] * k
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny
            self.knockback[0] *= 0.85
            self.knockback[1] *= 0.85
            if abs(self.knockback[0]) < 0.1: self.knockback[0] = 0
            if abs(self.knockback[1]) < 0.1: self.knockback[1] = 0

        # --- Преследование с синусоидой (с коллизиями) ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if 1 < dist < 350:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            sine_offset = math.sin(self.bob_time * 3) * 1.5 * (dt / 16.67)

            nx = self.x + dx * s
            ny = self.y + dy * s + sine_offset

            # X и Y проверяем отдельно — мышь «скользит» вдоль препятствий
            if world.is_walkable_rect(nx, self.y, self.w, self.h):
                self.x = nx
            if world.is_walkable_rect(self.x, ny, self.w, self.h):
                self.y = ny

    def take_damage(self, dmg, fx, fy):
        """fx, fy — координаты атакующего (для knockback)."""
        self.hp -= dmg
        self.hit_flash = 200
        dx = self.x - fx
        dy = self.y - fy
        d = (dx * dx + dy * dy) ** 0.5 or 1
        self.knockback = [dx / d * 10, dy / d * 10]

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

        # Красная вспышка при ударе
        color = (255, 100, 100) if self.hit_flash > 0 else (80, 60, 120)
        dark  = (40, 30, 60)

        # --- Крылья (машут через синус) ---
        wing_offset = int(math.sin(self.bob_time * 5) * 4)

        # Левое крыло
        pygame.draw.polygon(screen, color, [
            (sx + 8, sy + self.h // 2),
            (sx - 4, sy + 4 - wing_offset),
            (sx - 4, sy + self.h - 4 + wing_offset),
        ])
        # Правое крыло
        pygame.draw.polygon(screen, color, [
            (sx + self.w - 8, sy + self.h // 2),
            (sx + self.w + 4, sy + 4 - wing_offset),
            (sx + self.w + 4, sy + self.h - 4 + wing_offset),
        ])

        # --- Тело (тёмный овал) ---
        pygame.draw.ellipse(screen, dark, (sx + 4, sy + 6, self.w - 8, self.h - 6))

        # --- Красные глаза ---
        pygame.draw.circle(screen, (255, 50, 50), (sx + 8, sy + 10), 2)
        pygame.draw.circle(screen, (255, 50, 50), (sx + self.w - 8, sy + 10), 2)