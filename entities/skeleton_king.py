"""
entities/skeleton_king.py — Король Скелетов: босс подземелья.

30 HP, медленный преследователь. При HP <= 50% — ускоряется
и стреляет копьями чаще.

Стреляет костяными копьями (BoneProjectile) в игрока каждые 2 сек,
при 50% HP — каждые 1.2 сек.

Используется в game.py:
  - _ensure_dungeon() — создаёт экземпляр (один на подземелье)
  - _update_level_2() — update + take_damage
  - _draw_level_2() — draw
  - save_progress() / load_progress() — сохраняет только dead
    (HP при загрузке восстанавливается до полного — осознанно)

Особенности:
  - enraged = True при hp <= max_hp // 2 (15 HP)
  - в enraged: speed 0.9 → 1.5, shoot_interval 2.0 → 1.2
  - глаза меняют цвет: тускло-красные → ярко-красные
"""

import pygame
from settings import *


class SkeletonKing:

    # ============================================================
    #   ПАЛИТРА (атрибуты класса — не пересоздаются каждый кадр)
    # ============================================================
    BONE       = (230, 230, 210)     # кости
    BONE_D     = (160, 160, 140)     # тень костей
    MANTLE     = (40, 30, 50)        # мантия
    MANTLE_D   = (20, 15, 25)        # обводка мантии
    CROWN      = (240, 200, 80)      # корона
    CROWN_D    = (160, 120, 30)      # обводка короны
    EYE_NORMAL = (150, 60, 60)       # глаза (1 фаза)
    EYE_RAGE   = (255, 60, 60)       # глаза (2 фаза)

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y):
        # --- Позиция и размеры ---
        self.x = float(x)
        self.y = float(y)
        self.w, self.h = 48, 56

        # --- Здоровье ---
        self.hp = self.max_hp = 30

        # --- Движение ---
        # 0.9 px/кадр в 1 фазе, 1.5 px/кадр в 2 фазе (после enraged).
        self.speed = 0.9

        # --- Состояние ---
        self.hit_flash = 0           # мс — красная вспышка при ударе
        self.dead = False

        # --- Таймер стрельбы ---
        self.shoot_timer = 2.0
        self.shoot_interval_normal = 2.0     # сек — 1 фаза
        self.shoot_interval_enraged = 1.2    # сек — 2 фаза

        # --- Флаг «второй фазы» (при HP <= 50%) ---
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
        Обновляет состояние босса.

        Параметры:
          player — цель
          world — карта (для коллизий)
          dt — мс с прошлого кадра
          projectiles — список, куда босс добавляет новые снаряды
                        (game.py, self.dungeon_projectiles)
        """
        if self.dead:
            return

        # --- Таймеры ---
        # max(0, ...) — защита от отрицательного hit_flash при большом dt
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)

        # --- Переход во вторую фазу (HP <= 50%) ---
        # 30 // 2 = 15, то есть enraged на 15 HP и ниже.
        if not self.enraged and self.hp <= self.max_hp // 2:
            self.enraged = True
            self.speed = 1.5
            # shoot_interval сменится после следующего выстрела
            # (см. _shoot → self.shoot_timer = ...).

        # --- Таймер стрельбы ---
        # dt в миллисекундах, shoot_timer в секундах — переводим.
        # Клэмп до 0: проверка <= 0 работает и с отрицательным,
        # но так значение читаемее при отладке.
        self.shoot_timer = max(0.0, self.shoot_timer - dt / 1000.0)
        if self.shoot_timer <= 0:
            self._shoot(player, projectiles)
            self.shoot_timer = (self.shoot_interval_enraged
                                if self.enraged
                                else self.shoot_interval_normal)

        # --- Преследование игрока ---
        # dist > 40 — не приближается вплотную (иначе стоял бы на игроке).
        # dist < 600 — дальше не преследует (защита от «убегания» по всей карте).
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if 40 < dist < 600:
            dx, dy = dx / dist, dy / dist
            s = self.speed * (dt / 16.67)
            if world.is_walkable_rect(self.x + dx * s, self.y, self.w, self.h):
                self.x += dx * s
            if world.is_walkable_rect(self.x, self.y + dy * s, self.w, self.h):
                self.y += dy * s

    def _shoot(self, player, projectiles):
        """
        Стреляет 1 костяным копьём в сторону игрока.

        Снаряд спавнится в центре босса. Учитываем, что BoneProjectile
        использует self.x как ЛЕВЫЙ ВЕРХНИЙ угол, поэтому вычитаем
        половину размера снаряда, чтобы его центр совпал с центром босса.
        """
        dx = player.x - self.x
        dy = player.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 0.01:
            # Игрок ровно в точке босса — иначе dx/dist = 0 и снаряд
            # с vx = vy = 0 зависнет в воздухе. Стреляем вправо.
            dx, dy, dist = 1.0, 0.0, 1.0
        dx, dy = dx / dist, dy / dist

        # Центр босса минус половина размера снаряда = top-left для rect.
        half = BoneProjectile.SIZE // 2
        px = self.x + self.w / 2 - half
        py = self.y + self.h / 2 - half
        projectiles.append(BoneProjectile(px, py, dx, dy))

    def take_damage(self, dmg, fx, fy):
        """
        Наносит урон. Босса нельзя отбросить — параметры fx, fy
        сохранены для совместимости с API Slime / Bat / Boss,
        но не используются.
        """
        # Защита: нулевой/отрицательный урон не должен лечить босса,
        # и мёртвого босса нельзя «добить» второй раз.
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

        # --- Мантия/тело (широкий тёмный овал) ---
        # Верхние 20 px (sy..sy+20) — зона черепа и короны.
        pygame.draw.ellipse(screen, self.MANTLE,
                            (sx, sy + 20, self.w, self.h - 20))
        pygame.draw.ellipse(screen, self.MANTLE_D,
                            (sx, sy + 20, self.w, self.h - 20), 2)

        # --- Рёбра (видны спереди) ---
        for i in range(4):
            ry = sy + 28 + i * 5
            pygame.draw.line(screen, color_bone_d,
                             (sx + 12, ry), (sx + self.w - 12, ry), 2)

        # --- Череп (круг + обводка) ---
        pygame.draw.circle(screen, color_bone,
                           (sx + self.w // 2, sy + 18), 12)
        pygame.draw.circle(screen, color_bone_d,
                           (sx + self.w // 2, sy + 18), 12, 2)

        # --- Глазницы (цвет зависит от фазы) ---
        eye_color = self.EYE_RAGE if self.enraged else self.EYE_NORMAL
        pygame.draw.circle(screen, eye_color,
                           (sx + self.w // 2 - 5, sy + 16), 3)
        pygame.draw.circle(screen, eye_color,
                           (sx + self.w // 2 + 5, sy + 16), 3)

        # --- Корона (7-конечная, с обводкой) ---
        cx = sx + self.w // 2
        crown_pts = [
            (cx - 14, sy + 8),
            (cx - 10, sy + 2),
            (cx - 5,  sy + 7),
            (cx,      sy),
            (cx + 5,  sy + 7),
            (cx + 10, sy + 2),
            (cx + 14, sy + 8),
        ]
        pygame.draw.polygon(screen, self.CROWN, crown_pts)
        pygame.draw.polygon(screen, self.CROWN_D, crown_pts, 1)

        # --- HP-бар сверху экрана (только если босс в кадре) ---
        # Проверка «в кадре»: иначе бар виден даже когда босс за экраном.
        if -self.w < sx < WIDTH and -self.h < sy < HEIGHT:
            bw, bh = 240, 18
            bx = WIDTH // 2 - bw // 2
            by = 20

            pygame.draw.rect(screen, (30, 20, 40),
                             (bx, by, bw, bh), border_radius=4)

            # max(0, ...) — защита: если hp ушёл в минус (не должно
            # случаться, но на всякий), ширина не станет отрицательной.
            fill = max(0, int(bw * self.hp / self.max_hp))

            # Цвет полоски: серо-золотой в 1 фазе, ярко-красный в 2 фазе.
            bar_color = (200, 40, 60) if self.enraged else (180, 160, 120)
            pygame.draw.rect(screen, bar_color,
                             (bx, by, fill, bh), border_radius=4)
            pygame.draw.rect(screen, (240, 200, 100),
                             (bx, by, bw, bh), 2, border_radius=4)


# ============================================================
#   СНАРЯД — КОСТЯНОЕ КОПЬЁ
# ============================================================
class BoneProjectile:

    # Размер снаряда (8×8). Используется в SkeletonKing._shoot
    # для центрирования спавна.
    SIZE = 8

    # ============================================================
    #   КОНСТРУКТОР
    # ============================================================
    def __init__(self, x, y, dx, dy):
        # --- Позиция и размеры ---
        # self.x, self.y — левый верхний угол hitbox (как у всех entity).
        self.x = float(x)
        self.y = float(y)
        self.w = self.h = self.SIZE

        # --- Скорость ---
        # 5.0 px/кадр при 60 FPS — примерно в 5 раз быстрее игрока.
        self.vx = dx * 5.0
        self.vy = dy * 5.0

        # --- Время жизни ---
        # 2000 мс = 2 сек. За это время снаряд пролетит
        # до 600 px (2 сек × 60 FPS × 5 px) — ровно радиус агрессии босса.
        self.life = 2000

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

        # --- Перемещение (frame-independent) ---
        # dt в миллисекундах, k — множитель к 1 кадру при 60 FPS.
        k = dt / 16.67
        nx = self.x + self.vx * k
        ny = self.y + self.vy * k

        # --- Коллизия со стеной ---
        # Проверяем сразу конечную точку: при 5 px/кадр и dt ≤ 100 мс
        # снаряд не «протуннелирует» сквозь стену толщиной TILE = 32 px.
        if not world.is_walkable_rect(nx, ny, self.w, self.h):
            self.dead = True
            return

        self.x, self.y = nx, ny

        # --- Время жизни ---
        self.life -= dt
        if self.life <= 0:
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

        # --- Копьё: светлый круг + тёмная обводка ---
        # Центр = (sx + 4, sy + 4), радиус 4 — ровно по размеру hitbox 8×8.
        pygame.draw.circle(screen, (240, 230, 200), (sx + 4, sy + 4), 4)
        pygame.draw.circle(screen, (160, 140, 110), (sx + 4, sy + 4), 4, 1)