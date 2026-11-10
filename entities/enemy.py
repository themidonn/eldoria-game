"""
entities/enemy.py — Враги: слизни (обычные и элитные).

Обычный слизень: 2 HP, светло-зелёный.
Элитный слизень: 3+ HP, тёмно-зелёный (охраняют кристаллы).

Используется в game.py:
  - _spawn() — обычные слизни по карте + элитные у кристаллов
  - _spawn_crystal_and_guards() — элитные стражи (hp=2 или 3)
  - _update_level_1() — update + take_damage
  - _draw_level_1() — draw

Поиск по файлу: Ctrl+F "region"
"""

import pygame
from settings import *


class Slime:

    # region КОНСТРУКТОР
    def __init__(self, x, y, hp=2):
        # --- Позиция и размеры ---
        self.x, self.y = float(x), float(y)
        self.w = self.h = 28

        # --- Здоровье (hp=2 обычный, hp=3+ элитный) ---
        self.hp = self.max_hp = hp

        # --- Движение ---
        self.speed = 1.3                       # px/кадр при 60 FPS
        self.knockback = [0.0, 0.0]            # [vx, vy] — отбрасывание

        # --- Состояние ---
        self.hit_flash = 0                     # мс — красная вспышка при ударе
        self.dead = False
    # endregion

    # region СВОЙСТВА
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    # endregion

    # region ЛОГИКА
    def update(self, player, world, dt):
        if self.dead:
            return

        # --- Таймеры ---
        # max(0, ...) — защита от отрицательного hit_flash при большом dt
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)

        # --- Отбрасывание после удара (с коллизиями — слизень не в стене) ---
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

        # --- Преследование игрока (только в радиусе 20..250 px) ---
        # 20 px — минимальная дистанция: слизень не «толкает» игрока,
        # 250 px — радиус агрессии (дальше слизень стоит на месте).
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if 20 < dist < 250:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            nx = self.x + dx * s
            ny = self.y + dy * s
            self._try_move(nx, ny, world)

    def _try_move(self, nx, ny, world):
        """
        Пытается сдвинуть слизня в (nx, ny) с проверкой коллизий по осям.

        X и Y проверяются отдельно — иначе слизень застревает в углах
        стен и не может «скользить» вдоль препятствия.
        """
        if world.is_walkable_rect(nx, self.y, self.w, self.h):
            self.x = nx
        if world.is_walkable_rect(self.x, ny, self.w, self.h):
            self.y = ny

    def take_damage(self, dmg, fx, fy):
        """
        Наносит урон и отбрасывает слизня от атакующего.

        Параметры:
          dmg — урон (целое > 0)
          fx, fy — координаты атакующего (для knockback)
        """
        # Защита: нулевой/отрицательный урон не должен лечить слизня,
        # и мёртвого слизня нельзя «добить» второй раз.
        if dmg <= 0 or self.dead:
            return

        self.hp -= dmg
        self.hit_flash = 200

        # Вектор от атакующего к слизню — направление отбрасывания.
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
    # endregion

    # region ОТРИСОВКА
    def draw(self, screen, cam):
        if self.dead:
            return

        # int() для совместимости с WebAssembly (Pygbag не принимает float)
        sx = int(self.x - cam.x)
        sy = int(self.y - cam.y)

        # --- Выбор цвета по силе слизня ---
        if self.max_hp >= 3:
            # Элитный: тёмно-зелёный (охраняет кристаллы)
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
    # endregion