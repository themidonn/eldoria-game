"""
entities/bat.py — Летучая мышь: преследует игрока с коллизиями.

Слабая (1 HP), но её сложно поймать: двигается по синусоиде,
не даёт спокойно стоять на месте. Учитывает стены и колонны —
если игрок спрячется за колонной, мышь упрётся в неё.

Используется только в подземелье (game.py, _ensure_dungeon →
self.dungeon_bats).

Поиск по файлу: Ctrl+F "region"
"""

import math
import pygame


class Bat:

    # region КОНСТРУКТОР
    def __init__(self, x, y):
        # --- Позиция и размеры ---
        self.x = float(x)                      # левый верхний угол (float)
        self.y = float(y)
        self.w = self.h = 22                   # тело без крыльев

        # --- Здоровье ---
        self.hp = self.max_hp = 1

        # --- Движение ---
        self.speed = 1.8                       # px/кадр при 60 FPS
        self.bob_time = 0.0                    # фаза покачивания крыльев
        self.knockback = [0.0, 0.0]            # отбрасывание при ударе

        # --- Состояние ---
        self.hit_flash = 0                     # мс — красная вспышка при ударе
        self.dead = False
    # endregion

    # region СВОЙСТВА
    @property
    def rect(self):
        # Хитбокс включает крылья: они расширяют тело на ±4 px по X.
        # Без этого урон не срабатывает, когда мышь касается игрока боком.
        # ВАЖНО: для коллизий со стенами используется self.w (тело),
        # а не этот rect — крылья не должны застревать в стенах.
        return pygame.Rect(int(self.x) - 4, int(self.y), self.w + 8, self.h)
    # endregion

    # region ЛОГИКА
    def update(self, player, world, dt):
        if self.dead:
            return

        # --- Таймеры ---
        # max(0, ...) — защита от отрицательного hit_flash при большом dt
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)

        # bob_time крутится в цикле, чтобы float не терял точность
        # при очень долгой игре (синус от больших чисел — не проблема,
        # но так надёжнее и читаемее).
        self.bob_time = (self.bob_time + dt * 0.008) % (2 * math.pi * 1000)

        # --- Отбрасывание (с коллизиями — мышь не провалится в стену) ---
        if self.knockback[0] or self.knockback[1]:
            k = dt / 16.67
            nx = self.x + self.knockback[0] * k
            ny = self.y + self.knockback[1] * k
            self._try_move(nx, ny, world)

            # Frame-independent затухание: при 30 FPS и 60 FPS
            # knockback проходит одинаковое расстояние.
            decay = 0.85 ** (dt / 16.67)
            self.knockback[0] *= decay
            self.knockback[1] *= decay
            if abs(self.knockback[0]) < 0.1:
                self.knockback[0] = 0
            if abs(self.knockback[1]) < 0.1:
                self.knockback[1] = 0

        # --- Преследование с синусоидой (с коллизиями) ---
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        # 1 < dist — защита от деления на ноль, если мышь и игрок
        # оказались в одной точке. 350 — радиус агрессии.
        if 1 < dist < 350:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            sine_offset = math.sin(self.bob_time * 3) * 1.5 * (dt / 16.67)

            nx = self.x + dx * s
            ny = self.y + dy * s + sine_offset
            self._try_move(nx, ny, world)

    def _try_move(self, nx, ny, world):
        """
        Пытается сдвинуть мышь в (nx, ny) с проверкой коллизий по осям.

        X и Y проверяются отдельно — иначе мышь застревает в углах
        стен и не может «скользить» вдоль препятствия.
        """
        if world.is_walkable_rect(nx, self.y, self.w, self.h):
            self.x = nx
        if world.is_walkable_rect(self.x, ny, self.w, self.h):
            self.y = ny

    def take_damage(self, dmg, fx, fy):
        """
        Наносит урон и отбрасывает мышь от атакующего.

        Параметры:
          dmg — урон (целое > 0)
          fx, fy — координаты атакующего (для knockback)
        """
        # Защита: нулевой/отрицательный урон не должен лечить мышь,
        # и мёртвую мышь нельзя «добить» второй раз.
        if dmg <= 0 or self.dead:
            return

        self.hp -= dmg
        self.hit_flash = 200

        # Вектор от атакующего к мыши — направление отбрасывания.
        dx = self.x - fx
        dy = self.y - fy
        d = (dx * dx + dy * dy) ** 0.5
        if d < 0.01:
            # Игрок и мышь оказались в одной точке — отбрасываем вправо,
            # иначе dx/d * 10 = 0 и мышь «зависла» бы на месте.
            dx, dy, d = 1.0, 0.0, 1.0
        self.knockback = [dx / d * 10, dy / d * 10]

        if self.hp <= 0:
            self.dead = True
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        if self.dead:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Цвета (красная вспышка при ударе) ---
        color = (255, 100, 100) if self.hit_flash > 0 else (80, 60, 120)
        dark = (40, 30, 60)

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
    # endregion